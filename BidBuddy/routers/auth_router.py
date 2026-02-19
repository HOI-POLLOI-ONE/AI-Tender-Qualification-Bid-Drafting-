# =============================================================
#  routers/auth_router.py — User Registration & Login Endpoints
# =============================================================

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from auth import hash_password, verify_password, create_access_token
import models, schemas

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=schemas.UserOut, status_code=201)
def register(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user account.

    - Email must be unique
    - Password is hashed before storage (never stored in plain text)
    """
    # Check if email already in use
    existing = db.query(models.User).filter(models.User.email == user_data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists"
        )

    user = models.User(
        email           = user_data.email,
        full_name       = user_data.full_name,
        hashed_password = hash_password(user_data.password)
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=schemas.Token)
def login(login_data: schemas.LoginRequest, db: Session = Depends(get_db)):
    """
    Login with email + password. Returns a JWT bearer token.

    Use the returned token in the Authorization header for protected routes:
        Authorization: Bearer <token>
    """
    user = db.query(models.User).filter(models.User.email == login_data.email).first()

    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )

    token = create_access_token(data={"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=schemas.UserOut)
def get_me(db: Session = Depends(get_db)):
    """Placeholder — returns info about the authenticated user."""
    # Full implementation uses get_current_user dependency (see main.py)
    raise HTTPException(status_code=401, detail="Provide Authorization: Bearer <token>")
