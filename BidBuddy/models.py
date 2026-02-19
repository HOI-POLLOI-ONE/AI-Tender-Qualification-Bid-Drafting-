# =============================================================
#  models.py — SQLAlchemy ORM Models (Database Tables)
# =============================================================
#
#  Tables defined here:
#   1. User              — registered users of the platform
#   2. Tender            — uploaded tender PDFs + extracted data
#   3. CompanyProfile    — MSME company details for compliance checks
#   4. ComplianceReport  — scoring results linking a Tender + Company
#   5. BidDraft          — AI-generated bid proposal drafts
#   6. CopilotSession    — conversation history for the AI copilot
# =============================================================

from sqlalchemy import (
    Column, Integer, String, Float, Text,
    DateTime, JSON, Boolean, ForeignKey
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


# ------------------------------------------------------------------
# 1. USER
# ------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, index=True)
    email         = Column(String, unique=True, index=True, nullable=False)
    full_name     = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active     = Column(Boolean, default=True)
    created_at    = Column(DateTime, default=func.now())

    # Relationships — one user can have many companies, tenders, drafts
    company_profiles = relationship("CompanyProfile", back_populates="owner")
    tenders          = relationship("Tender", back_populates="uploaded_by")


# ------------------------------------------------------------------
# 2. TENDER
# ------------------------------------------------------------------
class Tender(Base):
    __tablename__ = "tenders"

    id              = Column(Integer, primary_key=True, index=True)
    user_id         = Column(Integer, ForeignKey("users.id"), nullable=True)
    filename        = Column(String, nullable=False)

    # Raw text pulled out of the PDF by pdfplumber
    raw_text        = Column(Text)

    # Structured JSON extracted by Gemini
    # Shape: { title, issuing_authority, deadline, estimated_value,
    #           eligibility: { min_turnover, years_experience, ... },
    #           documents_required: [...], key_clauses: [...], sector }
    extracted_data  = Column(JSON)

    # Quick summary fields mirrored from extracted_data for easy querying
    title           = Column(String)
    issuing_authority = Column(String)
    deadline        = Column(String)
    sector          = Column(String)
    estimated_value = Column(Float, nullable=True)

    # Processing status: pending | extracted | failed
    status          = Column(String, default="pending")
    error_message   = Column(Text, nullable=True)

    created_at      = Column(DateTime, default=func.now())

    # Relationships
    uploaded_by       = relationship("User", back_populates="tenders")
    compliance_reports = relationship("ComplianceReport", back_populates="tender")
    bid_drafts         = relationship("BidDraft", back_populates="tender")
    copilot_sessions   = relationship("CopilotSession", back_populates="tender")


# ------------------------------------------------------------------
# 3. COMPANY PROFILE
# ------------------------------------------------------------------
class CompanyProfile(Base):
    __tablename__ = "company_profiles"

    id                  = Column(Integer, primary_key=True, index=True)
    user_id             = Column(Integer, ForeignKey("users.id"), nullable=True)

    name                = Column(String, nullable=False)
    registration_number = Column(String)          # Company CIN / MSME Udyam No.
    pan_number          = Column(String)
    gst_number          = Column(String)

    # Financial info
    # Stored in INR Lakhs (e.g., 50.0 = ₹50 Lakhs)
    annual_turnover     = Column(Float)           # Last 3 year average
    net_worth           = Column(Float)
    years_in_operation  = Column(Integer)

    # Certifications as a JSON list:  ["ISO 9001", "MSME Udyam", "GeM Registered"]
    certifications      = Column(JSON, default=list)

    # Sectors the company operates in:  ["IT Services", "Civil Construction"]
    sectors             = Column(JSON, default=list)

    # Past project experience
    # [{ "name": "...", "client": "...", "value": 50.0, "year": 2022 }]
    past_projects       = Column(JSON, default=list)

    # Maximum value of a single past project (in INR Lakhs)
    max_single_project_value = Column(Float, default=0.0)

    # Documents company has ready:  ["GST Certificate", "Audited Balance Sheet"]
    available_documents = Column(JSON, default=list)

    # MSME classification: micro | small | medium
    msme_category       = Column(String)

    created_at          = Column(DateTime, default=func.now())
    updated_at          = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    owner              = relationship("User", back_populates="company_profiles")
    compliance_reports = relationship("ComplianceReport", back_populates="company")


# ------------------------------------------------------------------
# 4. COMPLIANCE REPORT
# ------------------------------------------------------------------
class ComplianceReport(Base):
    __tablename__ = "compliance_reports"

    id         = Column(Integer, primary_key=True, index=True)
    tender_id  = Column(Integer, ForeignKey("tenders.id"), nullable=False)
    company_id = Column(Integer, ForeignKey("company_profiles.id"), nullable=False)

    # 0–100 overall eligibility score
    score      = Column(Float)

    # ELIGIBLE | LIKELY INELIGIBLE | INELIGIBLE
    verdict    = Column(String)

    # List of gap objects:
    # [{ "field": "Turnover", "required": "₹50L", "actual": "₹30L",
    #    "severity": "DISQUALIFYING", "deduction": 40 }]
    gaps       = Column(JSON, default=list)

    # Human-readable action items to fix gaps
    recommendations = Column(JSON, default=list)

    # Full AI analysis text (narrative from Gemini)
    ai_analysis     = Column(Text, nullable=True)

    created_at = Column(DateTime, default=func.now())

    # Relationships
    tender  = relationship("Tender", back_populates="compliance_reports")
    company = relationship("CompanyProfile", back_populates="compliance_reports")


# ------------------------------------------------------------------
# 5. BID DRAFT
# ------------------------------------------------------------------
class BidDraft(Base):
    __tablename__ = "bid_drafts"

    id         = Column(Integer, primary_key=True, index=True)
    tender_id  = Column(Integer, ForeignKey("tenders.id"), nullable=False)
    company_id = Column(Integer, nullable=True)   # Optional link

    # The full AI-generated draft text (Markdown format)
    draft_text = Column(Text)

    # Draft version — allows iterative refinement
    version    = Column(Integer, default=1)

    # Status: generating | ready | failed
    status     = Column(String, default="ready")

    created_at = Column(DateTime, default=func.now())

    # Relationships
    tender = relationship("Tender", back_populates="bid_drafts")


# ------------------------------------------------------------------
# 6. COPILOT SESSION (Conversation History)
# ------------------------------------------------------------------
class CopilotSession(Base):
    __tablename__ = "copilot_sessions"

    id        = Column(Integer, primary_key=True, index=True)
    tender_id = Column(Integer, ForeignKey("tenders.id"), nullable=False)

    # Full conversation as JSON list:
    # [{ "role": "user", "content": "..." },
    #  { "role": "assistant", "content": "..." }]
    messages  = Column(JSON, default=list)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    tender = relationship("Tender", back_populates="copilot_sessions")
