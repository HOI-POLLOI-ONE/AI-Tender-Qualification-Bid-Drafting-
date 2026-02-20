from sqlalchemy.orm import Session
import models, schemas
from ai_copilot import extract_tender_structure

def upload_tender(db: Session, filename: str, raw_text: str, user_id: int):
    extracted = extract_tender_structure(raw_text)
    tender = models.Tender(
        user_id=user_id,
        filename=filename,
        raw_text=raw_text,
        extracted_data=extracted,
        title=extracted.get("title"),
        issuing_authority=extracted.get("issuing_authority"),
        deadline=extracted.get("deadline"),
        sector=extracted.get("sector"),
        estimated_value=extracted.get("estimated_value"),
        status="extracted"
    )
    db.add(tender)
    db.commit()
    db.refresh(tender)
    return tender

def get_tender(db: Session, tender_id: int):
    return db.query(models.Tender).filter(models.Tender.id==tender_id).first()

def list_tenders(db: Session, user_id: int = None):
    query = db.query(models.Tender)
    if user_id:
        query = query.filter(models.Tender.user_id==user_id)
    return query.all()

def update_tender(db: Session, tender_id: int, updates: dict):
    tender = db.query(models.Tender).filter(models.Tender.id==tender_id).first()
    for key, value in updates.items():
        setattr(tender, key, value)
    db.commit()
    db.refresh(tender)
    return tender

def delete_tender(db: Session, tender_id: int):
    tender = db.query(models.Tender).filter(models.Tender.id==tender_id).first()
    db.delete(tender)
    db.commit()
    return True