"""
Authentication Router
Handles user registration, login, and current user information
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from datetime import timedelta, datetime
import uuid
import logging

from database import get_db
from models import User, UserRegister, UserLogin, UserResponse, Token
from auth import get_password_hash, verify_password, create_access_token, get_current_active_user
from audit_logger import log_registration, log_login_success, log_login_failure
from security import SecurityValidator
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api", tags=["authentication"])

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


@router.post("/register", response_model=UserResponse)
@limiter.limit("5/minute")  # Max 5 registration attempts per minute per IP
async def register(request: Request, user: UserRegister, db: Session = Depends(get_db)):
    """Register a new user with input validation and password strength check"""
    # Validate username (prevent XSS and SQL injection)
    validated_username = SecurityValidator.validate_username(user.username)
    
    # Validate email format
    validated_email = SecurityValidator.validate_email(user.email)
    
    # Validate password strength
    SecurityValidator.validate_password_strength(user.password)
    
    # Sanitize full name (prevent XSS)
    validated_full_name = SecurityValidator.sanitize_input(user.full_name, max_length=100)
    
    # Check if username already exists
    existing_user = db.query(User).filter(User.username == validated_username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # Check if email already exists
    existing_email = db.query(User).filter(User.email == validated_email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user
    db_user = User(
        id=str(uuid.uuid4()),
        username=validated_username,
        email=validated_email,
        hashed_password=get_password_hash(user.password),
        full_name=validated_full_name,
        is_active=True,
        is_admin=False,
        created_at=datetime.utcnow()
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Log successful registration
    log_registration(validated_username, request.client.host, "success")
    logger.info(f"New user registered: {validated_username}")
    return db_user


@router.post("/login", response_model=Token)
@limiter.limit("10/minute")  # Max 10 login attempts per minute per IP
async def login(request: Request, user: UserLogin, db: Session = Depends(get_db)):
    """Login and get JWT token with rate limiting"""
    # Find user by username
    db_user = db.query(User).filter(User.username == user.username).first()
    
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        # Log failed login attempt
        log_login_failure(user.username, request.client.host, "invalid_credentials")
        logger.warning(f"Failed login attempt for username: {user.username} from IP: {request.client.host}")
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not db_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    # Update last login
    db_user.last_login = datetime.utcnow()
    db.commit()
    
    # Create access token
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": db_user.id, "username": db_user.username},
        expires_delta=access_token_expires
    )
    
    # Log successful login
    log_login_success(db_user.username, request.client.host)
    logger.info(f"User logged in: {user.username}")
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current user information"""
    return current_user
