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

# JWT Configuration
JWT_SECRET = os.environ.get('JWT_SECRET', 'salonbookin-admin-secret-key-2024')
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Upload directory
UPLOAD_DIR = ROOT_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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

# ==================== MODELS ====================

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
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
    business_name: str
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
    merchant_name: Optional[str] = None
    v_number: Optional[str] = None
    merchant_number: Optional[str] = None
    terminal_number: Optional[str] = None
    bin: Optional[str] = None
    chain: Optional[str] = None
    store_number: Optional[str] = None
    card_types: Optional[List[str]] = None
    networks: Optional[List[str]] = None
    amex_se: Optional[str] = None
    disc_se: Optional[str] = None
    aba: Optional[str] = None
    raw_comments: Optional[str] = None

class Block29ProvisionRequest(BaseModel):
    merchant_id: str
    processor: str
    terminal_data: Dict[str, Any]

class AgentMerchantCreate(BaseModel):
    agent_id: str
    merchant_id: str
    commission_rate: float
    level: int = 1

class TransactionCreate(BaseModel):
    merchant_id: str
    terminal_id: str
    amount: float
    card_type: str
    status: str = "pending"

class VirtualTerminalTransaction(BaseModel):
    merchant_id: str
    transaction_type: str
    amount: float
    card_number: str
    card_expiry: str
    card_cvv: str
    cardholder_name: str
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    description: Optional[str] = None

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
        "ip_address": "0.0.0.0",
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
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def require_roles(*allowed_roles):
    async def role_checker(user: dict = Depends(get_current_user)):
        if user["role"] not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return role_checker

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

app = FastAPI(title="SalonBookin Admin API", lifespan=lifespan)
api_router = APIRouter(prefix="/api")

async def create_tables():
    """Create admin-specific tables if they don't exist (most tables already exist in the database)"""
    # The database already has most tables with existing schema
    # We only need to ensure admin-specific tables exist
    
    # Check if admin user exists, if not create one
    admin = await fetch_one("SELECT id FROM users WHERE email = :email", {"email": "admin@salonbookin.com"})
    if not admin:
        await insert_row("users", {
            "id": str(uuid.uuid4()),
            "email": "admin@salonbookin.com",
            "password_hash": hash_password("admin123"),
            "business_name": "SalonBookin Admin",
            "phone_number": "",
            "role": "SUPER_ADMIN",
            "is_active": 1,
            "failed_login_attempts": 0,
            "created_at": datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        })
        logger.info("Default admin user created: admin@salonbookin.com / admin123")
    else:
        logger.info("Admin user already exists")

# ==================== AUTH ENDPOINTS ====================

