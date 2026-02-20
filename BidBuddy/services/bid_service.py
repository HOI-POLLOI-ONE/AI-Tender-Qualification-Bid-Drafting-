from sqlalchemy.orm import Session
import models
from ai_copilot import generate_bid_draft

def create_bid(db: Session, tender_id: int, company_id: int):
    tender = db.query(models.Tender).filter(models.Tender.id==tender_id).first()
    company = db.query(models.CompanyProfile).filter(models.CompanyProfile.id==company_id).first()
    draft_text = generate_bid_draft(tender.extracted_data, company.__dict__)
    bid = models.BidDraft(
        tender_id=tender_id,
        company_id=company_id,
        draft_text=draft_text,
        status="ready"
    )
    db.add(bid)
    db.commit()
    db.refresh(bid)
    return bid

def get_bid(db: Session, bid_id: int):
    return db.query(models.BidDraft).filter(models.BidDraft.id==bid_id).first()

def list_bids(db: Session, tender_id: int = None):
    query = db.query(models.BidDraft)
    if tender_id:
        query = query.filter(models.BidDraft.tender_id==tender_id)
    return query.all()