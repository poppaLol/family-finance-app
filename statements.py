from typing import Annotated
from uuid import uuid4


from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from finance_app.csv_adapter import normalise_statement_key, parse_statement_csv
from finance_app.models import StatementLine


router = APIRouter(prefix="/statements", tags=["statements"])

templates = Jinja2Templates(directory="templates")
TRANSACTION_TYPES = [
    "DEBIT",
    "CREDIT",
    "TRANSFER",
    "CARD_PAYMENT",
    "DIRECT_DEBIT",
]


def _statement_line_from_form(
    date: str,
    counter_party: str,
    reference: str,
    transaction_type: str,
    amount: float,
    balance: float,
    external_category: str,
) -> StatementLine:
    return StatementLine(
        date=date,
        counter_party=counter_party,
        reference=reference,
        transaction_type=transaction_type,
        amount=amount,
        balance=balance,
        external_category=external_category,
    )


def _pending_import(request: Request, import_id: str):
    pending = request.app.state.pending_imports.get(import_id)
    if pending is None:
        raise HTTPException(status_code=404, detail="Pending import not found")
    return pending


def _import_groups(lines: list[StatementLine], assignments: dict[str, str]):
    grouped: dict[str, list[StatementLine]] = {}
    for line in lines:
        grouped.setdefault(normalise_statement_key(line), []).append(line)
    return [
        {
            "index": index,
            "key": key,
            "lines": group_lines,
            "category_name": assignments.get(
                group_lines[0].source_hash,
                group_lines[0].external_category,
            ),
        }
        for index, (key, group_lines) in enumerate(
            sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0]))
        )
    ]


@router.get("/", response_class=HTMLResponse)
async def statement_list(request: Request, imported: int | None = None):
    store = request.app.state.store

    return templates.TemplateResponse(
        request=request,
        name="statements/list.html",
        context={
            "statements": store.list_statement_lines_with_owners(),
            "imported": imported,
        },
    )


@router.get("/create", response_class=HTMLResponse)
async def statement_input(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="statements/create.html",
        context={
            "form": None,
            "errors": [],
            "transaction_types": TRANSACTION_TYPES,
            "title": "Statement Line Entry",
            "submit_label": "Save Statement Line",
        },
    )


@router.post("/create")
async def statement_input_post(
    date: Annotated[str, Form()],
    counter_party: Annotated[str, Form()],
    reference: Annotated[str, Form()],
    transaction_type: Annotated[str, Form()],
    amount: Annotated[float, Form()],
    balance: Annotated[float, Form()],
    external_category: Annotated[str, Form()],
    request: Request,
):
    store = request.app.state.store
    line = _statement_line_from_form(
        date=date,
        counter_party=counter_party,
        reference=reference,
        transaction_type=transaction_type,
        amount=amount,
        balance=balance,
        external_category=external_category,
    )

    store.save(line)

    return RedirectResponse(
        "/statements",
        status_code=303,
    )


@router.get("/import", response_class=HTMLResponse)
async def statement_import(request: Request):
    store = request.app.state.store
    return templates.TemplateResponse(
        request=request,
        name="statements/import.html",
        context={"errors": [], "people": store.list_persons()},
    )


@router.post("/import", response_class=HTMLResponse)
async def statement_import_post(
    request: Request,
    person_id: Annotated[int, Form()],
    file: UploadFile = File(...),
):
    store = request.app.state.store
    people = store.list_persons()
    if store.get_person(person_id) is None:
        return templates.TemplateResponse(
            request=request,
            name="statements/import.html",
            context={"errors": ["Please choose a family member"], "people": people},
            status_code=400,
        )

    if not file.filename or not file.filename.lower().endswith(".csv"):
        return templates.TemplateResponse(
            request=request,
            name="statements/import.html",
            context={"errors": ["Please upload a CSV file"], "people": people},
            status_code=400,
        )

    try:
        lines = parse_statement_csv(await file.read(), file.filename)
    except (UnicodeDecodeError, ValueError) as exc:
        return templates.TemplateResponse(
            request=request,
            name="statements/import.html",
            context={"errors": [str(exc)], "people": people},
            status_code=400,
        )

    person = store.get_person(person_id)
    assignments: dict[str, str] = {}
    for line in lines:
        category = store.category_for_statement_line(line)
        if category is not None:
            assignments[line.source_hash] = category["props"]["name"]

    import_id = uuid4().hex
    request.app.state.pending_imports[import_id] = {
        "person_id": person_id,
        "person_name": person["props"]["name"],
        "source_name": file.filename,
        "lines": lines,
        "assignments": assignments,
        "remember_hashes": set(),
    }

    return RedirectResponse(
        f"/statements/import/{import_id}/categorise",
        status_code=303,
    )


@router.get("/import/{import_id}/categorise", response_class=HTMLResponse)
async def statement_import_categorise(import_id: str, request: Request):
    pending = _pending_import(request, import_id)

    return templates.TemplateResponse(
        request=request,
        name="statements/import_categorise.html",
        context={
            "import_id": import_id,
            "pending": pending,
            "groups": _import_groups(pending["lines"], pending["assignments"]),
            "categories": request.app.state.store.list_categories(),
            "errors": [],
        },
    )


