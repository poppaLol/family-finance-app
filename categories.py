from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from finance_app.models import Category


router = APIRouter(prefix="/categories", tags=["categories"])
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def category_list(request: Request):
    store = request.app.state.store

    return templates.TemplateResponse(
        request=request,
        name="categories/list.html",
        context={"categories": store.list_categories()},
    )


@router.get("/create", response_class=HTMLResponse)
async def category_create(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="categories/form.html",
        context={
            "form": None,
            "errors": [],
            "title": "Add Category",
            "submit_label": "Save Category",
        },
    )


@router.post("/create")
async def category_create_post(
    request: Request,
    name: Annotated[str, Form()],
):
    store = request.app.state.store
    store.save_category(Category(name=name))

    return RedirectResponse(
        "/categories",
        status_code=303,
    )


@router.get("/{category_id}/edit", response_class=HTMLResponse)
async def category_edit(category_id: int, request: Request):
    store = request.app.state.store
    category = store.get_category(category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")

    return templates.TemplateResponse(
        request=request,
        name="categories/form.html",
        context={
            "form": category["props"],
            "errors": [],
            "title": "Edit Category",
            "submit_label": "Update Category",
        },
    )


@router.post("/{category_id}/edit")
async def category_edit_post(
    category_id: int,
    request: Request,
    name: Annotated[str, Form()],
):
    store = request.app.state.store
    if store.get_category(category_id) is None:
        raise HTTPException(status_code=404, detail="Category not found")

    store.update_category(category_id, Category(name=name))

    return RedirectResponse(
        "/categories",
        status_code=303,
    )


@router.post("/{category_id}/delete")
async def category_delete(category_id: int, request: Request):
    store = request.app.state.store
    if store.get_category(category_id) is None:
        raise HTTPException(status_code=404, detail="Category not found")

    store.delete_category(category_id)

    return RedirectResponse(
        "/categories",
        status_code=303,
    )
