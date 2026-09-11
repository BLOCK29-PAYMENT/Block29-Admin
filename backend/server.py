from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Form, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import jwt
import bcrypt
import re
import json
import aiofiles
import asyncio
import contextvars
from contextlib import asynccontextmanager

# SQLAlchemy imports
from sqlalchemy import create_engine, Column, String, Text, DateTime, Float, Integer, JSON, Enum as SQLEnum, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker as async_sessionmaker
from sqlalchemy.future import select
from sqlalchemy import text
import aiomysql

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MySQL connection
MYSQL_HOST = os.environ.get('MYSQL_HOST')
MYSQL_PORT = os.environ.get('MYSQL_PORT', '3306')
MYSQL_USER = os.environ.get('MYSQL_USER')
MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD')
MYSQL_DATABASE = os.environ.get('MYSQL_DATABASE')

DATABASE_URL = f"mysql+aiomysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"

# Create async engine
engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True, pool_recycle=3600)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# JWT Configuration - a signing secret must be provided; refuse to start with a guessable default
JWT_SECRET = os.environ.get('JWT_SECRET')
if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET environment variable is not set. Set a strong random secret before starting the server.")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Upload directory
UPLOAD_DIR = ROOT_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Client IP of the request currently being handled (set by middleware, read by audit logging)
_client_ip = contextvars.ContextVar("client_ip", default="unknown")

# ==================== LOGIN RATE LIMITING ====================
# In-memory sliding window per (client_ip, email). Single-instance deployment;
# move to a shared store if the API is ever scaled horizontally.
LOGIN_MAX_FAILURES = 5
LOGIN_WINDOW_SECONDS = 15 * 60
_login_failures: Dict[str, List[float]] = {}

def _rate_limit_key(email: str) -> str:
    return f"{_client_ip.get()}|{email.lower()}"

def login_rate_limited(email: str) -> bool:
    import time
    now = time.time()
    attempts = [t for t in _login_failures.get(_rate_limit_key(email), []) if now - t < LOGIN_WINDOW_SECONDS]
    _login_failures[_rate_limit_key(email)] = attempts
    return len(attempts) >= LOGIN_MAX_FAILURES

def record_login_failure(email: str):
    import time
    now = time.time()
    # Bound the tracker: prune fully-expired keys once the dict grows large,
    # so an attacker cycling emails cannot exhaust memory via the login endpoint.
    if len(_login_failures) > 5000:
        stale = [k for k, ts in _login_failures.items() if not ts or now - max(ts) > LOGIN_WINDOW_SECONDS]
        for k in stale:
            _login_failures.pop(k, None)
    _login_failures.setdefault(_rate_limit_key(email), []).append(now)

def clear_login_failures(email: str):
    _login_failures.pop(_rate_limit_key(email), None)

# ==================== DATABASE HELPER ====================

async def get_db():
    async with async_session() as session:
        yield session

async def execute_query(query: str, params: dict = None):
    """Execute a raw SQL query"""
    async with async_session() as session:
        result = await session.execute(text(query), params or {})
        await session.commit()
        return result

async def fetch_all(query: str, params: dict = None):
    """Fetch all rows from a query"""
    async with async_session() as session:
        result = await session.execute(text(query), params or {})
        rows = result.fetchall()
        columns = result.keys()
        return [dict(zip(columns, row)) for row in rows]

async def fetch_one(query: str, params: dict = None):
    """Fetch one row from a query"""
    async with async_session() as session:
        result = await session.execute(text(query), params or {})
        row = result.fetchone()
        if row:
            columns = result.keys()
            return dict(zip(columns, row))
        return None

async def insert_row(table: str, data: dict):
    """Insert a row into a table"""
    columns = ', '.join(data.keys())
    placeholders = ', '.join([f':{k}' for k in data.keys()])
    query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
    await execute_query(query, data)

async def update_row(table: str, data: dict, where_clause: str, where_params: dict):
    """Update rows in a table"""
    set_clause = ', '.join([f"{k} = :{k}" for k in data.keys()])
    query = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"
    await execute_query(query, {**data, **where_params})

async def delete_row(table: str, where_clause: str, where_params: dict):
    """Delete rows from a table"""
    query = f"DELETE FROM {table} WHERE {where_clause}"
    await execute_query(query, where_params)

def clamp_pagination(page: int, page_size: int, max_page_size: int = 200):
    """Normalize pagination inputs."""
    return max(1, page), min(max(1, page_size), max_page_size)

async def paginated(base_query: str, count_query: str, params: dict, page: int, page_size: int, order_by: str):
    """Run a filtered query with a total count and LIMIT/OFFSET. order_by must be a code-owned literal."""
    total_row = await fetch_one(count_query, params)
    total = total_row["total"] if total_row else 0
    offset = (page - 1) * page_size
    items = await fetch_all(f"{base_query} ORDER BY {order_by} LIMIT {page_size} OFFSET {offset}", params)
    return items, total

# ==================== MODELS ====================

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=120)
    role: str = "READ_ONLY"

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    created_at: str

class MerchantCreate(BaseModel):
    business_name: str = Field(min_length=1, max_length=255)
    dba: Optional[str] = None
    tax_id: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    status: str = "pending"

class MerchantUpdate(BaseModel):
    business_name: Optional[str] = None
    dba: Optional[str] = None
    tax_id: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    status: Optional[str] = None

class TerminalProfileCreate(BaseModel):
    merchant_id: str
    provider: str = "tsys"
    v_number: Optional[str] = None
    merchant_number: Optional[str] = None
    terminal_number: Optional[str] = None
    terminal_status: Optional[str] = None
    bin: Optional[str] = None
    chain: Optional[str] = None
    store_number: Optional[str] = None
    agent_code: Optional[str] = None
    edc_primary: Optional[str] = None
    edc_secondary: Optional[str] = None
    amex_se: Optional[str] = None
    disc_se: Optional[str] = None
    aba: Optional[str] = None
    reimbursement_att: Optional[str] = None
    card_types: Optional[List[str]] = None
    networks: Optional[List[str]] = None
    raw_comments: Optional[str] = None
    provisioning_status: str = "draft"

class TerminalProfileUpdate(BaseModel):
    v_number: Optional[str] = None
    merchant_number: Optional[str] = None
    terminal_number: Optional[str] = None
    terminal_status: Optional[str] = None
    bin: Optional[str] = None
    chain: Optional[str] = None
    store_number: Optional[str] = None
    agent_code: Optional[str] = None
    edc_primary: Optional[str] = None
    edc_secondary: Optional[str] = None
    amex_se: Optional[str] = None
    disc_se: Optional[str] = None
    aba: Optional[str] = None
    reimbursement_att: Optional[str] = None
    card_types: Optional[List[str]] = None
    networks: Optional[List[str]] = None
    raw_comments: Optional[str] = None
    provisioning_status: Optional[str] = None

class VarSheetParsedData(BaseModel):
    """Editable review fields for a parsed VAR sheet.

    Must cover every field the VAR Sheet review form exposes - any field
    missing here is silently dropped on save.
    """
    merchant_name: Optional[str] = None
    merchant_number: Optional[str] = None
    v_number_primary: Optional[str] = None
    v_number_secondary: Optional[str] = None
    terminal_status: Optional[str] = None
    terminal_number: Optional[str] = None
    bin: Optional[str] = None
    agent: Optional[str] = None
    chain: Optional[str] = None
    store_number: Optional[str] = None
    location_number: Optional[str] = None
    street_address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    phone: Optional[str] = None
    country: Optional[str] = None
    currency_code: Optional[str] = None
    time_zone: Optional[str] = None
    time_zone_differential: Optional[str] = None
    visa_mcc: Optional[str] = None
    industry_type: Optional[str] = None
    host_capture_participant: Optional[str] = None
    edc_primary: Optional[str] = None
    edc_secondary: Optional[str] = None
    card_types: Optional[List[str]] = None
    networks: Optional[List[str]] = None
    amex_se: Optional[str] = None
    disc_se: Optional[str] = None
    aba: Optional[str] = None
    reimbursement_att: Optional[str] = None
    raw_comments: Optional[str] = None

class UserStatusUpdate(BaseModel):
    is_active: bool

# ==================== AUDIT LOG HELPER ====================

async def create_audit_log(user_id: str, user_email: str, action: str, resource_type: str, resource_id: str = None, details: dict = None):
    log_entry = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "user_email": user_email,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id or "",
        "details": json.dumps(details or {}),
        "ip_address": _client_ip.get(),
        "timestamp": datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    }
    await insert_row("audit_logs", log_entry)
    return log_entry

