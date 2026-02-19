# =============================================================
#  routers/copilot.py — AI Copilot & Bid Draft Endpoints
# =============================================================

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from database import get_db
import models, schemas
from services import gemini_client

router = APIRouter(prefix="/copilot", tags=["AI Copilot & Draft Generation"])


# ── POST /copilot/ask ──────────────────────────────────────────
@router.post("/ask", response_model=schemas.CopilotResponse)
def ask_copilot(
    request: schemas.CopilotAskRequest,
    db: Session = Depends(get_db)
):
    """
    Ask the AI copilot a question about a specific tender.

    The copilot maintains conversation history within a session,
    allowing multi-turn Q&A about the same tender.

    Examples of questions:
    - "What is the minimum turnover required?"
    - "Do we need ISO certification for this tender?"
    - "What documents do I need to submit?"
    - "Can we apply as a consortium?"
    - "What is the EMD amount and format?"
    """

    # ── Fetch tender ──
    tender = db.query(models.Tender).filter(
        models.Tender.id == request.tender_id
    ).first()

    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    if not tender.extracted_data:
        raise HTTPException(
            status_code=422,
            detail="Tender has not been extracted yet. Cannot answer questions about it."
        )

    # ── Get or create session ──
    if request.session_id:
        session = db.query(models.CopilotSession).filter(
            models.CopilotSession.id == request.session_id
        ).first()
        if not session:
            raise HTTPException(status_code=404, detail="Copilot session not found")
    else:
        # Start a new session
        session = models.CopilotSession(
            tender_id = request.tender_id,
            messages  = []
        )
        db.add(session)
        db.commit()
        db.refresh(session)

    # ── Add user message to history ──
    messages = list(session.messages or [])
    messages.append({"role": "user", "content": request.question})

    # ── Get AI answer ──
    answer = gemini_client.copilot_answer(
        tender_data          = tender.extracted_data,
        question             = request.question,
        conversation_history = messages[:-1]   # Exclude the just-added message
    )

    # ── Add AI response to history ──
    messages.append({"role": "assistant", "content": answer})

    # ── Save updated session ──
    session.messages = messages
    db.commit()

    return schemas.CopilotResponse(
        session_id   = session.id,
        answer       = answer,
        conversation = [
            schemas.CopilotMessage(role=m["role"], content=m["content"])
            for m in messages
        ]
    )


# ── GET /copilot/sessions/{session_id} ───────────────────────
@router.get("/sessions/{session_id}", response_model=schemas.CopilotResponse)
def get_session(session_id: int, db: Session = Depends(get_db)):
    """Get the full conversation history of a copilot session."""
    session = db.query(models.CopilotSession).filter(
        models.CopilotSession.id == session_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = session.messages or []
    last_answer = messages[-1]["content"] if messages and messages[-1]["role"] == "assistant" else ""

    return schemas.CopilotResponse(
        session_id   = session.id,
        answer       = last_answer,
        conversation = [
            schemas.CopilotMessage(role=m["role"], content=m["content"])
            for m in messages
        ]
    )


# ── POST /copilot/generate-draft ──────────────────────────────
@router.post("/generate-draft", response_model=schemas.BidDraftOut, status_code=201)
def generate_draft(
    request: schemas.DraftRequest,
    db: Session = Depends(get_db)
):
    """
    Generate a structured bid proposal draft.

    Uses the tender's extracted data and the company's profile to create
    a complete, professional bid proposal in Markdown format.

    The draft includes:
    - Cover letter
    - Company overview
    - Technical compliance statement
    - Scope understanding
    - Relevant past experience
    - Team deployment plan
    - Quality assurance commitment
    - Document index
    """

    # ── Fetch tender ──
    tender = db.query(models.Tender).filter(
        models.Tender.id == request.tender_id
    ).first()
    if not tender or not tender.extracted_data:
        raise HTTPException(
            status_code=404,
            detail="Tender not found or not yet extracted"
        )

    # ── Fetch company ──
    company = db.query(models.CompanyProfile).filter(
        models.CompanyProfile.id == request.company_id
    ).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company profile not found")

    company_dict = {
        "name":              company.name,
        "annual_turnover":   company.annual_turnover,
        "years_in_operation": company.years_in_operation,
        "certifications":    company.certifications or [],
        "sectors":           company.sectors or [],
        "past_projects":     company.past_projects or [],
        "msme_category":     company.msme_category,
        "registration_number": company.registration_number,
        "gst_number":        company.gst_number,
    }

    # ── Generate draft ──
    draft_text = gemini_client.generate_bid_draft(
        tender_data        = tender.extracted_data,
        company_data       = company_dict,
        additional_context = request.additional_context
    )

    # ── Check for existing drafts (for versioning) ──
    existing_count = db.query(models.BidDraft).filter(
        models.BidDraft.tender_id == request.tender_id,
        models.BidDraft.company_id == request.company_id
    ).count()

    # ── Save draft ──
    draft = models.BidDraft(
        tender_id  = request.tender_id,
        company_id = request.company_id,
        draft_text = draft_text,
        version    = existing_count + 1,
        status     = "ready"
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)

    return draft


# ── GET /copilot/drafts/{draft_id} ───────────────────────────
@router.get("/drafts/{draft_id}", response_model=schemas.BidDraftOut)
def get_draft(draft_id: int, db: Session = Depends(get_db)):
    """Get a specific bid draft."""
    draft = db.query(models.BidDraft).filter(models.BidDraft.id == draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft


# ── GET /copilot/drafts ───────────────────────────────────────
@router.get("/drafts", response_model=List[schemas.BidDraftOut])
def list_drafts(
    tender_id:  int = None,
    company_id: int = None,
    db: Session = Depends(get_db)
):
    """List all generated bid drafts with optional filtering."""
    query = db.query(models.BidDraft)
    if tender_id:
        query = query.filter(models.BidDraft.tender_id == tender_id)
    if company_id:
        query = query.filter(models.BidDraft.company_id == company_id)
    return query.all()
