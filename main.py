import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from grm_rs import Neo4jSession

import categories
from finance_app.store import FinanceStore
import people
import statements


BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@asynccontextmanager
async def lifespan(app: FastAPI):
    graph = Neo4jSession(
        uri=os.environ["NEO4J_URI"],
        user=os.environ["NEO4J_USER"],
        password=os.environ["NEO4J_PASSWORD"],
    )
    app.state.store = FinanceStore(graph)
    app.state.pending_imports = {}
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(categories.router)
app.include_router(people.router)
app.include_router(statements.router)


@app.get("/")
def home(request: Request):
    store: FinanceStore = request.app.state.store

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"store": store},
    )