# ==================== AUTH HELPERS ====================

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

def create_token(user_id: str, email: str, role: str) -> str:
    payload = {
        "user_id": user_id,
        "email": email,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Deactivation must revoke access immediately, not at token expiry:
    # verify the account still exists and is active on every request.
    # (Role changes still take effect at next login - documented behavior.)
    row = await fetch_one("SELECT is_active FROM users WHERE id = :id", {"id": payload.get("user_id")})
    if not row:
        raise HTTPException(status_code=401, detail="Account no longer exists")
    if row.get("is_active") in (0, False):
        raise HTTPException(status_code=403, detail="Account is deactivated")
    return payload

def require_roles(*allowed_roles):
    async def role_checker(user: dict = Depends(get_current_user)):
        if user["role"] not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return role_checker

VALID_ROLES = ["SUPER_ADMIN", "OPERATIONS", "SUPPORT", "READ_ONLY"]

# ==================== VAR PARSER (TSYS Format) ====================

def parse_var_sheet_text(text: str) -> Dict[str, Any]:
    """Parse TSYS VAR Form / Express Keysheets"""
    parsed = {
        "document_type": "TSYS VAR Form / Express Keysheets",
        "merchant_name": None,
        "merchant_number": None,
        "v_number_primary": None,
        "v_number_secondary": None,
        "terminal_status": None,
        "terminal_number": None,
        "bin": None,
        "agent": None,
        "chain": None,
        "store_number": None,
        "street_address": None,
        "city": None,
        "state": None,
        "postal_code": None,
        "phone": None,
        "country": None,
        "currency_code": None,
        "time_zone": None,
        "visa_mcc": None,
        "industry_type": None,
        "card_types": [],
        "networks": [],
        "edc_primary": None,
        "edc_secondary": None,
        "amex_se": None,
        "disc_se": None,
        "aba": None,
        "reimbursement_att": None,
        "raw_comments": None,
        "confidence_flags": {},
        "extraction_notes": [],
        "confidence_score": 0
    }
    
    text = text.replace('\r', '\n')
    
    # Merchant Name
    for pattern in [r"Merchant\s+Name[:\s]+([A-Za-z0-9\s&.,'\-]+?)(?:\n|Merchant)", r"DBA[:\s]+([A-Za-z0-9\s&.,'\-]+?)(?:\n|$)"]:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            parsed["merchant_name"] = match.group(1).strip()
            parsed["confidence_flags"]["merchant_name"] = "high"
            break
    
    # Merchant Number
    mn_match = re.search(r"Merchant\s*(?:Number|#)?[:\s]*(\d{9,15})", text, re.IGNORECASE)
    if mn_match:
        parsed["merchant_number"] = mn_match.group(1).strip()
        parsed["confidence_flags"]["merchant_number"] = "high"
    
    # V Numbers
    v_matches = re.findall(r"V[\s-]?(?:Number)?[:\s]*(V\d{7})", text, re.IGNORECASE)
    if v_matches:
        parsed["v_number_primary"] = v_matches[0]
        if len(v_matches) > 1:
            parsed["v_number_secondary"] = v_matches[1]
        parsed["confidence_flags"]["v_number"] = "high"
    
    # Terminal Number
    term_match = re.search(r"Terminal\s*#?[:\s]*(\d{4})", text, re.IGNORECASE)
    if term_match:
        parsed["terminal_number"] = term_match.group(1)
        parsed["confidence_flags"]["terminal_number"] = "high"
    
    # BIN
    bin_match = re.search(r"BIN[:\s]*(\d{6})", text, re.IGNORECASE)
    if bin_match:
        parsed["bin"] = bin_match.group(1)
        parsed["confidence_flags"]["bin"] = "high"
    
    # Agent
    agent_match = re.search(r"Agent[:\s]*(\d{6})", text, re.IGNORECASE)
    if agent_match:
        parsed["agent"] = agent_match.group(1)
    
    # Chain
    chain_match = re.search(r"Chain[:\s]*(\d{6})", text, re.IGNORECASE)
    if chain_match:
        parsed["chain"] = chain_match.group(1)
        parsed["confidence_flags"]["chain"] = "high"
    
    # Store Number
    store_match = re.search(r"Store\s*(?:Number|#)?[:\s]*(\d{4})", text, re.IGNORECASE)
    if store_match:
        parsed["store_number"] = store_match.group(1)
        parsed["confidence_flags"]["store_number"] = "high"
    
    # Card Types
    cards = []
    for pattern, card in [(r"VISA", "VISA"), (r"MASTER\s*CARD|MC", "MasterCard"), (r"AMERICAN\s*EXPRESS|AMEX", "American Express"), (r"JCB", "JCB"), (r"DISCOVER", "Discover"), (r"ATM|DEBIT", "ATM/Debit")]:
        if re.search(pattern, text, re.IGNORECASE):
            cards.append(card)
    parsed["card_types"] = cards
    if cards:
        parsed["confidence_flags"]["card_types"] = "high"
    
    # Networks
    networks = []
    for pattern, name in [(r"Pulse", "Pulse"), (r"Interlink", "Interlink"), (r"STAR", "STAR"), (r"Maestro", "Maestro"), (r"NYCE", "NYCE"), (r"ACCEL", "ACCEL")]:
        if re.search(pattern, text, re.IGNORECASE) and name not in networks:
            networks.append(name)
    parsed["networks"] = networks
    if networks:
        parsed["confidence_flags"]["networks"] = "high"
    
    # Comments section
    comments_match = re.search(r"Comments.*?[:\s]*(.+?)(?:Please\s*note|Confidential|$)", text, re.IGNORECASE | re.DOTALL)
    if comments_match:
        comments = comments_match.group(1).strip()
        parsed["raw_comments"] = comments[:500]
        
        amex_match = re.search(r"AMEX\s*SE[:\s]*(\d{10})", comments, re.IGNORECASE)
        if amex_match:
            parsed["amex_se"] = amex_match.group(1)
            parsed["confidence_flags"]["amex_se"] = "high"
        
        disc_match = re.search(r"DISC\s*SE[:\s]*(\d{12,15})", comments, re.IGNORECASE)
        if disc_match:
            parsed["disc_se"] = disc_match.group(1)
            parsed["confidence_flags"]["disc_se"] = "high"
        
        aba_match = re.search(r"ABA[:\s]*(\d{9})", comments, re.IGNORECASE)
        if aba_match:
            parsed["aba"] = aba_match.group(1)
            parsed["confidence_flags"]["aba"] = "high"
    
    # Confidence score
    critical_fields = ["merchant_name", "merchant_number", "v_number", "terminal_number", "bin", "chain", "store_number", "card_types", "networks", "aba"]
    found = sum(1 for f in critical_fields if parsed["confidence_flags"].get(f) == "high")
    parsed["confidence_score"] = round((found / len(critical_fields)) * 100, 1)
    
    return parsed

# ==================== APP SETUP ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up - creating database tables...")
    await create_tables()
    yield
    # Shutdown
    logger.info("Shutting down...")

app = FastAPI(
    title="Block29 Admin API",
    description="Internal operations console for the Block29 ecosystem (AsterPOS, Chain29, Agent9): merchants, VAR sheets, terminal tracking, transactions, reports, users, and audit logs.",
    version="1.1.0",
    lifespan=lifespan
)
api_router = APIRouter(prefix="/api")

# X-Forwarded-For is attacker-controlled unless a trusted proxy appends to it.
# TRUSTED_PROXY_HOPS=0 (default) ignores XFF entirely and uses the socket peer;
# set it to the number of trusted proxies in front of the API to use the
# rightmost trustworthy XFF entry. Prevents rate-limit bypass and audit forgery.
TRUSTED_PROXY_HOPS = int(os.environ.get("TRUSTED_PROXY_HOPS", "0"))

@app.middleware("http")
async def capture_client_ip(request, call_next):
    ip = request.client.host if request.client else "unknown"
    if TRUSTED_PROXY_HOPS > 0:
        parts = [p.strip() for p in request.headers.get("x-forwarded-for", "").split(",") if p.strip()]
        if len(parts) >= TRUSTED_PROXY_HOPS:
            ip = parts[-TRUSTED_PROXY_HOPS]
    token = _client_ip.set(ip or "unknown")
    try:
        response = await call_next(request)
    finally:
        _client_ip.reset(token)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Cache-Control", "no-store")
    return response

async def create_tables():
    """Seed the initial SUPER_ADMIN account, only when explicitly configured via env vars."""
    admin_email = os.environ.get('ADMIN_EMAIL')
    admin_password = os.environ.get('ADMIN_PASSWORD')
    if not admin_email or not admin_password:
        logger.info("ADMIN_EMAIL/ADMIN_PASSWORD not set - skipping admin seed")
        return

    admin = await fetch_one("SELECT id FROM users WHERE email = :email", {"email": admin_email})
    if not admin:
        await insert_row("users", {
            "id": str(uuid.uuid4()),
            "email": admin_email,
            "password": hash_password(admin_password),
            "name": "Block29 Admin",
            "role": "SUPER_ADMIN",
            "created_at": datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        })
        logger.info(f"Seeded SUPER_ADMIN account: {admin_email}")
    else:
        logger.info("Admin user already exists")

# ==================== AUTH ENDPOINTS ====================

@api_router.post("/auth/register", response_model=UserResponse)
async def register(user: UserCreate, current_user: dict = Depends(require_roles("SUPER_ADMIN"))):
    existing = await fetch_one("SELECT id FROM users WHERE email = :email", {"email": user.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    if user.role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail="Invalid role")

    user_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

    await insert_row("users", {
        "id": user_id,
        "email": user.email,
        "password": hash_password(user.password),
        "name": user.name,
        "role": user.role,
        "created_at": created_at
    })

    await create_audit_log(current_user["user_id"], current_user["email"], "CREATE", "user", user_id, {"email": user.email, "role": user.role})
    return UserResponse(id=user_id, email=user.email, name=user.name, role=user.role, created_at=created_at)

@api_router.post("/auth/login")
async def login(credentials: UserLogin):
    if login_rate_limited(credentials.email):
        raise HTTPException(status_code=429, detail="Too many failed login attempts. Try again in 15 minutes.")

    user = await fetch_one("SELECT * FROM users WHERE email = :email", {"email": credentials.email})
    if not user or not user.get("password") or not verify_password(credentials.password, user["password"]):
        record_login_failure(credentials.email)
        await create_audit_log("", credentials.email, "LOGIN_FAILED", "user")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if user.get("is_active") in (0, False):
        await create_audit_log(user["id"], user["email"], "LOGIN_FAILED", "user", user["id"], {"reason": "deactivated"})
        raise HTTPException(status_code=403, detail="Account is deactivated")

    clear_login_failures(credentials.email)
    token = create_token(user["id"], user["email"], user["role"])
    await create_audit_log(user["id"], user["email"], "LOGIN", "user", user["id"])
    return {
        "token": token,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "role": user["role"]
        }
    }

@api_router.get("/auth/me", response_model=UserResponse)
async def get_me(user: dict = Depends(get_current_user)):
    user_doc = await fetch_one("SELECT id, email, name, role, created_at FROM users WHERE id = :id", {"id": user["user_id"]})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    user_doc["created_at"] = str(user_doc["created_at"])
    return UserResponse(**user_doc)

# ==================== USER MANAGEMENT ====================

@api_router.get("/users")
async def list_users(search: Optional[str] = None, page: int = 1, page_size: int = 50, user: dict = Depends(require_roles("SUPER_ADMIN"))):
    page, page_size = clamp_pagination(page, page_size)
    where = "FROM users WHERE 1=1"
    params = {}
    if search:
        where += " AND (name LIKE :search OR email LIKE :search)"
        params["search"] = f"%{search}%"

    users, total = await paginated(
        f"SELECT * {where}", f"SELECT COUNT(*) as total {where}", params, page, page_size, "created_at DESC"
    )

    safe = []
    for u in users:
        safe.append({
            "id": u.get("id"),
            "email": u.get("email"),
            "name": u.get("name"),
            "role": u.get("role"),
            "is_active": 0 if u.get("is_active") in (0, False) else 1,
            "created_at": str(u.get("created_at")) if u.get("created_at") else None
        })
    return {"items": safe, "total": total, "page": page, "page_size": page_size}

@api_router.put("/users/{user_id}/role")
async def update_user_role(user_id: str, role: str, user: dict = Depends(require_roles("SUPER_ADMIN"))):
    if role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail="Invalid role")
    if user_id == user["user_id"]:
        raise HTTPException(status_code=400, detail="You cannot change your own role")

    target = await fetch_one("SELECT id FROM users WHERE id = :id", {"id": user_id})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    await update_row("users", {"role": role}, "id = :user_id", {"user_id": user_id})
    await create_audit_log(user["user_id"], user["email"], "UPDATE", "user", user_id, {"role": role})
    return {"message": "Role updated successfully"}

