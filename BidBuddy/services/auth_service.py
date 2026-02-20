from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict

from database import get_db
from models import CopilotSession, Tender
from schemas import CopilotSessionOut, CopilotMessage
from ai_copilot import copilot_answer
from utils.security import get_current_user

router = APIRouter()

@router.post("/{tender_id}", response_model=CopilotSessionOut)
def send_copilot_message(tender_id: int, message: CopilotMessage, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")

    # get last session or create new
    session = db.query(CopilotSession).filter(CopilotSession.tender_id == tender_id).order_by(CopilotSession.id.desc()).first()
    if not session:
        session = CopilotSession(tender_id=tender_id, messages=[])
    session.messages.append(message.dict())

    response_text = copilot_answer(tender.extracted_data, message.content, session.messages)
    session.messages.append({"role": "assistant", "content": response_text})

    db.add(session)
    db.commit()
    db.refresh(session)
    return session

@router.get("/{tender_id}", response_model=CopilotSessionOut)
def get_copilot_session(tender_id: int, db: Session = Depends(get_db)):
    session = db.query(CopilotSession).filter(CopilotSession.tender_id == tender_id).order_by(CopilotSession.id.desc()).first()
    if not session:
        raise HTTPException(status_code=404, detail="No session found")
    return session