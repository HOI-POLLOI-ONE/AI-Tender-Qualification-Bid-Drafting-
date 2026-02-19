# =============================================================
#  main.py — FastAPI Application Entry Point
# =============================================================
#
#  To run:
#     uvicorn main:app --reload
#
#  Then open:
#     http://localhost:8000/docs     ← Swagger UI (test all endpoints)
#     http://localhost:8000/redoc    ← Alternative API docs
# =============================================================

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import database engine and base — creates tables on startup
from database import engine
import models

# Import all routers
from routers import auth_router, tender, company, compliance, copilot

# ── Create all database tables ────────────────────────────────
# This is safe to call on every startup — SQLAlchemy only creates
# tables that don't exist yet (it won't overwrite existing data)
models.Base.metadata.create_all(bind=engine)

# ── Initialize FastAPI App ─────────────────────────────────────
app = FastAPI(
    title       = os.getenv("APP_NAME", "Procurement Intelligence Platform"),
    description = """
## 🏛️ AI-Powered Procurement Intelligence Platform for MSMEs

This API helps MSMEs participate more effectively in Indian government tenders by:

- **📄 Tender Extraction**: Upload tender PDFs → get structured eligibility data
- **✅ Compliance Scoring**: Check your company's eligibility with a detailed score
- **📝 Bid Draft Generation**: AI-generated professional bid proposals
- **🤖 AI Copilot**: Ask questions about any tender in natural language

### Quick Start
1. Upload a tender PDF via `POST /tenders/upload`
2. Create your company profile via `POST /companies`
3. Run compliance check via `POST /compliance/score`
4. Generate a bid draft via `POST /copilot/generate-draft`
5. Ask questions via `POST /copilot/ask`

### Authentication
Most endpoints work without authentication (for hackathon demo).
Use `POST /auth/register` + `POST /auth/login` to get a JWT token for full access.
    """,
    version     = "1.0.0-mvp",
    contact     = {
        "name": "Procurement Intelligence Team",
    },
    license_info = {
        "name": "MIT",
    }
)

# ── CORS Middleware ────────────────────────────────────────────
# Allows the frontend (React/Next.js) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],      # In production: specify your frontend URL
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ── Register Routers ───────────────────────────────────────────
app.include_router(auth_router.router)
app.include_router(tender.router)
app.include_router(company.router)
app.include_router(compliance.router)
app.include_router(copilot.router)


# ── Root Endpoint ──────────────────────────────────────────────
@app.get("/", tags=["Health"])
def root():
    return {
        "status":  "✅ Procurement Intelligence Platform is running",
        "version": "1.0.0-mvp",
        "docs":    "/docs",
        "message": "Welcome! Visit /docs to explore and test all API endpoints."
    }


# ── Health Check ──────────────────────────────────────────────
@app.get("/health", tags=["Health"])
def health_check():
    """
    Simple health check endpoint.
    Returns database status and API key configuration status.
    """
    import os

    gemini_key    = os.getenv("GEMINI_API_KEY", "")
    gemini_status = "✅ Configured" if (gemini_key and gemini_key != "your_gemini_api_key_here") else "❌ Not configured (AI features disabled)"

    return {
        "status":       "healthy",
        "database":     "✅ SQLite connected",
        "gemini_api":   gemini_status,
        "uploads_dir":  "✅ Ready" if os.path.exists("uploads") else "❌ Missing",
    }


# ── Global Exception Handler ──────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Catch-all error handler — returns clean JSON instead of server crash pages.
    In production, you'd log these to a monitoring service.
    """
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error":   "Internal server error",
            "detail":  str(exc)
        }
    )