@api_router.put("/users/{user_id}/status")
async def update_user_status(user_id: str, update: UserStatusUpdate, user: dict = Depends(require_roles("SUPER_ADMIN"))):
    if user_id == user["user_id"]:
        raise HTTPException(status_code=400, detail="You cannot deactivate your own account")

    target = await fetch_one("SELECT id FROM users WHERE id = :id", {"id": user_id})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        await update_row("users", {"is_active": 1 if update.is_active else 0}, "id = :user_id", {"user_id": user_id})
    except Exception as e:
        # Only the missing-column case gets the migration hint; anything else
        # is a real DB failure and must surface, not masquerade as schema advice.
        if "1054" in str(e) or "unknown column" in str(e).lower():
            raise HTTPException(status_code=400, detail="The users table has no is_active column. Run migration backend/migrations/001_users_is_active.sql")
        logger.exception("Failed to update user status")
        raise HTTPException(status_code=500, detail="Failed to update user status")

    await create_audit_log(user["user_id"], user["email"], "UPDATE", "user", user_id, {"is_active": update.is_active})
    return {"message": "User activated" if update.is_active else "User deactivated"}

# ==================== MERCHANT ENDPOINTS ====================

@api_router.post("/merchants")
async def create_merchant(merchant: MerchantCreate, user: dict = Depends(require_roles("SUPER_ADMIN", "OPERATIONS"))):
    merchant.business_name = merchant.business_name.strip()
    if not merchant.business_name:
        raise HTTPException(status_code=400, detail="Business name is required")

    duplicate = await fetch_one(
        "SELECT id FROM merchants WHERE LOWER(business_name) = LOWER(:name)",
        {"name": merchant.business_name}
    )
    if duplicate:
        raise HTTPException(status_code=400, detail="A merchant with this business name already exists")

    merchant_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    
    await insert_row("merchants", {
        "id": merchant_id,
        "business_name": merchant.business_name,
        "dba": merchant.dba,
        "tax_id": merchant.tax_id,
        "contact_email": merchant.contact_email,
        "contact_phone": merchant.contact_phone,
        "address": merchant.address,
        "status": merchant.status,
        "created_at": created_at,
        "created_by": user["user_id"]
    })

    await create_audit_log(user["user_id"], user["email"], "CREATE", "merchant", merchant_id, {"business_name": merchant.business_name})
    return {"id": merchant_id, **merchant.model_dump(), "created_at": created_at}

@api_router.get("/merchants")
async def list_merchants(status: Optional[str] = None, search: Optional[str] = None, page: int = 1, page_size: int = 50, user: dict = Depends(get_current_user)):
    page, page_size = clamp_pagination(page, page_size, max_page_size=500)
    where = "FROM merchants WHERE 1=1"
    params = {}

    if status:
        where += " AND status = :status"
        params["status"] = status
    if search:
        where += " AND (business_name LIKE :search OR dba LIKE :search)"
        params["search"] = f"%{search}%"

    merchants, total = await paginated(
        f"SELECT * {where}", f"SELECT COUNT(*) as total {where}", params, page, page_size, "created_at DESC"
    )

    for m in merchants:
        m["created_at"] = str(m["created_at"]) if m["created_at"] else None
        m["updated_at"] = str(m["updated_at"]) if m.get("updated_at") else None

    return {"items": merchants, "total": total, "page": page, "page_size": page_size}

@api_router.get("/merchants/{merchant_id}")
async def get_merchant(merchant_id: str, user: dict = Depends(get_current_user)):
    merchant = await fetch_one("SELECT * FROM merchants WHERE id = :id", {"id": merchant_id})
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
    merchant["created_at"] = str(merchant["created_at"])
    return merchant

