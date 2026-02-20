from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models import CompanyProfile
from schemas import CompanyProfileCreate, CompanyProfileOut
from utils.security import get_current_user  # optional, implement JWT auth

router = APIRouter()

@router.post("/", response_model=CompanyProfileOut)
def create_company(profile: CompanyProfileCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    company = CompanyProfile(**profile.dict(), user_id=current_user.id)
    db.add(company)
    db.commit()
    db.refresh(company)
    return company

@router.get("/", response_model=List[CompanyProfileOut])
def list_companies(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return db.query(CompanyProfile).filter(CompanyProfile.user_id == current_user.id).all()

@router.get("/{company_id}", response_model=CompanyProfileOut)
def get_company(company_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    company = db.query(CompanyProfile).filter(CompanyProfile.id == company_id, CompanyProfile.user_id == current_user.id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company

@router.put("/{company_id}", response_model=CompanyProfileOut)
def update_company(company_id: int, profile: CompanyProfileCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    company = db.query(CompanyProfile).filter(CompanyProfile.id == company_id, CompanyProfile.user_id == current_user.id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    for key, value in profile.dict().items():
        setattr(company, key, value)
    db.commit()
    db.refresh(company)
    return company

@router.delete("/{company_id}")
def delete_company(company_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    company = db.query(CompanyProfile).filter(CompanyProfile.id == company_id, CompanyProfile.user_id == current_user.id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    db.delete(company)
    db.commit()
    return {"detail": "Company deleted"}