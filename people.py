from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from finance_app.models import Person


router = APIRouter(prefix="/people", tags=["people"])
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def person_list(request: Request):
    store = request.app.state.store

    return templates.TemplateResponse(
        request=request,
        name="people/list.html",
        context={"people": store.list_persons()},
    )


@router.get("/create", response_class=HTMLResponse)
async def person_create(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="people/form.html",
        context={
            "form": None,
            "errors": [],
            "title": "Add Family Member",
            "submit_label": "Save Person",
        },
    )


@router.post("/create")
async def person_create_post(
    request: Request,
    name: Annotated[str, Form()],
):
    store = request.app.state.store
    person = Person(name=name)
    store.save_person(person)

    return RedirectResponse(
        "/people",
        status_code=303,
    )


@router.get("/{person_id}/edit", response_class=HTMLResponse)
async def person_edit(person_id: int, request: Request):
    store = request.app.state.store
    person = store.get_person(person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found")

    return templates.TemplateResponse(
        request=request,
        name="people/form.html",
        context={
            "form": person["props"],
            "errors": [],
            "title": "Edit Family Member",
            "submit_label": "Update Person",
        },
    )


@router.post("/{person_id}/edit")
async def person_edit_post(
    person_id: int,
    request: Request,
    name: Annotated[str, Form()],
):
    store = request.app.state.store
    if store.get_person(person_id) is None:
        raise HTTPException(status_code=404, detail="Person not found")

    person = Person(name=name)
    store.update_person(person_id, person)

    return RedirectResponse(
        "/people",
        status_code=303,
    )


@router.post("/{person_id}/delete")
async def person_delete(person_id: int, request: Request):
    store = request.app.state.store
    if store.get_person(person_id) is None:
        raise HTTPException(status_code=404, detail="Person not found")

    store.delete_person(person_id)

    return RedirectResponse(
        "/people",
        status_code=303,
    )
