from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict

from database import get_db
from models import ComplianceReport, Tender, CompanyProfile
from schemas import ComplianceReportOut
from ai_copilot import analyze_compliance_gaps
from utils.security import get_current_user

router = APIRouter()

@router.post("/{tender_id}/{company_id}", response_model=ComplianceReportOut)
def create_compliance_report(tender_id: int, company_id: int, gaps: List[Dict], db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    company = db.query(CompanyProfile).filter(CompanyProfile.id == company_id).first()
    if not tender or not company:
        raise HTTPException(status_code=404, detail="Tender or Company not found")

    ai_analysis = analyze_compliance_gaps(tender.extracted_data, company.__dict__, gaps)

    report = ComplianceReport(
        tender_id=tender_id,
        company_id=company_id,
        score=0,  # initial, can calculate separately
        verdict="Pending",
        gaps=gaps,
        recommendations=[],
        ai_analysis=ai_analysis
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report

@router.get("/{tender_id}/{company_id}", response_model=ComplianceReportOut)
def get_compliance_report(tender_id: int, company_id: int, db: Session = Depends(get_db)):
    report = db.query(ComplianceReport).filter(ComplianceReport.tender_id == tender_id, ComplianceReport.company_id == company_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report