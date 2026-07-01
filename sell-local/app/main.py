"""Sell Local — FastAPI app (Milestones M0 + M1: browse + search).

Public, server-rendered routes only. Intake, LLM parsing, and the admin queue
(M2/M3) are intentionally not built here.
"""
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import repository as repo
from .config import CONTACT_MODE, PAGE_SIZE
from .db import connect, init_db
from .timeutil import to_display, to_display_date

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="Sell Local", docs_url=None, redoc_url=None)

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
# Expose config + time helpers to every template.
templates.env.globals["CONTACT_MODE"] = CONTACT_MODE
templates.env.filters["display_dt"] = to_display
templates.env.filters["display_date"] = to_display_date

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# --- DB lifecycle -----------------------------------------------------------
@app.on_event("startup")
def _startup() -> None:
    # Ensure schema exists so the app is runnable even before an explicit init.
    conn = connect()
    try:
        init_db(conn)
    finally:
        conn.close()


def get_db():
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


# --- helpers ----------------------------------------------------------------
def _is_htmx(request: Request) -> bool:
    return request.headers.get("HX-Request") == "true"


@app.exception_handler(StarletteHTTPException)
async def _http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return templates.TemplateResponse(
            "404.html", {"request": request}, status_code=404
        )
    raise exc


# --- routes -----------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def landing(request: Request, conn=Depends(get_db)):
    communities = repo.list_active_communities(conn)
    return templates.TemplateResponse(
        "index.html", {"request": request, "communities": communities}
    )


@app.get("/c/{slug}", response_class=HTMLResponse)
def community_browse(
    request: Request,
    slug: str,
    q: str = Query("", description="Free-text search over title+description"),
    page: int = Query(1, ge=1),
    conn=Depends(get_db),
):
    community = repo.get_community_by_slug(conn, slug)
    if community is None:
        raise StarletteHTTPException(status_code=404)

    listings, total = _fetch_listings(conn, community["id"], q, page)

    ctx = {
        "request": request,
        "community": community,
        "q": q,
        "page": page,
        "page_size": PAGE_SIZE,
        "total": total,
        "listings": listings,
    }
    # htmx search-as-you-type swaps only the results fragment.
    template = "_listings.html" if _is_htmx(request) else "community.html"
    return templates.TemplateResponse(template, ctx)


@app.get("/c/{slug}/search", response_class=HTMLResponse)
def community_search_fragment(
    request: Request,
    slug: str,
    q: str = Query(""),
    page: int = Query(1, ge=1),
    conn=Depends(get_db),
):
    """Explicit htmx partial endpoint (Architecture route table)."""
    community = repo.get_community_by_slug(conn, slug)
    if community is None:
        raise StarletteHTTPException(status_code=404)
    listings, total = _fetch_listings(conn, community["id"], q, page)
    return templates.TemplateResponse(
        "_listings.html",
        {
            "request": request,
            "community": community,
            "q": q,
            "page": page,
            "page_size": PAGE_SIZE,
            "total": total,
            "listings": listings,
        },
    )


@app.get("/listing/{listing_id}", response_class=HTMLResponse)
def listing_detail(request: Request, listing_id: int, conn=Depends(get_db)):
    listing = repo.get_public_listing(conn, listing_id)
    if listing is None:
        raise StarletteHTTPException(status_code=404)
    community = conn.execute(
        "SELECT * FROM community WHERE id = ?", (listing["community_id"],)
    ).fetchone()
    return templates.TemplateResponse(
        "listing.html",
        {"request": request, "listing": listing, "community": community},
    )


@app.get("/api/listings/{listing_id}/contact", response_class=HTMLResponse)
def reveal_contact(request: Request, listing_id: int, conn=Depends(get_db)):
    """Reveal-contact endpoint. Exists so contact-gating is a config flip, not a
    rebuild (Architecture §4). In 'public' mode this simply returns the number;
    when CONTACT_MODE='gated' the render_contact partial's button targets this.
    """
    listing = repo.get_public_listing(conn, listing_id)
    if listing is None:
        raise StarletteHTTPException(status_code=404)
    return templates.TemplateResponse(
        "_contact_value.html", {"request": request, "listing": listing}
    )


# --- internal ---------------------------------------------------------------
def _fetch_listings(conn, community_id: int, q: str, page: int):
    offset = (page - 1) * PAGE_SIZE
    if q and q.strip():
        listings = repo.search_public_listings(
            conn, community_id, q, PAGE_SIZE, offset
        )
        total = len(listings)  # cheap; search result counts are small at this scale
    else:
        listings = repo.list_public_listings(conn, community_id, PAGE_SIZE, offset)
        total = repo.count_public_listings(conn, community_id)
    return listings, total
