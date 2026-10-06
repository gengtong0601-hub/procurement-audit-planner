"""Local Python web application; the same harness powers both UI and CLI."""

import fcntl
import io
import os
import re
import uuid
import zipfile
from contextlib import contextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from starlette.middleware.trustedhost import TrustedHostMiddleware

from procurement_audit.demo import create_demo
from procurement_audit.models import Decisions, Signoff
from procurement_audit.storage import WorkflowError
from procurement_audit.workflow import (
    build_pack,
    case_status,
    extract_rules,
    run_analysis,
    save_decisions,
    sign_off,
)

PACKAGE = Path(__file__).resolve().parent


def create_app(case_root: Path | None = None):
    root = (case_root or Path(os.getenv("AUDIT_CASES_DIR", ".audit-cases"))).resolve()
    root.mkdir(parents=True, exist_ok=True)
    app = FastAPI(title="Procurement Audit Planner", version="0.1.0")
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "testserver"]
    )
    app.mount("/static", StaticFiles(directory=PACKAGE / "static"), name="static")
    templates = Jinja2Templates(directory=PACKAGE / "templates")

    @app.middleware("http")
    async def browser_safety(request: Request, call_next):
        if request.method in {"POST", "PUT", "DELETE"}:
            origin = request.headers.get("origin")
            if origin and origin != str(request.base_url).rstrip("/"):
                return JSONResponse(
                    {"detail": "Cross-origin writes are not allowed."}, status_code=403
                )
            if (
                request.headers.get("content-length", "0").isdigit()
                and int(request.headers.get("content-length", "0")) > 2_000_000
            ):
                return JSONResponse({"detail": "Request exceeds 2 MB."}, status_code=413)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'self'"
        )
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(WorkflowError)
    async def workflow_error(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=409)

    @app.exception_handler(ValidationError)
    async def source_error(request, exc):
        return JSONResponse(
            {"detail": "Invalid source or artifact data: " + str(exc)}, status_code=422
        )

    def case_path(case_id):
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", case_id):
            raise WorkflowError("Invalid case identifier.")
        path = (root / case_id).resolve()
        if not path.is_relative_to(root) or not path.is_dir():
            raise WorkflowError("Case does not exist.")
        return path

    @contextmanager
    def locked(case):
        with (case / ".workflow.lock").open("a") as file:
            fcntl.flock(file, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(file, fcntl.LOCK_UN)

    @app.get("/", response_class=HTMLResponse)
    def home(request: Request):
        return templates.TemplateResponse(request=request, name="index.html")

    @app.get("/health")
    def health():
        return {"status": "ok", "application": "procurement-audit-planner"}

    @app.get("/api/cases")
    def list_cases():
        return {
            "cases": sorted(
                p.name for p in root.iterdir() if (p / "inputs/manifest.json").is_file()
            )
        }

    @app.post("/api/cases/demo", status_code=201)
    def demo():
        case_id = "demo-" + uuid.uuid4().hex[:12]
        case = root / case_id
        create_demo(case)
        with locked(case):
            extract_rules(case)
            run_analysis(case)
        return {"case_id": case_id, **case_status(case)}

    @app.get("/api/cases/{case_id}")
    def status(case_id: str):
        case = case_path(case_id)
        with locked(case):
            return {"case_id": case_id, **case_status(case)}

    @app.post("/api/cases/{case_id}/decisions")
    def decide(case_id: str, decisions: Decisions):
        case = case_path(case_id)
        with locked(case):
            save_decisions(case, decisions)
        return {"status": "saved", "next": "plan"}

    @app.post("/api/cases/{case_id}/plan")
    def plan(case_id: str):
        case = case_path(case_id)
        with locked(case):
            build_pack(case)
            return case_status(case)

    @app.post("/api/cases/{case_id}/sign-off")
    def signoff(case_id: str, decision: Signoff):
        case = case_path(case_id)
        with locked(case):
            sign_off(case, decision)
            return case_status(case)

    @app.get("/api/cases/{case_id}/files/{filename}")
    def artifact(case_id: str, filename: str):
        case = case_path(case_id)
        if not re.fullmatch(r"[a-z-]+\.(md|json)", filename):
            raise WorkflowError("Invalid artifact name.")
        path = (case / "outputs" / filename).resolve()
        if not path.is_relative_to(case / "outputs") or not path.is_file():
            raise WorkflowError("Artifact does not exist.")
        return Response(path.read_bytes(), media_type="text/plain; charset=utf-8")

    @app.get("/api/cases/{case_id}/download")
    def download(case_id: str):
        case = case_path(case_id)
        data = io.BytesIO()
        with locked(case), zipfile.ZipFile(data, "w", zipfile.ZIP_DEFLATED) as archive:
            state = case_status(case)
            if state["stale"]:
                raise WorkflowError(
                    "The case contains stale artifacts; rerun the required stage before export."
                )
            for filename in state["files"]:
                path = (case / "outputs" / filename).resolve()
                if not path.is_relative_to(case / "outputs"):
                    raise WorkflowError("Artifact path escapes the output directory.")
                archive.write(path, arcname="outputs/" + filename)
        return Response(
            data.getvalue(),
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{case_id}-planning-pack.zip"'},
        )

    return app


app = create_app()
