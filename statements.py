from typing import Annotated


from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
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


@router.get("/", response_class=HTMLResponse)
async def statement_list(request: Request):
    store = request.app.state.store

    return templates.TemplateResponse(
        request=request,
        name="statements/list.html",
        context={"statements": store.list_statement_lines()},
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
    if store.get_statement_line(statement_line_id) is None:
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
