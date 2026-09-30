import logging
import os

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402

from .db import init_db  # noqa: E402
from .routes import auth, cases, flags, sources  # noqa: E402
from .seed import seed_users  # noqa: E402

log = logging.getLogger("trusttrail")

from contextlib import asynccontextmanager  # noqa: E402


@asynccontextmanager
async def lifespan(_app):
    init_db()
    seed_users()
    yield


app = FastAPI(title="TrustTrail", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Content-Type"],
)


@app.exception_handler(Exception)
async def no_stack_traces(request: Request, exc: Exception):
    log.exception("Unhandled error on %s", request.url.path)
    return JSONResponse({"detail": "Something went wrong."}, status_code=500)


for r in (auth.router, cases.router, sources.router, flags.router):
    app.include_router(r, prefix="/api")


# Production: serve the built frontend from the same origin (Cloud Run).
# Only files inside frontend/dist are reachable; unknown paths return index.html.
_DIST = os.getenv("FRONTEND_DIST", os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist"))
if os.path.isdir(_DIST):
    from fastapi.responses import FileResponse  # noqa: E402
    from fastapi.staticfiles import StaticFiles  # noqa: E402

    _DIST = os.path.realpath(_DIST)
    app.mount("/assets", StaticFiles(directory=os.path.join(_DIST, "assets")), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path.startswith("api/"):
            return JSONResponse({"detail": "Not found"}, status_code=404)
        return FileResponse(os.path.join(_DIST, "index.html"))