@api_router.post("/auth/register", response_model=UserResponse)
async def register(user: UserCreate):
    existing = await fetch_one("SELECT id FROM users WHERE email = :email", {"email": user.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
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
    
    return UserResponse(id=user_id, email=user.email, name=user.name, role=user.role, created_at=created_at)

@api_router.post("/auth/login")
async def login(credentials: UserLogin):
    user = await fetch_one("SELECT * FROM users WHERE email = :email", {"email": credentials.email})
    if not user or not verify_password(credentials.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_token(user["id"], user["email"], user["role"])
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
async def list_users(user: dict = Depends(require_roles("SUPER_ADMIN"))):
    users = await fetch_all("SELECT id, email, name, role, created_at FROM users")
    for u in users:
        u["created_at"] = str(u["created_at"])
    return users

@api_router.put("/users/{user_id}/role")
async def update_user_role(user_id: str, role: str, user: dict = Depends(require_roles("SUPER_ADMIN"))):
    valid_roles = ["SUPER_ADMIN", "OPERATIONS", "SUPPORT", "RISK", "READ_ONLY"]
    if role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role")
    
    await update_row("users", {"role": role}, "id = :user_id", {"user_id": user_id})
    return {"message": "Role updated successfully"}

# ==================== MERCHANT ENDPOINTS ====================

@api_router.post("/merchants")
async def create_merchant(merchant: MerchantCreate, user: dict = Depends(require_roles("SUPER_ADMIN", "OPERATIONS"))):
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
    
    return {"id": merchant_id, **merchant.model_dump(), "created_at": created_at}

@api_router.get("/merchants")
async def list_merchants(status: Optional[str] = None, search: Optional[str] = None, user: dict = Depends(get_current_user)):
    query = "SELECT * FROM merchants WHERE 1=1"
    params = {}
    
    if status:
        query += " AND status = :status"
        params["status"] = status
    if search:
        query += " AND (business_name LIKE :search OR dba LIKE :search)"
        params["search"] = f"%{search}%"
    
    query += " ORDER BY created_at DESC"
    merchants = await fetch_all(query, params)
    
    for m in merchants:
        m["created_at"] = str(m["created_at"]) if m["created_at"] else None
        m["updated_at"] = str(m["updated_at"]) if m.get("updated_at") else None
    
    return merchants

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
    
    return await get_merchant(merchant_id, user)

@api_router.delete("/merchants/{merchant_id}")
async def delete_merchant(merchant_id: str, user: dict = Depends(require_roles("SUPER_ADMIN"))):
    await delete_row("merchants", "id = :id", {"id": merchant_id})
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
    
    data["card_types"] = terminal.card_types
    data["networks"] = terminal.networks
    return data

@api_router.get("/admin/terminals")
async def list_terminals(merchant_id: Optional[str] = None, provisioning_status: Optional[str] = None, user: dict = Depends(get_current_user)):
    query = "SELECT * FROM terminal_profiles WHERE 1=1"
    params = {}
    
    if merchant_id:
        query += " AND merchant_id = :merchant_id"
        params["merchant_id"] = merchant_id
    if provisioning_status:
        query += " AND provisioning_status = :provisioning_status"
        params["provisioning_status"] = provisioning_status
    
    query += " ORDER BY created_at DESC"
    terminals = await fetch_all(query, params)
    
    for t in terminals:
        t["created_at"] = str(t["created_at"]) if t["created_at"] else None
        t["card_types"] = json.loads(t["card_types"]) if t.get("card_types") else []
        t["networks"] = json.loads(t["networks"]) if t.get("networks") else []
    
    return terminals

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
    
    return {"message": "Terminal provisioned successfully", "status": "provisioned"}

@api_router.post("/admin/terminals/{terminal_id}/pair")
async def generate_pairing_token(terminal_id: str, user: dict = Depends(require_roles("SUPER_ADMIN", "OPERATIONS"))):
    terminal = await fetch_one("SELECT id FROM terminal_profiles WHERE id = :id", {"id": terminal_id})
    if not terminal:
        raise HTTPException(status_code=404, detail="Terminal not found")
    
    pairing_token = str(uuid.uuid4()).upper()[:12]
    created_at = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S')
    
    await insert_row("pos_terminal_links", {
        "id": str(uuid.uuid4()),
        "terminal_profile_id": terminal_id,
        "pairing_token": pairing_token,
        "token_status": "active",
        "created_at": created_at,
        "expires_at": expires_at
    })
    
    return {"pairing_token": pairing_token, "expires_in": "24 hours"}

@api_router.post("/admin/terminals/{terminal_id}/mark-live")
async def mark_terminal_live(terminal_id: str, user: dict = Depends(require_roles("SUPER_ADMIN", "OPERATIONS"))):
    await update_row("terminal_profiles", {
        "provisioning_status": "live",
        "live_at": datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
        "live_by": user["user_id"]
    }, "id = :id", {"id": terminal_id})
    
    return {"message": "Terminal marked as live", "status": "live"}

# ==================== BLOCK29 GATEWAY ====================

@api_router.post("/block29/provision-terminal")
async def block29_provision(request: Block29ProvisionRequest, user: dict = Depends(require_roles("SUPER_ADMIN", "OPERATIONS"))):
    valid_processors = ["clover", "dejavoo", "valor"]
    if request.processor.lower() not in valid_processors:
        raise HTTPException(status_code=400, detail=f"Invalid processor")
    
    provision_id = str(uuid.uuid4())
    await insert_row("block29_provisions", {
        "id": provision_id,
        "merchant_id": request.merchant_id,
        "processor": request.processor.lower(),
        "terminal_data": json.dumps(request.terminal_data),
        "status": "submitted",
        "created_at": datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
        "created_by": user["user_id"]
    })
    
    return {"provision_id": provision_id, "status": "submitted", "processor": request.processor}

@api_router.get("/block29/provisions")
async def list_block29_provisions(merchant_id: Optional[str] = None, processor: Optional[str] = None, user: dict = Depends(get_current_user)):
    query = "SELECT * FROM block29_provisions WHERE 1=1"
    params = {}
    
    if merchant_id:
        query += " AND merchant_id = :merchant_id"
        params["merchant_id"] = merchant_id
    if processor:
        query += " AND processor = :processor"
        params["processor"] = processor.lower()
    
    query += " ORDER BY created_at DESC"
    provisions = await fetch_all(query, params)
    
    for p in provisions:
        p["created_at"] = str(p["created_at"]) if p["created_at"] else None
        p["terminal_data"] = json.loads(p["terminal_data"]) if p.get("terminal_data") else {}
    
    return provisions

# ==================== AGENT/AFFILIATE ====================

@api_router.post("/agents/merchants")
async def assign_merchant_to_agent(assignment: AgentMerchantCreate, user: dict = Depends(require_roles("SUPER_ADMIN", "OPERATIONS"))):
    merchant = await fetch_one("SELECT id FROM merchants WHERE id = :id", {"id": assignment.merchant_id})
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
    
    assignment_id = str(uuid.uuid4())
    await insert_row("agent_merchants", {
        "id": assignment_id,
        "agent_id": assignment.agent_id,
        "merchant_id": assignment.merchant_id,
        "commission_rate": assignment.commission_rate,
        "level": assignment.level,
        "created_at": datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
        "created_by": user["user_id"]
    })
    
    return {"id": assignment_id, **assignment.model_dump()}

@api_router.get("/agents/merchants")
async def list_agent_merchant_assignments(agent_id: Optional[str] = None, user: dict = Depends(get_current_user)):
    query = "SELECT * FROM agent_merchants WHERE 1=1"
    params = {}
    
    if agent_id:
        query += " AND agent_id = :agent_id"
        params["agent_id"] = agent_id
    
    assignments = await fetch_all(query, params)
    for a in assignments:
        a["created_at"] = str(a["created_at"]) if a["created_at"] else None
        a["commission_rate"] = float(a["commission_rate"]) if a.get("commission_rate") else 0
    return assignments

@api_router.get("/agents")
async def list_agents(user: dict = Depends(get_current_user)):
    agents = await fetch_all("SELECT id, email, name, role, created_at FROM users")
    for a in agents:
        a["created_at"] = str(a["created_at"]) if a["created_at"] else None
    return agents

# ==================== TRANSACTIONS ====================

@api_router.post("/transactions")
async def create_transaction(transaction: TransactionCreate, user: dict = Depends(require_roles("SUPER_ADMIN", "OPERATIONS", "SUPPORT"))):
    tx_id = str(uuid.uuid4())
    await insert_row("transactions", {
        "id": tx_id,
        "merchant_id": transaction.merchant_id,
        "terminal_id": transaction.terminal_id,
        "amount": transaction.amount,
        "card_type": transaction.card_type,
        "status": transaction.status,
        "created_at": datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    })
    
    await create_audit_log(user["user_id"], user["email"], "CREATE", "transaction", tx_id)
    return {"id": tx_id, **transaction.model_dump()}

@api_router.get("/transactions")
async def list_transactions(merchant_id: Optional[str] = None, status: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None, user: dict = Depends(require_roles("SUPER_ADMIN", "OPERATIONS", "SUPPORT"))):
    query = "SELECT * FROM transactions WHERE 1=1"
    params = {}
    
    if merchant_id:
        query += " AND merchant_id = :merchant_id"
        params["merchant_id"] = merchant_id
    if status:
        query += " AND status = :status"
        params["status"] = status
    if start_date:
        query += " AND created_at >= :start_date"
        params["start_date"] = start_date
    if end_date:
        query += " AND created_at <= :end_date"
        params["end_date"] = end_date
    
    query += " ORDER BY created_at DESC LIMIT 1000"
    transactions = await fetch_all(query, params)
    
    for t in transactions:
        t["created_at"] = str(t["created_at"]) if t["created_at"] else None
        t["amount"] = float(t["amount"]) if t.get("amount") else 0
    
    return transactions

# ==================== VIRTUAL TERMINAL ====================

@api_router.post("/virtual-terminal/process")
async def process_virtual_terminal(transaction: VirtualTerminalTransaction, user: dict = Depends(require_roles("SUPER_ADMIN", "OPERATIONS"))):
    merchant = await fetch_one("SELECT id FROM merchants WHERE id = :id", {"id": transaction.merchant_id})
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
    
    card_last_four = transaction.card_number[-4:] if len(transaction.card_number) >= 4 else "****"
    card_number = transaction.card_number.replace(" ", "").replace("-", "")
    
    if card_number.startswith("4"):
        card_brand = "VISA"
    elif card_number[:2] in ["51", "52", "53", "54", "55"]:
        card_brand = "MasterCard"
    elif card_number[:2] in ["34", "37"]:
        card_brand = "AMEX"
    elif card_number.startswith("6011"):
        card_brand = "Discover"
    else:
        card_brand = "Unknown"
    
    import random
    is_approved = random.random() > 0.1
    auth_code = str(uuid.uuid4())[:8].upper() if is_approved else None
    
    tx_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    
    await insert_row("transactions", {
        "id": tx_id,
        "merchant_id": transaction.merchant_id,
        "terminal_id": "VIRTUAL",
        "transaction_type": transaction.transaction_type,
        "amount": transaction.amount,
        "card_type": card_brand,
        "card_last_four": card_last_four,
        "card_expiry": transaction.card_expiry,
        "cardholder_name": transaction.cardholder_name,
        "customer_email": transaction.customer_email,
        "customer_phone": transaction.customer_phone,
        "description": transaction.description,
        "status": "approved" if is_approved else "declined",
        "auth_code": auth_code,
        "response_code": "00" if is_approved else "05",
        "response_message": "APPROVED" if is_approved else "DECLINED - Do Not Honor",
        "entry_mode": "KEYED",
        "processed_by": user["user_id"],
        "created_at": created_at
    })
    
    await create_audit_log(user["user_id"], user["email"], "VIRTUAL_TERMINAL", "transaction", tx_id, {"amount": transaction.amount, "status": "approved" if is_approved else "declined"})
    
    return {
        "id": tx_id,
        "status": "approved" if is_approved else "declined",
        "amount": transaction.amount,
        "card_type": card_brand,
        "card_last_four": card_last_four,
        "auth_code": auth_code,
        "response_code": "00" if is_approved else "05",
        "response_message": "APPROVED" if is_approved else "DECLINED - Do Not Honor",
        "created_at": created_at
    }

@api_router.post("/virtual-terminal/refund/{transaction_id}")
async def process_refund(transaction_id: str, amount: Optional[float] = None, user: dict = Depends(require_roles("SUPER_ADMIN", "OPERATIONS"))):
    original_tx = await fetch_one("SELECT * FROM transactions WHERE id = :id", {"id": transaction_id})
    if not original_tx:
        raise HTTPException(status_code=404, detail="Original transaction not found")
    
    if original_tx["status"] != "approved":
        raise HTTPException(status_code=400, detail="Can only refund approved transactions")
    
    refund_amount = amount if amount else float(original_tx["amount"])
    if refund_amount > float(original_tx["amount"]):
        raise HTTPException(status_code=400, detail="Refund amount cannot exceed original amount")
    
    refund_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    
    await insert_row("transactions", {
        "id": refund_id,
        "merchant_id": original_tx["merchant_id"],
        "terminal_id": "VIRTUAL",
        "transaction_type": "refund",
        "amount": refund_amount,
        "card_type": original_tx.get("card_type"),
        "card_last_four": original_tx.get("card_last_four"),
        "original_transaction_id": transaction_id,
        "status": "approved",
        "auth_code": str(uuid.uuid4())[:8].upper(),
        "response_code": "00",
        "response_message": "REFUND APPROVED",
        "entry_mode": "KEYED",
        "processed_by": user["user_id"],
        "created_at": created_at
    })
    
    await create_audit_log(user["user_id"], user["email"], "REFUND", "transaction", refund_id, {"original_tx": transaction_id, "amount": refund_amount})
    
    return {"id": refund_id, "status": "approved", "amount": refund_amount, "response_message": "REFUND APPROVED"}

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
            "net_settlement": round(sum(b["net_amount"] for b in batch_list), 2)
        },
        "batches": batch_list,
        "report_generated": datetime.now(timezone.utc).isoformat()
    }

@api_router.get("/reports/settlement")
async def get_settlement_report(start_date: str, end_date: str, user: dict = Depends(require_roles("SUPER_ADMIN", "OPERATIONS"))):
    transactions = await fetch_all(
        "SELECT * FROM transactions WHERE created_at >= :start_date AND created_at <= :end_date AND status = 'approved'",
        {"start_date": start_date, "end_date": end_date}
    )
    merchants = await fetch_all("SELECT * FROM merchants")
    merchant_map = {m["id"]: m for m in merchants}
    
    settlements = {}
    for tx in transactions:
        mid = tx.get("merchant_id")
        if mid not in settlements:
            merchant = merchant_map.get(mid, {})
            settlements[mid] = {"merchant_id": mid, "merchant_name": merchant.get("business_name", "Unknown"), "transaction_count": 0, "gross_amount": 0, "refund_amount": 0, "net_amount": 0, "fee_amount": 0}
        
        amount = float(tx["amount"]) if tx.get("amount") else 0
        if tx.get("transaction_type") == "refund":
            settlements[mid]["refund_amount"] += amount
        else:
            settlements[mid]["gross_amount"] += amount
        settlements[mid]["transaction_count"] += 1
    
    for s in settlements.values():
        s["net_amount"] = round(s["gross_amount"] - s["refund_amount"], 2)
        s["fee_amount"] = round(s["gross_amount"] * 0.029 + (s["transaction_count"] * 0.30), 2)
        s["payout_amount"] = round(s["net_amount"] - s["fee_amount"], 2)
        s["gross_amount"] = round(s["gross_amount"], 2)
        s["refund_amount"] = round(s["refund_amount"], 2)
    
    settlement_list = sorted(settlements.values(), key=lambda x: x["net_amount"], reverse=True)
    
    return {
        "summary": {
            "total_merchants": len(settlement_list),
            "total_gross": round(sum(s["gross_amount"] for s in settlement_list), 2),
            "total_fees": round(sum(s["fee_amount"] for s in settlement_list), 2),
            "total_payout": round(sum(s["payout_amount"] for s in settlement_list), 2)
        },
        "settlements": settlement_list,
        "report_generated": datetime.now(timezone.utc).isoformat()
    }

@api_router.get("/reports/export")
async def export_transactions_csv(start_date: str, end_date: str, merchant_id: Optional[str] = None, user: dict = Depends(require_roles("SUPER_ADMIN", "OPERATIONS", "SUPPORT"))):
    query = "SELECT * FROM transactions WHERE created_at >= :start_date AND created_at <= :end_date"
    params = {"start_date": start_date, "end_date": end_date}
    
    if merchant_id:
        query += " AND merchant_id = :merchant_id"
        params["merchant_id"] = merchant_id
    
    query += " ORDER BY created_at DESC"
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
            "Entry Mode": tx.get("entry_mode", ""),
            "Cardholder": tx.get("cardholder_name", "")
        })
    
    await create_audit_log(user["user_id"], user["email"], "EXPORT", "report", None, {"type": "transactions", "count": len(csv_data)})
    
    return {"data": csv_data, "count": len(csv_data)}