@api_router.put("/merchants/{merchant_id}")
async def update_merchant(merchant_id: str, update: MerchantUpdate, user: dict = Depends(require_roles("SUPER_ADMIN", "OPERATIONS"))):
    update_data = {k: v for k, v in update.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No update data provided")
    
    update_data["updated_at"] = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    await update_row("merchants", update_data, "id = :merchant_id", {"merchant_id": merchant_id})

    await create_audit_log(user["user_id"], user["email"], "UPDATE", "merchant", merchant_id, update_data)
    return await get_merchant(merchant_id, user)

@api_router.delete("/merchants/{merchant_id}")
async def delete_merchant(merchant_id: str, user: dict = Depends(require_roles("SUPER_ADMIN"))):
    terminals = await fetch_one("SELECT COUNT(*) as count FROM terminal_profiles WHERE merchant_id = :id", {"id": merchant_id})
    transactions = await fetch_one("SELECT COUNT(*) as count FROM transactions WHERE merchant_id = :id", {"id": merchant_id})
    t_count = terminals["count"] if terminals else 0
    tx_count = transactions["count"] if transactions else 0
    if t_count or tx_count:
        raise HTTPException(
            status_code=400,
            detail=f"Merchant has {t_count} terminal(s) and {tx_count} transaction(s). Suspend the merchant instead of deleting, or remove its terminals first."
        )

    await delete_row("merchants", "id = :id", {"id": merchant_id})
    # Remove any Hub mapping too, or its unique key blocks re-linking later
    await delete_row("hub_merchant_links", "merchant_id = :id", {"id": merchant_id})
    await create_audit_log(user["user_id"], user["email"], "DELETE", "merchant", merchant_id)
    return {"message": "Merchant deleted successfully"}

# ==================== VAR SHEET ENDPOINTS ====================

@api_router.post("/admin/varsheet/upload")
async def upload_varsheet(file: UploadFile = File(...), merchant_id: str = Form(...), user: dict = Depends(require_roles("SUPER_ADMIN", "OPERATIONS"))):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    file_id = str(uuid.uuid4())
    file_path = UPLOAD_DIR / f"{file_id}.pdf"
    
    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)
    
    created_at = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    
    await insert_row("varsheet_uploads", {
        "id": file_id,
        "merchant_id": merchant_id,
        "provider": "tsys",
        "file_path": str(file_path),
        "filename": file.filename,
        "parse_status": "pending",
        "created_at": created_at,
        "created_by": user["user_id"]
    })

    await create_audit_log(user["user_id"], user["email"], "UPLOAD", "varsheet", file_id, {"filename": file.filename, "merchant_id": merchant_id})
    return {"id": file_id, "merchant_id": merchant_id, "filename": file.filename, "parse_status": "pending", "created_at": created_at}

@api_router.post("/admin/varsheet/{varsheet_id}/parse")
async def parse_varsheet(varsheet_id: str, user: dict = Depends(require_roles("SUPER_ADMIN", "OPERATIONS"))):
    varsheet = await fetch_one("SELECT * FROM varsheet_uploads WHERE id = :id", {"id": varsheet_id})
    if not varsheet:
        raise HTTPException(status_code=404, detail="VAR sheet not found")
    
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(varsheet["file_path"])
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        
        parsed_data = parse_var_sheet_text(text)
        parse_status = "success" if parsed_data.get("merchant_number") else "needs_review"
    except Exception as e:
        logger.error(f"PDF parsing error: {e}")
        parsed_data = {"error": str(e)}
        parse_status = "failed"
    
    parsed_at = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    await update_row("varsheet_uploads", {
        "parsed_json": json.dumps(parsed_data),
        "parse_status": parse_status,
        "parsed_at": parsed_at
    }, "id = :id", {"id": varsheet_id})

    await create_audit_log(user["user_id"], user["email"], "PARSE", "varsheet", varsheet_id, {"parse_status": parse_status})
    return {"id": varsheet_id, "parsed_json": parsed_data, "parse_status": parse_status}

@api_router.get("/admin/varsheet/{varsheet_id}")
async def get_varsheet(varsheet_id: str, user: dict = Depends(get_current_user)):
    varsheet = await fetch_one("SELECT * FROM varsheet_uploads WHERE id = :id", {"id": varsheet_id})
    if not varsheet:
        raise HTTPException(status_code=404, detail="VAR sheet not found")
    
    varsheet["created_at"] = str(varsheet["created_at"]) if varsheet["created_at"] else None
    if varsheet.get("parsed_json"):
        varsheet["parsed_json"] = json.loads(varsheet["parsed_json"]) if isinstance(varsheet["parsed_json"], str) else varsheet["parsed_json"]
    return varsheet

@api_router.get("/admin/varsheets")
async def list_varsheets(merchant_id: Optional[str] = None, parse_status: Optional[str] = None, user: dict = Depends(get_current_user)):
    query = "SELECT * FROM varsheet_uploads WHERE 1=1"
    params = {}
    
    if merchant_id:
        query += " AND merchant_id = :merchant_id"
        params["merchant_id"] = merchant_id
    if parse_status:
        query += " AND parse_status = :parse_status"
        params["parse_status"] = parse_status
    
    query += " ORDER BY created_at DESC"
    varsheets = await fetch_all(query, params)
    
    for v in varsheets:
        v["created_at"] = str(v["created_at"]) if v["created_at"] else None
        if v.get("parsed_json"):
            v["parsed_json"] = json.loads(v["parsed_json"]) if isinstance(v["parsed_json"], str) else v["parsed_json"]
    
    return varsheets

@api_router.put("/admin/varsheet/{varsheet_id}")
async def update_varsheet_parsed_data(varsheet_id: str, parsed_data: VarSheetParsedData, user: dict = Depends(require_roles("SUPER_ADMIN", "OPERATIONS"))):
    varsheet = await fetch_one("SELECT parsed_json FROM varsheet_uploads WHERE id = :id", {"id": varsheet_id})
    if not varsheet:
        raise HTTPException(status_code=404, detail="VAR sheet not found")
    
    existing = json.loads(varsheet["parsed_json"]) if varsheet.get("parsed_json") else {}
    update_data = {k: v for k, v in parsed_data.model_dump().items() if v is not None}
    merged = {**existing, **update_data}
    
    await update_row("varsheet_uploads", {
        "parsed_json": json.dumps(merged),
        "updated_at": datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    }, "id = :id", {"id": varsheet_id})

    await create_audit_log(user["user_id"], user["email"], "UPDATE", "varsheet", varsheet_id)
    return {"id": varsheet_id, "parsed_json": merged}

# ==================== TERMINAL ENDPOINTS ====================

@api_router.post("/admin/terminals")
async def create_terminal(terminal: TerminalProfileCreate, user: dict = Depends(require_roles("SUPER_ADMIN", "OPERATIONS"))):
    merchant = await fetch_one("SELECT id FROM merchants WHERE id = :id", {"id": terminal.merchant_id})
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
    
    terminal_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    
    data = terminal.model_dump()
    data["id"] = terminal_id
    data["created_at"] = created_at
    data["created_by"] = user["user_id"]
    data["card_types"] = json.dumps(data.get("card_types") or [])
    data["networks"] = json.dumps(data.get("networks") or [])
    
    await insert_row("terminal_profiles", data)

    await create_audit_log(user["user_id"], user["email"], "CREATE", "terminal", terminal_id, {"merchant_id": terminal.merchant_id, "terminal_number": terminal.terminal_number})
    data["card_types"] = terminal.card_types
    data["networks"] = terminal.networks
    return data

@api_router.get("/admin/terminals")
async def list_terminals(merchant_id: Optional[str] = None, provisioning_status: Optional[str] = None, search: Optional[str] = None, page: int = 1, page_size: int = 50, user: dict = Depends(get_current_user)):
    page, page_size = clamp_pagination(page, page_size)
    where = "FROM terminal_profiles WHERE 1=1"
    params = {}

    if merchant_id:
        where += " AND merchant_id = :merchant_id"
        params["merchant_id"] = merchant_id
    if provisioning_status:
        where += " AND provisioning_status = :provisioning_status"
        params["provisioning_status"] = provisioning_status
    if search:
        where += " AND (terminal_number LIKE :search OR merchant_number LIKE :search OR v_number LIKE :search)"
        params["search"] = f"%{search}%"

    terminals, total = await paginated(
        f"SELECT * {where}", f"SELECT COUNT(*) as total {where}", params, page, page_size, "created_at DESC"
    )

    for t in terminals:
        t["created_at"] = str(t["created_at"]) if t["created_at"] else None
        t["card_types"] = json.loads(t["card_types"]) if t.get("card_types") else []
        t["networks"] = json.loads(t["networks"]) if t.get("networks") else []

    return {"items": terminals, "total": total, "page": page, "page_size": page_size}

