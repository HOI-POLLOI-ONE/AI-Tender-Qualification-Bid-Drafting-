from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import shutil, os

from database import get_db
from models import Tender
from schemas import TenderOut
from utils.pdf_praser import extract_text_from_pdf
from services.gemini_client import extract_tender_structure
from utils.security import get_current_user

UPLOAD_DIR = "uploads/tenders"
os.makedirs(UPLOAD_DIR, exist_ok=True)

router = APIRouter()

@router.post("/", response_model=TenderOut)
def upload_tender(file: UploadFile = File(...), db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    raw_text = extract_text_from_pdf(file_path)
    extracted_data = extract_tender_structure(raw_text)

    tender = Tender(
        filename=file.filename,
        raw_text=raw_text,
        extracted_data=extracted_data,
        title=extracted_data.get("title"),
        issuing_authority=extracted_data.get("issuing_authority"),
        deadline=extracted_data.get("deadline"),
        sector=extracted_data.get("sector"),
        estimated_value=extracted_data.get("estimated_value"),
        user_id=current_user.id,
        status="extracted"
    )
    db.add(tender)
    db.commit()
    db.refresh(tender)
    return tender

@router.get("/", response_model=List[TenderOut])
def list_tenders(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return db.query(Tender).filter(Tender.user_id == current_user.id).all()

@router.get("/{tender_id}", response_model=TenderOut)
def get_tender(tender_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    tender = db.query(Tender).filter(Tender.id == tender_id, Tender.user_id == current_user.id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    return tender