@router.post("/import/{import_id}/categorise")
async def statement_import_categorise_post(import_id: str, request: Request):
    pending = _pending_import(request, import_id)
    form = await request.form()
    assignments: dict[str, str] = {}
    remember_hashes: set[str] = set()

    groups = _import_groups(pending["lines"], pending["assignments"])
    for group in groups:
        category_name = str(form.get(f"category_{group['index']}", "")).strip()
        remember = form.get(f"remember_{group['index']}") == "true"
        if not category_name:
            continue
        for line in group["lines"]:
            assignments[line.source_hash] = category_name
            if remember:
                remember_hashes.add(line.source_hash)

    pending["assignments"] = assignments
    pending["remember_hashes"] = remember_hashes

    return RedirectResponse(
        f"/statements/import/{import_id}/review",
        status_code=303,
    )


@router.get("/import/{import_id}/review", response_class=HTMLResponse)
async def statement_import_review(import_id: str, request: Request):
    pending = _pending_import(request, import_id)
    rows = [
        {
            "line": line,
            "category_name": pending["assignments"].get(line.source_hash, ""),
            "remember_rule": line.source_hash in pending["remember_hashes"],
        }
        for line in pending["lines"]
    ]

    return templates.TemplateResponse(
        request=request,
        name="statements/import_review.html",
        context={
            "import_id": import_id,
            "pending": pending,
            "rows": rows,
            "uncategorised_count": sum(1 for row in rows if not row["category_name"]),
        },
    )


@router.post("/import/{import_id}/ingest")
async def statement_import_ingest(import_id: str, request: Request):
    pending = _pending_import(request, import_id)
    imported = request.app.state.store.import_statement_lines(
        pending["lines"],
        pending["person_id"],
        pending["assignments"],
        pending["remember_hashes"],
    )
    del request.app.state.pending_imports[import_id]

    return RedirectResponse(
        f"/statements?imported={imported}",
        status_code=303,
    )


@router.get("/{statement_line_id}/edit", response_class=HTMLResponse)
async def statement_edit(statement_line_id: int, request: Request):
    store = request.app.state.store
    statement = store.get_statement_line(statement_line_id)
    if statement is None:
        raise HTTPException(status_code=404, detail="Statement line not found")

    return templates.TemplateResponse(
        request=request,
        name="statements/create.html",
        context={
            "form": statement["props"],
            "errors": [],
            "transaction_types": TRANSACTION_TYPES,
            "title": "Edit Statement Line",
            "submit_label": "Update Statement Line",
        },
    )


@router.post("/{statement_line_id}/edit")
async def statement_edit_post(
    statement_line_id: int,
    date: Annotated[str, Form()],
    counter_party: Annotated[str, Form()],
    reference: Annotated[str, Form()],
    transaction_type: Annotated[str, Form()],
    amount: Annotated[float, Form()],
    balance: Annotated[float, Form()],
    external_category: Annotated[str, Form()],
    request: Request,
):
    store = request.app.state.store
    existing = store.get_statement_line(statement_line_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Statement line not found")

    line = _statement_line_from_form(
        date=date,
        counter_party=counter_party,
        reference=reference,
        transaction_type=transaction_type,
        amount=amount,
        balance=balance,
        external_category=external_category,
    )
    line.source_hash = existing["props"].get("source_hash", "")
    store.update_statement_line(statement_line_id, line)

    return RedirectResponse(
        "/statements",
        status_code=303,
    )


@router.post("/{statement_line_id}/delete")
async def statement_delete(statement_line_id: int, request: Request):
    store = request.app.state.store
    if store.get_statement_line(statement_line_id) is None:
        raise HTTPException(status_code=404, detail="Statement line not found")

    store.delete_statement_line(statement_line_id)

    return RedirectResponse(
        "/statements",
        status_code=303,
    )


@router.get("/{statement_line_id}/categorise", response_class=HTMLResponse)
async def statement_categorise(statement_line_id: int, request: Request):
    store = request.app.state.store
    statement = store.get_statement_line(statement_line_id)
    if statement is None:
        raise HTTPException(status_code=404, detail="Statement line not found")

    return templates.TemplateResponse(
        request=request,
        name="statements/categorise.html",
        context={
            "statement": statement,
            "categories": store.list_categories(),
            "errors": [],
        },
    )


@router.post("/{statement_line_id}/categorise")
async def statement_categorise_post(
    statement_line_id: int,
    request: Request,
    category_name: Annotated[str, Form()],
    remember_rule: Annotated[bool, Form()] = False,
):
    store = request.app.state.store
    if store.get_statement_line(statement_line_id) is None:
        raise HTTPException(status_code=404, detail="Statement line not found")

    if not category_name.strip():
        statement = store.get_statement_line(statement_line_id)
        return templates.TemplateResponse(
            request=request,
            name="statements/categorise.html",
            context={
                "statement": statement,
                "categories": store.list_categories(),
                "errors": ["Category is required"],
            },
            status_code=400,
        )

    store.categorise_statement_line(
        statement_line_id,
        category_name,
        remember_rule,
    )

    return RedirectResponse(
        "/statements",
        status_code=303,
    )
