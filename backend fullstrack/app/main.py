from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, HttpUrl
import asyncio

from .scraper import scrape_url


class ScrapeRequest(BaseModel):
    url: HttpUrl


app = FastAPI(title="Lyftr Scraper", version="0.1.0")

# Simple CORS setup so the browser is allowed to call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="app/templates")


@app.get("/healthz")
async def healthcheck():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    # This serves the HTML from FastAPI at http://localhost:8000/
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/scrape")
async def scrape(payload: ScrapeRequest):
    # This is called by the JavaScript fetch('/scrape') on the page.
    try:
        result = await scrape_url(str(payload.url))
    except Exception as exc:  # pragma: no cover - defensive guard
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return JSONResponse(content=result)

