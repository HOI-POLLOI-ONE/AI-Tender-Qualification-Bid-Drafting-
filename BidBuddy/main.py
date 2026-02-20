from fastapi import FastAPI
from database import Base, engine
from routers import (
    auth_router,
    company_router,
    tender_router,
    compliance_router,
    bid_router,
    copilot_router
)

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Tender Intelligence & Bid Copilot")

# Routers
app.include_router(auth_router.router, prefix="/auth", tags=["Authentication"])
app.include_router(company_router.router, prefix="/company", tags=["Company"])
app.include_router(tender_router.router, prefix="/tender", tags=["Tender"])
app.include_router(compliance_router.router, prefix="/compliance", tags=["Compliance"])
app.include_router(bid_router.router, prefix="/bid", tags=["Bid Drafts"])
app.include_router(copilot_router.router, prefix="/copilot", tags=["AI Copilot"])