@api_router.get("/admin/terminals/{terminal_id}")
async def get_terminal(terminal_id: str, user: dict = Depends(get_current_user)):
    terminal = await fetch_one("SELECT * FROM terminal_profiles WHERE id = :id", {"id": terminal_id})
    if not terminal:
        raise HTTPException(status_code=404, detail="Terminal not found")
    terminal["created_at"] = str(terminal["created_at"])
    terminal["card_types"] = json.loads(terminal["card_types"]) if terminal.get("card_types") else []
    terminal["networks"] = json.loads(terminal["networks"]) if terminal.get("networks") else []
    return terminal

@api_router.put("/admin/terminals/{terminal_id}")
async def update_terminal(terminal_id: str, update: TerminalProfileUpdate, user: dict = Depends(require_roles("SUPER_ADMIN", "OPERATIONS"))):
    update_data = {k: v for k, v in update.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No update data provided")
    
    if "card_types" in update_data:
        update_data["card_types"] = json.dumps(update_data["card_types"])
    if "networks" in update_data:
        update_data["networks"] = json.dumps(update_data["networks"])
    
    update_data["updated_at"] = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    await update_row("terminal_profiles", update_data, "id = :terminal_id", {"terminal_id": terminal_id})

    await create_audit_log(user["user_id"], user["email"], "UPDATE", "terminal", terminal_id)
    return await get_terminal(terminal_id, user)

@api_router.post("/admin/terminals/{terminal_id}/provision")
async def provision_terminal(terminal_id: str, user: dict = Depends(require_roles("SUPER_ADMIN", "OPERATIONS"))):
    terminal = await fetch_one("SELECT provisioning_status FROM terminal_profiles WHERE id = :id", {"id": terminal_id})
    if not terminal:
        raise HTTPException(status_code=404, detail="Terminal not found")
    
    if terminal["provisioning_status"] == "live":
        raise HTTPException(status_code=400, detail="Terminal already live")
    
    await update_row("terminal_profiles", {
        "provisioning_status": "provisioned",
        "provisioned_at": datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
        "provisioned_by": user["user_id"]
    }, "id = :id", {"id": terminal_id})

    await create_audit_log(user["user_id"], user["email"], "PROVISION", "terminal", terminal_id)
    return {"message": "Terminal provisioned successfully", "status": "provisioned"}

@api_router.post("/admin/terminals/{terminal_id}/mark-live")
async def mark_terminal_live(terminal_id: str, user: dict = Depends(require_roles("SUPER_ADMIN", "OPERATIONS"))):
    terminal = await fetch_one("SELECT id FROM terminal_profiles WHERE id = :id", {"id": terminal_id})
    if not terminal:
        raise HTTPException(status_code=404, detail="Terminal not found")

    await update_row("terminal_profiles", {
        "provisioning_status": "live",
        "live_at": datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
        "live_by": user["user_id"]
    }, "id = :id", {"id": terminal_id})

    await create_audit_log(user["user_id"], user["email"], "MARK_LIVE", "terminal", terminal_id)
    return {"message": "Terminal marked as live", "status": "live"}

# ==================== TRANSACTIONS ====================

@api_router.get("/transactions")
async def list_transactions(merchant_id: Optional[str] = None, status: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None, page: int = 1, page_size: int = 50, user: dict = Depends(require_roles("SUPER_ADMIN", "OPERATIONS", "SUPPORT"))):
    page, page_size = clamp_pagination(page, page_size)
    where = "FROM transactions WHERE 1=1"
    params = {}

    if merchant_id:
        where += " AND merchant_id = :merchant_id"
        params["merchant_id"] = merchant_id
    if status:
        where += " AND status = :status"
        params["status"] = status
    if start_date:
        where += " AND created_at >= :start_date"
        params["start_date"] = start_date
    if end_date:
        where += " AND created_at <= :end_date"
        params["end_date"] = end_date

    transactions, total = await paginated(
        f"SELECT * {where}", f"SELECT COUNT(*) as total {where}", params, page, page_size, "created_at DESC"
    )

    # Summary over the FULL filtered set (not just the current page), so UI totals are accurate
    summary_row = await fetch_one(
        f"SELECT COUNT(*) as count, COALESCE(SUM(amount), 0) as volume, "
        f"SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) as approved {where}",
        params
    )

    for t in transactions:
        t["created_at"] = str(t["created_at"]) if t["created_at"] else None
        t["amount"] = float(t["amount"]) if t.get("amount") else 0

    return {
        "items": transactions,
        "total": total,
        "page": page,
        "page_size": page_size,
        "summary": {
            "count": summary_row["count"] if summary_row else 0,
            "volume": float(summary_row["volume"]) if summary_row and summary_row["volume"] else 0,
            "approved": int(summary_row["approved"]) if summary_row and summary_row["approved"] else 0
        }
    }

# ==================== REPORTS ====================

@api_router.get("/reports/transactions")
async def get_transaction_report(start_date: str, end_date: str, merchant_id: Optional[str] = None, card_type: Optional[str] = None, status: Optional[str] = None, user: dict = Depends(require_roles("SUPER_ADMIN", "OPERATIONS", "SUPPORT"))):
    query = "SELECT * FROM transactions WHERE created_at >= :start_date AND created_at <= :end_date"
    params = {"start_date": start_date, "end_date": end_date}
    
    if merchant_id:
        query += " AND merchant_id = :merchant_id"
        params["merchant_id"] = merchant_id
    if card_type:
        query += " AND card_type = :card_type"
        params["card_type"] = card_type
    if status:
        query += " AND status = :status"
        params["status"] = status
    
    query += " ORDER BY created_at DESC"
    transactions = await fetch_all(query, params)
    
    for t in transactions:
        t["created_at"] = str(t["created_at"]) if t["created_at"] else None
        t["amount"] = float(t["amount"]) if t.get("amount") else 0
    
    total_amount = sum(t["amount"] for t in transactions)
    approved_count = sum(1 for t in transactions if t.get("status") == "approved")
    declined_count = sum(1 for t in transactions if t.get("status") == "declined")
    refund_amount = sum(t["amount"] for t in transactions if t.get("transaction_type") == "refund")
    
    by_card_type = {}
    for tx in transactions:
        ct = tx.get("card_type", "Unknown") or "Unknown"
        if ct not in by_card_type:
            by_card_type[ct] = {"count": 0, "amount": 0}
        by_card_type[ct]["count"] += 1
        by_card_type[ct]["amount"] += tx["amount"]
    
    return {
        "summary": {
            "total_transactions": len(transactions),
            "total_amount": round(total_amount, 2),
            "approved_count": approved_count,
            "declined_count": declined_count,
            "refund_amount": round(refund_amount, 2),
            "approval_rate": round((approved_count / len(transactions) * 100), 2) if transactions else 0
        },
        "by_card_type": by_card_type,
        "transactions": transactions,
        "report_generated": datetime.now(timezone.utc).isoformat()
    }

@api_router.get("/reports/batches")
async def get_batch_report(start_date: str, end_date: str, merchant_id: Optional[str] = None, user: dict = Depends(require_roles("SUPER_ADMIN", "OPERATIONS", "SUPPORT"))):
    query = "SELECT * FROM transactions WHERE created_at >= :start_date AND created_at <= :end_date AND status = 'approved'"
    params = {"start_date": start_date, "end_date": end_date}
    
    if merchant_id:
        query += " AND merchant_id = :merchant_id"
        params["merchant_id"] = merchant_id
    
    query += " ORDER BY created_at"
    transactions = await fetch_all(query, params)
    
    batches = {}
    for tx in transactions:
        date_str = str(tx["created_at"])[:10] if tx["created_at"] else "unknown"
        if date_str not in batches:
            batches[date_str] = {"date": date_str, "transaction_count": 0, "sales_count": 0, "sales_amount": 0, "refund_count": 0, "refund_amount": 0, "net_amount": 0}
        
        batches[date_str]["transaction_count"] += 1
        amount = float(tx["amount"]) if tx.get("amount") else 0
        
        if tx.get("transaction_type") == "refund":
            batches[date_str]["refund_count"] += 1
            batches[date_str]["refund_amount"] += amount
        else:
            batches[date_str]["sales_count"] += 1
            batches[date_str]["sales_amount"] += amount
    
    for batch in batches.values():
        batch["net_amount"] = round(batch["sales_amount"] - batch["refund_amount"], 2)
        batch["sales_amount"] = round(batch["sales_amount"], 2)
        batch["refund_amount"] = round(batch["refund_amount"], 2)
    
    batch_list = sorted(batches.values(), key=lambda x: x["date"], reverse=True)
    
    return {
        "summary": {
            "total_batches": len(batch_list),
            "total_sales": round(sum(b["sales_amount"] for b in batch_list), 2),
            "total_refunds": round(sum(b["refund_amount"] for b in batch_list), 2),
            "net_total": round(sum(b["net_amount"] for b in batch_list), 2)
        },
        "batches": batch_list,
        "report_generated": datetime.now(timezone.utc).isoformat()
    }

@api_router.get("/reports/export")
async def export_transactions_csv(start_date: str, end_date: str, merchant_id: Optional[str] = None, status: Optional[str] = None, user: dict = Depends(require_roles("SUPER_ADMIN", "OPERATIONS", "SUPPORT"))):
    query = "SELECT * FROM transactions WHERE created_at >= :start_date AND created_at <= :end_date"
    params = {"start_date": start_date, "end_date": end_date}

    if merchant_id:
        query += " AND merchant_id = :merchant_id"
        params["merchant_id"] = merchant_id
    if status:
        query += " AND status = :status"
        params["status"] = status
    
    # Bounded export: cap at 10,000 rows to avoid unbounded memory/response size
    query += " ORDER BY created_at DESC LIMIT 10000"
    transactions = await fetch_all(query, params)

    csv_data = []
    for tx in transactions:
        csv_data.append({
            "Transaction ID": tx.get("id"),
            "Date": str(tx.get("created_at", ""))[:19],
            "Merchant ID": tx.get("merchant_id"),
            "Type": tx.get("transaction_type", "sale"),
            "Amount": float(tx.get("amount", 0)),
            "Card Type": tx.get("card_type"),
            "Card Last 4": tx.get("card_last_four", "****"),
            "Status": tx.get("status"),
            "Auth Code": tx.get("auth_code", ""),
            "Entry Mode": tx.get("entry_mode", "")
        })

    await create_audit_log(user["user_id"], user["email"], "EXPORT", "report", None, {"type": "transactions", "count": len(csv_data)})

    return {"data": csv_data, "count": len(csv_data), "truncated": len(csv_data) == 10000}

# ==================== SYSTEM LOGS ====================

@api_router.get("/logs")
async def get_system_logs(action: Optional[str] = None, resource_type: Optional[str] = None, user_id: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None, page: int = 1, page_size: int = 100, user: dict = Depends(require_roles("SUPER_ADMIN"))):
    page, page_size = clamp_pagination(page, page_size, max_page_size=500)
    where = "FROM audit_logs WHERE 1=1"
    params = {}

    if action:
        where += " AND action = :action"
        params["action"] = action
    if resource_type:
        where += " AND resource_type = :resource_type"
        params["resource_type"] = resource_type
    if user_id:
        where += " AND user_id = :filter_user_id"
        params["filter_user_id"] = user_id
    if start_date:
        where += " AND timestamp >= :start_date"
        params["start_date"] = start_date
    if end_date:
        where += " AND timestamp <= :end_date"
        params["end_date"] = end_date

    logs, total = await paginated(
        f"SELECT * {where}", f"SELECT COUNT(*) as total {where}", params, page, page_size, "timestamp DESC"
    )

    for log in logs:
        log["timestamp"] = str(log["timestamp"]) if log["timestamp"] else None
        if log.get("details"):
            log["details"] = json.loads(log["details"]) if isinstance(log["details"], str) else log["details"]

    return {"items": logs, "total": total, "page": page, "page_size": page_size}

@api_router.get("/logs/actions")
async def get_log_action_types(user: dict = Depends(require_roles("SUPER_ADMIN"))):
    actions = await fetch_all("SELECT DISTINCT action FROM audit_logs")
    resource_types = await fetch_all("SELECT DISTINCT resource_type FROM audit_logs")
    return {
        "actions": [a["action"] for a in actions] or ["CREATE", "UPDATE", "DELETE", "LOGIN", "UPLOAD", "PARSE", "PROVISION", "MARK_LIVE", "EXPORT"],
        "resource_types": [r["resource_type"] for r in resource_types] or ["merchant", "terminal", "transaction", "varsheet", "user", "report"]
    }

@api_router.get("/logs/export")
async def export_audit_logs(start_date: str, end_date: str, user: dict = Depends(require_roles("SUPER_ADMIN"))):
    logs = await fetch_all(
        "SELECT * FROM audit_logs WHERE timestamp >= :start_date AND timestamp <= :end_date ORDER BY timestamp DESC LIMIT 10000",
        {"start_date": start_date, "end_date": end_date}
    )
    await create_audit_log(user["user_id"], user["email"], "EXPORT", "report", None, {"type": "audit_logs", "count": len(logs)})

    csv_data = []
    for log in logs:
        csv_data.append({
            "Timestamp": str(log.get("timestamp")),
            "User": log.get("user_email"),
            "Action": log.get("action"),
            "Resource Type": log.get("resource_type"),
            "Resource ID": log.get("resource_id", ""),
            "IP Address": log.get("ip_address", ""),
            "Details": log.get("details", "")
        })
    
    return {"data": csv_data, "count": len(csv_data)}

# ==================== DASHBOARD ====================

@api_router.get("/dashboard/stats")
async def get_dashboard_stats(user: dict = Depends(get_current_user)):
    total_merchants = await fetch_one("SELECT COUNT(*) as count FROM merchants")
    active_merchants = await fetch_one("SELECT COUNT(*) as count FROM merchants WHERE status = 'active'")
    pending_merchants = await fetch_one("SELECT COUNT(*) as count FROM merchants WHERE status = 'pending'")
    
    total_terminals = await fetch_one("SELECT COUNT(*) as count FROM terminal_profiles")
    live_terminals = await fetch_one("SELECT COUNT(*) as count FROM terminal_profiles WHERE provisioning_status = 'live'")
    
    total_transactions = await fetch_one("SELECT COUNT(*) as count FROM transactions")

    recent_transactions = await fetch_all("SELECT * FROM transactions ORDER BY created_at DESC LIMIT 30")
    for t in recent_transactions:
        t["created_at"] = str(t["created_at"]) if t["created_at"] else None
        t["amount"] = float(t["amount"]) if t.get("amount") else 0

    # Real weekly transaction aggregates for the last 4 weeks.
    # Buckets are whole calendar days (7 per bucket, ending today) so no
    # boundary day is ever dropped from the fetched range.
    today = datetime.now(timezone.utc).date()
    cutoff_date = today - timedelta(days=27)
    daily = await fetch_all(
        "SELECT DATE(created_at) as day, COUNT(*) as count, COALESCE(SUM(amount), 0) as volume "
        "FROM transactions WHERE created_at >= :cutoff GROUP BY DATE(created_at)",
        {"cutoff": cutoff_date.strftime('%Y-%m-%d 00:00:00')}
    )
    weekly = []
    for i in range(3, -1, -1):
        week_end_date = today - timedelta(days=7 * i)
        week_start_date = week_end_date - timedelta(days=6)
        count = 0
        volume = 0.0
        for row in daily:
            day = row["day"]
            day_date = day if not hasattr(day, "date") else day.date()
            if week_start_date <= day_date <= week_end_date:
                count += row["count"]
                volume += float(row["volume"] or 0)
        weekly.append({
            "name": f"{week_start_date.strftime('%b %d')} - {week_end_date.strftime('%b %d')}",
            "transactions": count,
            "volume": round(volume, 2)
        })

    return {
        "merchants": {
            "total": total_merchants["count"] if total_merchants else 0,
            "active": active_merchants["count"] if active_merchants else 0,
            "pending": pending_merchants["count"] if pending_merchants else 0
        },
        "terminals": {
            "total": total_terminals["count"] if total_terminals else 0,
            "live": live_terminals["count"] if live_terminals else 0
        },
        "transactions": {
            "total": total_transactions["count"] if total_transactions else 0,
            "recent": recent_transactions,
            "weekly": weekly
        }
    }

# ==================== PAYMENT HUB OPERATIONS ====================
# Control-plane only: the admin calls the Payment Hub's LIVE canonical APIs
# (see hub.py header and PAYMENT_HUB_ADMIN_API_MAP.md). No Hub business logic
# is reimplemented here; no financial operations exist. Diagnostics are pinned
# to real Hub/device responses - anything unprovable reports UNKNOWN.

import hub as hub_client

# Hub identifiers travel into Hub URL paths - restrict to plain tokens so a
# crafted value cannot re-point the admin-key request at another Hub endpoint.
HUB_ID_REGEX = r"^[A-Za-z0-9_\-]{1,64}$"

class HubMerchantLink(BaseModel):
    hub_merchant_id: str = Field(min_length=1, max_length=64, pattern=HUB_ID_REGEX)

class HubTerminalLink(BaseModel):
    hub_terminal_id: str = Field(min_length=1, max_length=64, pattern=HUB_ID_REGEX)
    terminal_serial: Optional[str] = Field(default=None, max_length=64)

class BulkPingRequest(BaseModel):
    profile_ids: List[str] = Field(min_length=1, max_length=50)

def require_hub_id(value: str) -> str:
    if not hub_client.valid_hub_id(value):
        raise HTTPException(status_code=400, detail="Invalid Hub identifier")
    return value

def _overall_hub_status(checks: List[Dict[str, Any]]) -> str:
    statuses = [c["status"] for c in checks]
    if all(s == "ONLINE" for s in statuses):
        return "ONLINE"
    if all(s == "NOT_CONFIGURED" for s in statuses):
        return "NOT_CONFIGURED"
    if any(s == "OFFLINE" for s in statuses) and not any(s == "ONLINE" for s in statuses):
        return "OFFLINE"
    if any(s in ("OFFLINE", "DEGRADED", "UNKNOWN") for s in statuses) and any(s == "ONLINE" for s in statuses):
        return "DEGRADED"
    return "UNKNOWN"

@api_router.get("/hub/status")
async def hub_status(manual: bool = False, user: dict = Depends(get_current_user)):
    correlation_id = hub_client.new_correlation_id()
    # Independent checks run concurrently so a black-holed Hub costs one
    # timeout (max ~10s), not the sum of all three.
    health, ready, alerts = await asyncio.gather(
        hub_client.hub_health(correlation_id),
        hub_client.hub_ready(correlation_id),
        hub_client.hub_alerts(correlation_id),
    )

    checks = [
        {"test": "Hub API /health", **{k: health[k] for k in ("status", "latency_ms", "detail")}},
        {"test": "Hub /ready (dependencies)", **{k: ready[k] for k in ("status", "latency_ms", "detail")}},
        {"test": "Hub metrics/alerts", **{k: alerts[k] for k in ("status", "latency_ms", "detail")}},
    ]

    # Surface real triggered alerts from the Hub, if any
    triggered_alerts = None
    if alerts["status"] == "ONLINE" and isinstance(alerts.get("data"), dict):
        triggered_alerts = alerts["data"]

    if manual:
        await create_audit_log(user["user_id"], user["email"], "HUB_HEALTH_CHECK", "hub", None,
                               {"correlation_id": correlation_id, "overall": _overall_hub_status(checks)})

    return {
        "configured": hub_client.hub_configured(),
        "environment": hub_client.PAYMENT_HUB_ENV,
        "overall": _overall_hub_status(checks),
        "checks": checks,
        "dependencies": ready.get("data") if ready["status"] == "ONLINE" else None,
        "alerts": triggered_alerts,
        "correlation_id": correlation_id,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }

@api_router.get("/hub/merchants/{merchant_id}/hub-view")
async def hub_merchant_view(merchant_id: str, user: dict = Depends(get_current_user)):
    """Live Hub view of one ADMIN merchant: Hub record, processor profiles with
    cached connectivity, terminals, and routing config."""
    merchant = await fetch_one("SELECT id, business_name FROM merchants WHERE id = :id", {"id": merchant_id})
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")

    link = await fetch_one("SELECT hub_merchant_id FROM hub_merchant_links WHERE merchant_id = :id", {"id": merchant_id})
    if not link:
        return {"linked": False, "detail": "Merchant is not linked to the Payment Hub yet"}
    # Stored values predating the identifier allowlist are re-validated on use
    require_hub_id(link["hub_merchant_id"])

    lookup = await hub_client.hub_merchant_lookup(link["hub_merchant_id"])
    routing = None
    terminals = None
    if lookup["status"] == "ONLINE" and isinstance(lookup.get("data"), dict):
        hub_int_id = lookup["data"].get("id")
        if hub_int_id is not None:
            routing = await hub_client.hub_payment_path(str(hub_int_id))
            terminals = await hub_client.hub_merchant_terminals(str(hub_int_id))

    return {
        "linked": True,
        "hub_merchant_id": link["hub_merchant_id"],
        "environment": hub_client.PAYMENT_HUB_ENV,
        "lookup": lookup,
        "routing": routing,
        "terminals": terminals,
    }

@api_router.post("/hub/profiles/{profile_id}/ping")
async def hub_ping_profile(profile_id: str, user: dict = Depends(require_roles("SUPER_ADMIN", "OPERATIONS", "SUPPORT"))):
    """Real device probe via the Hub (SPIn ConnectionStatus / Valor device info)."""
    require_hub_id(profile_id)
    correlation_id = hub_client.new_correlation_id()
    result = await hub_client.hub_profile_ping(profile_id, correlation_id)
    state = hub_client.ping_state(result)
    await create_audit_log(user["user_id"], user["email"], "TERMINAL_PING", "hub_profile", profile_id,
                           {"correlation_id": correlation_id, "state": state,
                            "latency_ms": result["latency_ms"], "detail": result["detail"]})
    return {"environment": hub_client.PAYMENT_HUB_ENV, "state": state,
            "checked_at": datetime.now(timezone.utc).isoformat(), **result}

@api_router.post("/hub/profiles/bulk-ping")
async def hub_bulk_ping(request: BulkPingRequest, user: dict = Depends(require_roles("SUPER_ADMIN", "OPERATIONS"))):
    correlation_id = hub_client.new_correlation_id()
    if not hub_client.hub_configured():
        raise HTTPException(status_code=503, detail="Payment Hub is not configured")
    for pid in request.profile_ids:
        require_hub_id(pid)
    result = await hub_client.bulk_profile_ping(request.profile_ids, correlation_id)
    await create_audit_log(user["user_id"], user["email"], "TERMINAL_BULK_PING", "hub_profile", None,
                           {"correlation_id": correlation_id, "counts": result["counts"], "pinged": result["pinged"]})
    return {"environment": hub_client.PAYMENT_HUB_ENV, "correlation_id": correlation_id, **result}

@api_router.get("/hub/events")
async def hub_events_view(user: dict = Depends(require_roles("SUPER_ADMIN", "OPERATIONS", "SUPPORT"))):
    stats, undelivered = await asyncio.gather(
        hub_client.hub_events_stats(),
        hub_client.hub_events_undelivered(limit=50),
    )
    return {"environment": hub_client.PAYMENT_HUB_ENV, "stats": stats, "undelivered": undelivered}

# ---- persisted Hub mappings (references to canonical records, no duplication) ----

@api_router.get("/hub/links")
async def hub_links_list(user: dict = Depends(get_current_user)):
    merchants = await fetch_all("SELECT * FROM hub_merchant_links")
    terminals = await fetch_all("SELECT * FROM hub_terminal_links")
    for row in merchants + terminals:
        row["created_at"] = str(row["created_at"]) if row.get("created_at") else None
        row["updated_at"] = str(row["updated_at"]) if row.get("updated_at") else None
    return {"merchant_links": merchants, "terminal_links": terminals}

@api_router.put("/hub/links/merchants/{merchant_id}")
async def hub_link_merchant(merchant_id: str, link: HubMerchantLink, user: dict = Depends(require_roles("SUPER_ADMIN", "OPERATIONS"))):
    merchant = await fetch_one("SELECT id FROM merchants WHERE id = :id", {"id": merchant_id})
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")

    # Verify the identifier against the live Hub before persisting; save is
    # allowed while the Hub is unreachable, but verification state is reported.
    verification = await hub_client.hub_merchant_lookup(link.hub_merchant_id)
    if verification["status"] == "ONLINE" and verification.get("http_status") == 200:
        verified = True
    elif verification.get("http_status") == 404:
        raise HTTPException(status_code=400, detail=f"Hub has no merchant '{link.hub_merchant_id}' (checked live)")
    else:
        verified = False

    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    existing = await fetch_one("SELECT merchant_id FROM hub_merchant_links WHERE merchant_id = :id", {"id": merchant_id})
    if existing:
        await update_row("hub_merchant_links",
                         {"hub_merchant_id": link.hub_merchant_id, "environment": hub_client.PAYMENT_HUB_ENV, "updated_at": now},
                         "merchant_id = :id", {"id": merchant_id})
    else:
        await insert_row("hub_merchant_links", {
            "merchant_id": merchant_id, "hub_merchant_id": link.hub_merchant_id,
            "environment": hub_client.PAYMENT_HUB_ENV, "created_by": user["user_id"], "created_at": now})

    await create_audit_log(user["user_id"], user["email"], "MERCHANT_HUB_LINK", "merchant", merchant_id,
                           {"hub_merchant_id": link.hub_merchant_id, "environment": hub_client.PAYMENT_HUB_ENV,
                            "verified_against_hub": verified})
    return {"merchant_id": merchant_id, "hub_merchant_id": link.hub_merchant_id,
            "environment": hub_client.PAYMENT_HUB_ENV, "verified_against_hub": verified,
            "verification_detail": verification["detail"]}

@api_router.put("/hub/links/terminals/{terminal_id}")
async def hub_link_terminal(terminal_id: str, link: HubTerminalLink, user: dict = Depends(require_roles("SUPER_ADMIN", "OPERATIONS"))):
    terminal = await fetch_one("SELECT id FROM terminal_profiles WHERE id = :id", {"id": terminal_id})
    if not terminal:
        raise HTTPException(status_code=404, detail="Terminal not found")

    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    existing = await fetch_one("SELECT terminal_id FROM hub_terminal_links WHERE terminal_id = :id", {"id": terminal_id})
    if existing:
        await update_row("hub_terminal_links",
                         {"hub_terminal_id": link.hub_terminal_id, "terminal_serial": link.terminal_serial,
                          "environment": hub_client.PAYMENT_HUB_ENV, "updated_at": now},
                         "terminal_id = :id", {"id": terminal_id})
    else:
        await insert_row("hub_terminal_links", {
            "terminal_id": terminal_id, "hub_terminal_id": link.hub_terminal_id,
            "terminal_serial": link.terminal_serial, "environment": hub_client.PAYMENT_HUB_ENV,
            "created_by": user["user_id"], "created_at": now})

    await create_audit_log(user["user_id"], user["email"], "TERMINAL_HUB_LINK", "terminal", terminal_id,
                           {"hub_terminal_id": link.hub_terminal_id, "environment": hub_client.PAYMENT_HUB_ENV})
    return {"terminal_id": terminal_id, "hub_terminal_id": link.hub_terminal_id, "environment": hub_client.PAYMENT_HUB_ENV}

# ---- readiness (computed from real records + real Hub responses; UNKNOWN stays UNKNOWN) ----

def _readiness_overall(checks: List[Dict[str, str]]) -> str:
    critical = [c for c in checks if c.get("critical")]
    if any(c["status"] == "FAIL" for c in critical):
        return "NOT_READY"
    if any(c["status"] == "UNKNOWN" for c in critical):
        return "NOT_READY"  # never mark ready while critical checks are unknown
    if any(c["status"] in ("WARN", "UNKNOWN", "FAIL") for c in checks):
        return "DEGRADED"
    return "READY"

@api_router.get("/hub/merchants/{merchant_id}/readiness")
async def merchant_go_live_readiness(merchant_id: str, user: dict = Depends(require_roles("SUPER_ADMIN", "OPERATIONS", "SUPPORT"))):
    correlation_id = hub_client.new_correlation_id()
    checks: List[Dict[str, Any]] = []

    merchant = await fetch_one("SELECT * FROM merchants WHERE id = :id", {"id": merchant_id})
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
    checks.append({"check": "Merchant record", "critical": True,
                   "status": "PASS" if merchant.get("status") == "active" else "FAIL",
                   "detail": f"status={merchant.get('status')}"})

    var_ok = await fetch_one(
        "SELECT COUNT(*) as count FROM varsheet_uploads WHERE merchant_id = :id AND parse_status = 'success'",
        {"id": merchant_id})
    checks.append({"check": "VAR data", "critical": False,
                   "status": "PASS" if var_ok and var_ok["count"] else "WARN",
                   "detail": f"{var_ok['count'] if var_ok else 0} parsed VAR sheet(s)"})

    terminals = await fetch_all("SELECT id, terminal_number FROM terminal_profiles WHERE merchant_id = :id", {"id": merchant_id})
    checks.append({"check": "Terminals registered", "critical": True,
                   "status": "PASS" if terminals else "FAIL",
                   "detail": f"{len(terminals)} terminal(s) in admin registry"})

    hub_link = await fetch_one("SELECT hub_merchant_id FROM hub_merchant_links WHERE merchant_id = :id", {"id": merchant_id})
    checks.append({"check": "Hub merchant mapping", "critical": True,
                   "status": "PASS" if hub_link else "FAIL",
                   "detail": hub_link["hub_merchant_id"] if hub_link else "not linked"})

    health = await hub_client.hub_health(correlation_id)
    checks.append({"check": "Hub reachable", "critical": True,
                   "status": {"ONLINE": "PASS", "OFFLINE": "FAIL"}.get(health["status"], "UNKNOWN"),
                   "detail": health["detail"] or f"{health['latency_ms']} ms"})

    # Live Hub merchant lookup + real per-profile device pings
    profiles = []
    if hub_link and health["status"] == "ONLINE":
        lookup = await hub_client.hub_merchant_lookup(hub_link["hub_merchant_id"])
        if lookup["status"] == "ONLINE" and isinstance(lookup.get("data"), dict):
            checks.append({"check": "Hub merchant record", "critical": True, "status": "PASS",
                           "detail": f"hub id {lookup['data'].get('id')} / {lookup['data'].get('hub_mid', '')}"})
            profiles = lookup["data"].get("profiles") or []
            routing = await hub_client.hub_payment_path(str(lookup["data"].get("id")))
            checks.append({"check": "Processor route configured", "critical": True,
                           "status": "PASS" if routing["status"] == "ONLINE" and routing.get("data") else
                                     ("UNKNOWN" if routing["status"] in ("UNKNOWN", "NOT_CONFIGURED") else "FAIL"),
                           "detail": routing["detail"] or "payment path present"})
        elif lookup.get("http_status") == 404:
            checks.append({"check": "Hub merchant record", "critical": True, "status": "FAIL",
                           "detail": f"Hub has no merchant '{hub_link['hub_merchant_id']}'"})
        else:
            checks.append({"check": "Hub merchant record", "critical": True, "status": "UNKNOWN",
                           "detail": lookup["detail"]})
    else:
        checks.append({"check": "Hub merchant record", "critical": True, "status": "UNKNOWN",
                       "detail": "not linked" if not hub_link else "hub not reachable"})

    profile_ids = [p.get("id") for p in profiles if p.get("id")]
    if profile_ids:
        ping = await hub_client.bulk_profile_ping([str(p) for p in profile_ids[:10]], correlation_id)
        c = ping["counts"]
        if c["online"] == len(profile_ids[:10]):
            p_status = "PASS"
        elif c["online"]:
            p_status = "WARN"
        elif c["offline"]:
            p_status = "FAIL"
        else:
            p_status = "UNKNOWN"
        checks.append({"check": "Terminal ping (live probe)", "critical": False, "status": p_status,
                       "detail": f"online {c['online']} / offline {c['offline']} / unknown {c['unknown']}"})
    else:
        checks.append({"check": "Terminal ping (live probe)", "critical": False, "status": "UNKNOWN",
                       "detail": "no Hub processor profiles found"})

    overall = _readiness_overall(checks)
    await create_audit_log(user["user_id"], user["email"], "READINESS_CHECK", "merchant", merchant_id,
                           {"correlation_id": correlation_id, "overall": overall})
    return {"merchant_id": merchant_id, "environment": hub_client.PAYMENT_HUB_ENV,
            "overall": overall, "checks": checks, "correlation_id": correlation_id,
            "checked_at": datetime.now(timezone.utc).isoformat()}

# ==================== ROOT ====================


@api_router.get("/")
async def root():
    return {"message": "Block29 Admin API", "version": "1.1.0", "database": "MySQL"}

@api_router.get("/health")
async def health():
    try:
        await fetch_one("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except:
        return {"status": "unhealthy", "database": "disconnected"}

# Include router and middleware
app.include_router(api_router)

# Auth uses Bearer tokens (no cookies), so credentialed CORS is unnecessary.
# Set CORS_ORIGINS to the admin frontend origin(s) in production instead of '*'.
_cors_origins = [o.strip() for o in os.environ.get('CORS_ORIGINS', '*').split(',') if o.strip()]
if _cors_origins == ['*']:
    logger.warning("CORS_ORIGINS is '*' - set it to the admin frontend origin in production")
app.add_middleware(
    CORSMiddleware,
    allow_credentials=False,
    allow_origins=_cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
