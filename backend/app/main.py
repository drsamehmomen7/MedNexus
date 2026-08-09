from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.app.modules.medical_document_intelligence.api.deidentification import (
    router as deidentification_router,
)

from backend.app.api.routes.file_upload import (
    router as file_upload_router,
)

app = FastAPI(
    title="MedNexus",
    description="Enterprise Healthcare AI Platform",
    version="0.1.0-alpha",
)

# -------------------------
# Routers
# -------------------------

app.include_router(deidentification_router)
app.include_router(file_upload_router)

# -------------------------
# Frontend
# -------------------------

BASE_DIR = Path(__file__).resolve().parents[2]
FRONTEND_DIR = BASE_DIR / "frontend"

app.mount(
    "/static",
    StaticFiles(directory=FRONTEND_DIR),
    name="static",
)


@app.get("/")
def root():
    return {
        "platform": "MedNexus",
        "module": "Medical Document Intelligence",
        "status": "Running",
    }


@app.get("/app")
def application():
    return FileResponse(
        FRONTEND_DIR / "index.html"
    )