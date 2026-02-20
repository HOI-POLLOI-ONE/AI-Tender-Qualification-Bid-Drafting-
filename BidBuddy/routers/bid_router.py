from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db
from models import BidDraft, Tender, CompanyProfile
from schemas import BidDraftOut
from ai_copilot import generate_bid_draft
from utils.security import get_current_user

router = APIRouter()

@router.post("/{tender_id}/{company_id}", response_model=BidDraftOut)
def create_bid_draft(tender_id: int, company_id: int, additional_context: Optional[str] = None, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    company = db.query(CompanyProfile).filter(CompanyProfile.id == company_id).first()
    if not tender or not company:
        raise HTTPException(status_code=404, detail="Tender or Company not found")

    draft_text = generate_bid_draft(tender.extracted_data, company.__dict__, additional_context)
    draft = BidDraft(tender_id=tender_id, company_id=company_id, draft_text=draft_text)
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return draft

@router.get("/{draft_id}", response_model=BidDraftOut)
def get_bid_draft(draft_id: int, db: Session = Depends(get_db)):
    draft = db.query(BidDraft).filter(BidDraft.id == draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft