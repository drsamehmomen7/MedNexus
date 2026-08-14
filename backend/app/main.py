from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.app.modules.medical_document_intelligence.api.deidentification import (
    router as deidentification_router,
)
from backend.app.modules.medical_document_intelligence.api.understanding import (
    router as understanding_router,
)

from backend.app.api.routes.file_upload import (
    router as file_upload_router,
)


app = FastAPI(
    title="MedNexus",
    description="Enterprise Healthcare AI Platform",
    version="0.1.0-alpha",
)


# ============================================================
# API ROUTERS
# ============================================================

app.include_router(deidentification_router)
app.include_router(file_upload_router)
app.include_router(understanding_router)


# ============================================================
# FRONTEND PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]
FRONTEND_DIR = BASE_DIR / "frontend"

ASSETS_DIR = FRONTEND_DIR / "assets"
PRIVACY_ASSETS_DIR = FRONTEND_DIR / "privacy-assets"


# ============================================================
# STATIC ASSETS
# ============================================================

# New MedNexus main homepage assets
if ASSETS_DIR.exists():
    app.mount(
        "/assets",
        StaticFiles(directory=ASSETS_DIR),
        name="assets",
    )


# Existing Clinical Privacy Policy Engine assets
if PRIVACY_ASSETS_DIR.exists():
    app.mount(
        "/privacy-assets",
        StaticFiles(directory=PRIVACY_ASSETS_DIR),
        name="privacy-assets",
    )


# Keep the original /static mount for backward compatibility.
app.mount(
    "/static",
    StaticFiles(directory=FRONTEND_DIR),
    name="static",
)


# ============================================================
# PLATFORM API ROOT
# ============================================================

@app.get("/")
def root():
    return {
        "platform": "MedNexus",
        "module": "Enterprise Medical Document Intelligence",
        "status": "Running",
    }


# ============================================================
# MEDNEXUS MAIN HOMEPAGE
# ============================================================

@app.get("/app")
def application():
    """
    MedNexus main platform homepage.
    """
    return FileResponse(
        FRONTEND_DIR / "index.html"
    )


@app.get("/styles.css")
def homepage_styles():
    return FileResponse(
        FRONTEND_DIR / "styles.css",
        media_type="text/css",
    )


@app.get("/app.js")
def homepage_javascript():
    return FileResponse(
        FRONTEND_DIR / "app.js",
        media_type="application/javascript",
    )


# ============================================================
# CLINICAL PRIVACY POLICY ENGINE
# ============================================================

@app.get("/privacy")
def privacy_engine():
    """
    Existing approved Clinical Privacy Policy Engine interface.
    """
    return FileResponse(
        FRONTEND_DIR / "privacy.html"
    )


@app.get("/privacy-styles.css")
def privacy_styles():
    return FileResponse(
        FRONTEND_DIR / "privacy-styles.css",
        media_type="text/css",
    )


# ============================================================
# MEDICAL DOCUMENT UNDERSTANDING & RECOGNITION
# ============================================================

@app.get("/understanding")
def understanding_application():
    return FileResponse(FRONTEND_DIR / "understanding.html")


@app.get("/understanding-styles.css")
def understanding_styles():
    return FileResponse(
        FRONTEND_DIR / "understanding-styles.css",
        media_type="text/css",
    )


@app.get("/understanding.js")
def understanding_javascript():
    return FileResponse(
        FRONTEND_DIR / "understanding.js",
        media_type="application/javascript",
    )


@app.get("/progressive-result.js")
def progressive_result_javascript():
    return FileResponse(
        FRONTEND_DIR / "progressive-result.js",
        media_type="application/javascript",
    )
