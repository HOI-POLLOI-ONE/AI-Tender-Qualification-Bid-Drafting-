from sqlalchemy.orm import Session
import models, schemas

def create_company(db: Session, company: schemas.CompanyCreate, user_id: int):
    db_company = models.CompanyProfile(user_id=user_id, **company.dict())
    db.add(db_company)
    db.commit()
    db.refresh(db_company)
    return db_company

def get_company(db: Session, company_id: int):
    return db.query(models.CompanyProfile).filter(models.CompanyProfile.id==company_id).first()

def list_companies(db: Session, user_id: int = None):
    query = db.query(models.CompanyProfile)
    if user_id:
        query = query.filter(models.CompanyProfile.user_id==user_id)
    return query.all()

def update_company(db: Session, company_id: int, updates: dict):
    db_company = db.query(models.CompanyProfile).filter(models.CompanyProfile.id==company_id).first()
    for key, value in updates.items():
        setattr(db_company, key, value)
    db.commit()
    db.refresh(db_company)
    return db_company

def delete_company(db: Session, company_id: int):
    db_company = db.query(models.CompanyProfile).filter(models.CompanyProfile.id==company_id).first()
    db.delete(db_company)
    db.commit()
    return True