# ==================== SYSTEM LOGS ====================

@api_router.get("/logs")
async def get_system_logs(limit: int = 100, action: Optional[str] = None, resource_type: Optional[str] = None, user_id: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None, user: dict = Depends(require_roles("SUPER_ADMIN"))):
    query = "SELECT * FROM audit_logs WHERE 1=1"
    params = {}
    
    if action:
        query += " AND action = :action"
        params["action"] = action
    if resource_type:
        query += " AND resource_type = :resource_type"
        params["resource_type"] = resource_type
    if user_id:
        query += " AND user_id = :filter_user_id"
        params["filter_user_id"] = user_id
    if start_date:
        query += " AND timestamp >= :start_date"
        params["start_date"] = start_date
    if end_date:
        query += " AND timestamp <= :end_date"
        params["end_date"] = end_date
    
    query += f" ORDER BY timestamp DESC LIMIT {limit}"
    logs = await fetch_all(query, params)
    
    for log in logs:
        log["timestamp"] = str(log["timestamp"]) if log["timestamp"] else None
        if log.get("details"):
            log["details"] = json.loads(log["details"]) if isinstance(log["details"], str) else log["details"]
    
    return logs

@api_router.get("/logs/actions")
async def get_log_action_types(user: dict = Depends(require_roles("SUPER_ADMIN"))):
    actions = await fetch_all("SELECT DISTINCT action FROM audit_logs")
    resource_types = await fetch_all("SELECT DISTINCT resource_type FROM audit_logs")
    return {
        "actions": [a["action"] for a in actions] or ["CREATE", "UPDATE", "DELETE", "VIRTUAL_TERMINAL", "REFUND", "EXPORT"],
        "resource_types": [r["resource_type"] for r in resource_types] or ["merchant", "terminal", "transaction", "varsheet", "user", "report"]
    }

@api_router.get("/logs/export")
async def export_audit_logs(start_date: str, end_date: str, user: dict = Depends(require_roles("SUPER_ADMIN"))):
    logs = await fetch_all(
        "SELECT * FROM audit_logs WHERE timestamp >= :start_date AND timestamp <= :end_date ORDER BY timestamp DESC",
        {"start_date": start_date, "end_date": end_date}
    )
    
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
            "recent": recent_transactions
        }
    }

# ==================== ROOT ====================

@api_router.get("/")
async def root():
    return {"message": "SalonBookin Admin API", "version": "1.0.0", "database": "MySQL"}

@api_router.get("/health")
async def health():
    try:
        await fetch_one("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except:
        return {"status": "unhealthy", "database": "disconnected"}

# Include router and middleware
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)
