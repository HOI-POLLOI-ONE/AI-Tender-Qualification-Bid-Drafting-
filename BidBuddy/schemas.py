from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict

# ----------------- User Schemas -----------------
class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str

class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    is_active: bool

    class Config:
        orm_mode = True

# ----------------- Company Schemas -----------------
class CompanyProfileCreate(BaseModel):
    name: str
    registration_number: Optional[str] = None
    pan_number: Optional[str] = None
    gst_number: Optional[str] = None
    annual_turnover: Optional[float] = None
    net_worth: Optional[float] = None
    years_in_operation: Optional[int] = None
    certifications: Optional[List[str]] = []
    sectors: Optional[List[str]] = []
    past_projects: Optional[List[Dict]] = []
    msme_category: Optional[str] = None
    available_documents: Optional[List[str]] = []

class CompanyProfileOut(CompanyProfileCreate):
    id: int
    user_id: int

    class Config:
        orm_mode = True

# ----------------- Tender Schemas -----------------
class TenderCreate(BaseModel):
    filename: str
    raw_text: Optional[str] = None

class TenderOut(BaseModel):
    id: int
    title: Optional[str]
    issuing_authority: Optional[str]
    deadline: Optional[str]
    sector: Optional[str]
    estimated_value: Optional[float]

    class Config:
        orm_mode = True

# ----------------- Compliance Report Schemas -----------------
class ComplianceReportOut(BaseModel):
    id: int
    score: float
    verdict: str
    gaps: List[Dict]
    recommendations: List[Dict]
    ai_analysis: Optional[str]

    class Config:
        orm_mode = True

# ----------------- Bid Draft Schemas -----------------
class BidDraftOut(BaseModel):
    id: int
    draft_text: str
    version: int
    status: str

    class Config:
        from_attributes= True

# ----------------- Copilot -----------------
class CopilotMessage(BaseModel):
    role: str
    content: str

class CopilotSessionOut(BaseModel):
    id: int
    messages: List[CopilotMessage]

    class Config:
        from_attributes = True