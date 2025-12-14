from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Form, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
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

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Configuration
JWT_SECRET = os.environ.get('JWT_SECRET', 'salonbookin-admin-secret-key-2024')
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Upload directory
UPLOAD_DIR = ROOT_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

app = FastAPI(title="SalonBookin Admin API")
api_router = APIRouter(prefix="/api")
security = HTTPBearer()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==================== MODELS ====================

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str = "READ_ONLY"  # SUPER_ADMIN, OPERATIONS, SUPPORT, RISK, READ_ONLY

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
    status: str = "pending"  # pending, active, suspended

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
    provider: str = "luqra"
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
    provisioning_status: str = "draft"  # draft, ready, provisioned, live

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
    processor: str  # clover, dejavoo, valor
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
    status: str = "pending"  # pending, approved, declined

class VirtualTerminalTransaction(BaseModel):
    merchant_id: str
    transaction_type: str  # sale, authorization, refund
    amount: float
    card_number: str  # masked, only last 4 stored
    card_expiry: str
    card_cvv: str  # not stored
    cardholder_name: str
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    description: Optional[str] = None

class AuditLogCreate(BaseModel):
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

class BatchReport(BaseModel):
    merchant_id: Optional[str] = None
    start_date: str
    end_date: str

# ==================== AUDIT LOG HELPER ====================

async def create_audit_log(user_id: str, user_email: str, action: str, resource_type: str, resource_id: str = None, details: dict = None):
    """Create an audit log entry for tracking all admin actions"""
    log_entry = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "user_email": user_email,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "details": details or {},
        "ip_address": "0.0.0.0",  # Would be captured from request in production
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    await db.audit_logs.insert_one(log_entry)
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

# ==================== VAR PARSER ====================

def parse_var_sheet_text(text: str) -> Dict[str, Any]:
    """Parse VAR sheet text and extract key fields using regex patterns"""
    parsed = {
        "merchant_name": None,
        "v_number": None,
        "merchant_number": None,
        "terminal_number": None,
        "bin": None,
        "chain": None,
        "store_number": None,
        "card_types": [],
        "networks": [],
        "amex_se": None,
        "disc_se": None,
        "aba": None,
        "raw_comments": None,
        "confidence_flags": {}
    }
    
    # Pattern matching for common VAR sheet fields
    patterns = {
        "v_number": r"V[\s-]?Number[:\s]+([A-Z0-9]+)",
        "merchant_number": r"Merchant[\s-]?(?:Number|#|ID)[:\s]+([A-Z0-9]+)",
        "terminal_number": r"Terminal[\s-]?(?:Number|#|ID)[:\s]+([A-Z0-9]+)",
        "bin": r"BIN[:\s]+([0-9]+)",
        "chain": r"Chain[:\s]+([A-Z0-9]+)",
        "store_number": r"Store[\s-]?(?:Number|#)[:\s]+([A-Z0-9]+)",
        "amex_se": r"AMEX[\s-]?SE[:\s]+([A-Z0-9]+)",
        "disc_se": r"DISC(?:OVER)?[\s-]?SE[:\s]+([A-Z0-9]+)",
        "aba": r"ABA[:\s]+([0-9]+)",
        "merchant_name": r"(?:Merchant|Business)[\s-]?Name[:\s]+([A-Za-z0-9\s&.,'-]+)"
    }
    
    for field, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            parsed[field] = match.group(1).strip()
            parsed["confidence_flags"][field] = "high"
        else:
            parsed["confidence_flags"][field] = "not_found"
    
    # Card types detection
    card_types = []
    if re.search(r"\bVISA\b", text, re.IGNORECASE):
        card_types.append("VISA")
    if re.search(r"\bMasterCard|MC\b", text, re.IGNORECASE):
        card_types.append("MasterCard")
    if re.search(r"\bAMEX|American Express\b", text, re.IGNORECASE):
        card_types.append("AMEX")
    if re.search(r"\bDiscover\b", text, re.IGNORECASE):
        card_types.append("Discover")
    parsed["card_types"] = card_types
    
    # Networks detection
    networks = []
    if re.search(r"\bSTAR\b", text):
        networks.append("STAR")
    if re.search(r"\bPLUS\b", text):
        networks.append("PLUS")
    if re.search(r"\bNYCE\b", text):
        networks.append("NYCE")
    if re.search(r"\bPulse\b", text, re.IGNORECASE):
        networks.append("Pulse")
    parsed["networks"] = networks
    
    return parsed

# ==================== AUTH ENDPOINTS ====================

@api_router.post("/auth/register", response_model=UserResponse)
async def register(user: UserCreate):
    # Check if user exists
    existing = await db.users.find_one({"email": user.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_doc = {
        "id": str(uuid.uuid4()),
        "email": user.email,
        "password": hash_password(user.password),
        "name": user.name,
        "role": user.role,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.users.insert_one(user_doc)
    return UserResponse(
        id=user_doc["id"],
        email=user_doc["email"],
        name=user_doc["name"],
        role=user_doc["role"],
        created_at=user_doc["created_at"]
    )

@api_router.post("/auth/login")
async def login(credentials: UserLogin):
    user = await db.users.find_one({"email": credentials.email})
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
    user_doc = await db.users.find_one({"id": user["user_id"]}, {"_id": 0, "password": 0})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(**user_doc)

# ==================== USER MANAGEMENT ====================

@api_router.get("/users")
async def list_users(user: dict = Depends(require_roles("SUPER_ADMIN"))):
    users = await db.users.find({}, {"_id": 0, "password": 0}).to_list(1000)
    return users

@api_router.put("/users/{user_id}/role")
async def update_user_role(user_id: str, role: str, user: dict = Depends(require_roles("SUPER_ADMIN"))):
    valid_roles = ["SUPER_ADMIN", "OPERATIONS", "SUPPORT", "RISK", "READ_ONLY"]
    if role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {valid_roles}")
    
    result = await db.users.update_one({"id": user_id}, {"$set": {"role": role}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "Role updated successfully"}

# ==================== MERCHANT ENDPOINTS ====================

@api_router.post("/merchants")
async def create_merchant(merchant: MerchantCreate, user: dict = Depends(require_roles("SUPER_ADMIN", "OPERATIONS"))):
    merchant_doc = {
        "id": str(uuid.uuid4()),
        **merchant.model_dump(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": user["user_id"]
    }
    await db.merchants.insert_one(merchant_doc)
    merchant_doc.pop("_id", None)
    return merchant_doc

@api_router.get("/merchants")
async def list_merchants(
    status: Optional[str] = None,
    search: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    query = {}
    if status:
        query["status"] = status
    if search:
        query["$or"] = [
            {"business_name": {"$regex": search, "$options": "i"}},
            {"dba": {"$regex": search, "$options": "i"}}
        ]
    
    merchants = await db.merchants.find(query, {"_id": 0}).to_list(1000)
    return merchants

@api_router.get("/merchants/{merchant_id}")
async def get_merchant(merchant_id: str, user: dict = Depends(get_current_user)):
    merchant = await db.merchants.find_one({"id": merchant_id}, {"_id": 0})
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
    return merchant

@api_router.put("/merchants/{merchant_id}")
async def update_merchant(merchant_id: str, update: MerchantUpdate, user: dict = Depends(require_roles("SUPER_ADMIN", "OPERATIONS"))):
    update_data = {k: v for k, v in update.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No update data provided")
    
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = await db.merchants.update_one({"id": merchant_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Merchant not found")
    
    return await db.merchants.find_one({"id": merchant_id}, {"_id": 0})

@api_router.delete("/merchants/{merchant_id}")
async def delete_merchant(merchant_id: str, user: dict = Depends(require_roles("SUPER_ADMIN"))):
    result = await db.merchants.delete_one({"id": merchant_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Merchant not found")
    return {"message": "Merchant deleted successfully"}

# ==================== VAR SHEET ENDPOINTS ====================

@api_router.post("/admin/varsheet/upload")
async def upload_varsheet(
    file: UploadFile = File(...),
    merchant_id: str = Form(...),
    user: dict = Depends(require_roles("SUPER_ADMIN", "OPERATIONS"))
):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Save file
    file_id = str(uuid.uuid4())
    file_path = UPLOAD_DIR / f"{file_id}.pdf"
    
    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)
    
    # Create varsheet record
    varsheet_doc = {
        "id": file_id,
        "merchant_id": merchant_id,
        "provider": "luqra",
        "file_path": str(file_path),
        "filename": file.filename,
        "parsed_json": None,
        "parse_status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": user["user_id"]
    }
    await db.varsheet_uploads.insert_one(varsheet_doc)
    varsheet_doc.pop("_id", None)
    
    return varsheet_doc

@api_router.post("/admin/varsheet/{varsheet_id}/parse")
async def parse_varsheet(varsheet_id: str, user: dict = Depends(require_roles("SUPER_ADMIN", "OPERATIONS"))):
    varsheet = await db.varsheet_uploads.find_one({"id": varsheet_id})
    if not varsheet:
        raise HTTPException(status_code=404, detail="VAR sheet not found")
    
    # Try to parse PDF
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
        parsed_data = {"error": str(e), "confidence_flags": {}}
        parse_status = "failed"
    
    # Update record
    await db.varsheet_uploads.update_one(
        {"id": varsheet_id},
        {"$set": {
            "parsed_json": parsed_data,
            "parse_status": parse_status,
            "parsed_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {
        "id": varsheet_id,
        "parsed_json": parsed_data,
        "parse_status": parse_status
    }

@api_router.get("/admin/varsheet/{varsheet_id}")
async def get_varsheet(varsheet_id: str, user: dict = Depends(get_current_user)):
    varsheet = await db.varsheet_uploads.find_one({"id": varsheet_id}, {"_id": 0})
    if not varsheet:
        raise HTTPException(status_code=404, detail="VAR sheet not found")
    return varsheet

@api_router.get("/admin/varsheets")
async def list_varsheets(
    merchant_id: Optional[str] = None,
    parse_status: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    query = {}
    if merchant_id:
        query["merchant_id"] = merchant_id
    if parse_status:
        query["parse_status"] = parse_status
    
    varsheets = await db.varsheet_uploads.find(query, {"_id": 0}).to_list(1000)
    return varsheets

@api_router.put("/admin/varsheet/{varsheet_id}")
async def update_varsheet_parsed_data(
    varsheet_id: str,
    parsed_data: VarSheetParsedData,
    user: dict = Depends(require_roles("SUPER_ADMIN", "OPERATIONS"))
):
    varsheet = await db.varsheet_uploads.find_one({"id": varsheet_id})
    if not varsheet:
        raise HTTPException(status_code=404, detail="VAR sheet not found")
    
    # Merge with existing parsed data
    existing = varsheet.get("parsed_json", {}) or {}
    update_data = {k: v for k, v in parsed_data.model_dump().items() if v is not None}
    merged = {**existing, **update_data}
    
    await db.varsheet_uploads.update_one(
        {"id": varsheet_id},
        {"$set": {
            "parsed_json": merged,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"id": varsheet_id, "parsed_json": merged}

# ==================== TERMINAL ENDPOINTS ====================

@api_router.post("/admin/terminals")
async def create_terminal(terminal: TerminalProfileCreate, user: dict = Depends(require_roles("SUPER_ADMIN", "OPERATIONS"))):
    # Verify merchant exists
    merchant = await db.merchants.find_one({"id": terminal.merchant_id})
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
    
    terminal_doc = {
        "id": str(uuid.uuid4()),
        **terminal.model_dump(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": user["user_id"]
    }
    await db.terminal_profiles.insert_one(terminal_doc)
    terminal_doc.pop("_id", None)
    return terminal_doc

@api_router.get("/admin/terminals")
async def list_terminals(
    merchant_id: Optional[str] = None,
    provisioning_status: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    query = {}
    if merchant_id:
        query["merchant_id"] = merchant_id
    if provisioning_status:
        query["provisioning_status"] = provisioning_status
    
    terminals = await db.terminal_profiles.find(query, {"_id": 0}).to_list(1000)
    return terminals

@api_router.get("/admin/terminals/{terminal_id}")
async def get_terminal(terminal_id: str, user: dict = Depends(get_current_user)):
    terminal = await db.terminal_profiles.find_one({"id": terminal_id}, {"_id": 0})
    if not terminal:
        raise HTTPException(status_code=404, detail="Terminal not found")
    return terminal

@api_router.put("/admin/terminals/{terminal_id}")
async def update_terminal(terminal_id: str, update: TerminalProfileUpdate, user: dict = Depends(require_roles("SUPER_ADMIN", "OPERATIONS"))):
    update_data = {k: v for k, v in update.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No update data provided")
    
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = await db.terminal_profiles.update_one({"id": terminal_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Terminal not found")
    
    return await db.terminal_profiles.find_one({"id": terminal_id}, {"_id": 0})

@api_router.post("/admin/terminals/{terminal_id}/provision")
async def provision_terminal(terminal_id: str, user: dict = Depends(require_roles("SUPER_ADMIN", "OPERATIONS"))):
    terminal = await db.terminal_profiles.find_one({"id": terminal_id})
    if not terminal:
        raise HTTPException(status_code=404, detail="Terminal not found")
    
    if terminal["provisioning_status"] == "live":
        raise HTTPException(status_code=400, detail="Terminal already live")
    
    # Simulate provisioning
    await db.terminal_profiles.update_one(
        {"id": terminal_id},
        {"$set": {
            "provisioning_status": "provisioned",
            "provisioned_at": datetime.now(timezone.utc).isoformat(),
            "provisioned_by": user["user_id"]
        }}
    )
    
    return {"message": "Terminal provisioned successfully", "status": "provisioned"}

@api_router.post("/admin/terminals/{terminal_id}/pair")
async def generate_pairing_token(terminal_id: str, user: dict = Depends(require_roles("SUPER_ADMIN", "OPERATIONS"))):
    terminal = await db.terminal_profiles.find_one({"id": terminal_id})
    if not terminal:
        raise HTTPException(status_code=404, detail="Terminal not found")
    
    # Generate pairing token
    pairing_token = str(uuid.uuid4()).upper()[:12]
    
    link_doc = {
        "id": str(uuid.uuid4()),
        "terminal_profile_id": terminal_id,
        "pairing_token": pairing_token,
        "token_status": "active",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
    }
    await db.pos_terminal_links.insert_one(link_doc)
    
    return {"pairing_token": pairing_token, "expires_in": "24 hours"}

@api_router.post("/admin/terminals/{terminal_id}/mark-live")
async def mark_terminal_live(terminal_id: str, user: dict = Depends(require_roles("SUPER_ADMIN", "OPERATIONS"))):
    terminal = await db.terminal_profiles.find_one({"id": terminal_id})
    if not terminal:
        raise HTTPException(status_code=404, detail="Terminal not found")
    
    await db.terminal_profiles.update_one(
        {"id": terminal_id},
        {"$set": {
            "provisioning_status": "live",
            "live_at": datetime.now(timezone.utc).isoformat(),
            "live_by": user["user_id"]
        }}
    )
    
    return {"message": "Terminal marked as live", "status": "live"}

# ==================== BLOCK29 GATEWAY ENDPOINTS ====================

@api_router.post("/block29/provision-terminal")
async def block29_provision(request: Block29ProvisionRequest, user: dict = Depends(require_roles("SUPER_ADMIN", "OPERATIONS"))):
    # Validate processor
    valid_processors = ["clover", "dejavoo", "valor"]
    if request.processor.lower() not in valid_processors:
        raise HTTPException(status_code=400, detail=f"Invalid processor. Must be one of: {valid_processors}")
    
    # Log Block29 provisioning request
    provision_log = {
        "id": str(uuid.uuid4()),
        "merchant_id": request.merchant_id,
        "processor": request.processor,
        "terminal_data": request.terminal_data,
        "status": "submitted",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": user["user_id"]
    }
    await db.block29_provisions.insert_one(provision_log)
    
    # Simulate routing response
    return {
        "provision_id": provision_log["id"],
        "status": "submitted",
        "processor": request.processor,
        "message": f"Terminal provisioning submitted to {request.processor.title()} routing engine"
    }

@api_router.get("/block29/provisions")
async def list_block29_provisions(
    merchant_id: Optional[str] = None,
    processor: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    query = {}
    if merchant_id:
        query["merchant_id"] = merchant_id
    if processor:
        query["processor"] = processor.lower()
    
    provisions = await db.block29_provisions.find(query, {"_id": 0}).to_list(1000)
    return provisions

# ==================== AGENT/AFFILIATE ENDPOINTS ====================

@api_router.post("/agents/merchants")
async def assign_merchant_to_agent(assignment: AgentMerchantCreate, user: dict = Depends(require_roles("SUPER_ADMIN", "OPERATIONS"))):
    # Check if merchant exists
    merchant = await db.merchants.find_one({"id": assignment.merchant_id})
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
    
    assignment_doc = {
        "id": str(uuid.uuid4()),
        **assignment.model_dump(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": user["user_id"]
    }
    await db.agent_merchants.insert_one(assignment_doc)
    assignment_doc.pop("_id", None)
    return assignment_doc

@api_router.get("/agents/merchants")
async def list_agent_merchant_assignments(
    agent_id: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    query = {}
    if agent_id:
        query["agent_id"] = agent_id
    
    assignments = await db.agent_merchants.find(query, {"_id": 0}).to_list(1000)
    return assignments

@api_router.get("/agents")
async def list_agents(user: dict = Depends(get_current_user)):
    # Return users with agent-related roles or all for simplicity
    agents = await db.users.find({}, {"_id": 0, "password": 0}).to_list(1000)
    return agents

# ==================== TRANSACTION ENDPOINTS ====================

@api_router.post("/transactions")
async def create_transaction(transaction: TransactionCreate, user: dict = Depends(require_roles("SUPER_ADMIN", "OPERATIONS", "SUPPORT"))):
    transaction_doc = {
        "id": str(uuid.uuid4()),
        **transaction.model_dump(),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.transactions.insert_one(transaction_doc)
    transaction_doc.pop("_id", None)
    
    # Audit log
    await create_audit_log(user["user_id"], user["email"], "CREATE", "transaction", transaction_doc["id"])
    
    return transaction_doc

@api_router.get("/transactions")
async def list_transactions(
    merchant_id: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    card_type: Optional[str] = None,
    transaction_type: Optional[str] = None,
    user: dict = Depends(require_roles("SUPER_ADMIN", "OPERATIONS", "SUPPORT"))
):
    query = {}
    if merchant_id:
        query["merchant_id"] = merchant_id
    if status:
        query["status"] = status
    if card_type:
        query["card_type"] = card_type
    if transaction_type:
        query["transaction_type"] = transaction_type
    if start_date:
        query["created_at"] = {"$gte": start_date}
    if end_date:
        if "created_at" in query:
            query["created_at"]["$lte"] = end_date
        else:
            query["created_at"] = {"$lte": end_date}
    
    transactions = await db.transactions.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return transactions

# ==================== VIRTUAL TERMINAL ====================

@api_router.post("/virtual-terminal/process")
async def process_virtual_terminal(
    transaction: VirtualTerminalTransaction,
    user: dict = Depends(require_roles("SUPER_ADMIN", "OPERATIONS"))
):
    """Process a card-not-present transaction through the virtual terminal"""
    # Verify merchant exists
    merchant = await db.merchants.find_one({"id": transaction.merchant_id})
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
    
    # Mask card number (only store last 4)
    card_last_four = transaction.card_number[-4:] if len(transaction.card_number) >= 4 else "****"
    
    # Determine card type from card number
    card_number = transaction.card_number.replace(" ", "").replace("-", "")
    if card_number.startswith("4"):
        card_brand = "VISA"
    elif card_number.startswith(("51", "52", "53", "54", "55")):
        card_brand = "MasterCard"
    elif card_number.startswith(("34", "37")):
        card_brand = "AMEX"
    elif card_number.startswith("6011"):
        card_brand = "Discover"
    else:
        card_brand = "Unknown"
    
    # Simulate transaction processing (in production, this would call actual processor)
    import random
    is_approved = random.random() > 0.1  # 90% approval rate simulation
    
    auth_code = str(uuid.uuid4())[:8].upper() if is_approved else None
    
    transaction_doc = {
        "id": str(uuid.uuid4()),
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
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.transactions.insert_one(transaction_doc)
    transaction_doc.pop("_id", None)
    
    # Audit log
    await create_audit_log(
        user["user_id"], 
        user["email"], 
        "VIRTUAL_TERMINAL", 
        "transaction", 
        transaction_doc["id"],
        {"amount": transaction.amount, "status": transaction_doc["status"], "card_brand": card_brand}
    )
    
    return transaction_doc

@api_router.post("/virtual-terminal/refund/{transaction_id}")
async def process_refund(
    transaction_id: str,
    amount: Optional[float] = None,
    user: dict = Depends(require_roles("SUPER_ADMIN", "OPERATIONS"))
):
    """Process a refund for an existing transaction"""
    original_tx = await db.transactions.find_one({"id": transaction_id})
    if not original_tx:
        raise HTTPException(status_code=404, detail="Original transaction not found")
    
    if original_tx["status"] != "approved":
        raise HTTPException(status_code=400, detail="Can only refund approved transactions")
    
    refund_amount = amount if amount else original_tx["amount"]
    if refund_amount > original_tx["amount"]:
        raise HTTPException(status_code=400, detail="Refund amount cannot exceed original amount")
    
    refund_doc = {
        "id": str(uuid.uuid4()),
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
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.transactions.insert_one(refund_doc)
    refund_doc.pop("_id", None)
    
    # Audit log
    await create_audit_log(
        user["user_id"], 
        user["email"], 
        "REFUND", 
        "transaction", 
        refund_doc["id"],
        {"original_tx": transaction_id, "amount": refund_amount}
    )
    
    return refund_doc

# ==================== REPORTS ====================

@api_router.get("/reports/transactions")
async def get_transaction_report(
    start_date: str,
    end_date: str,
    merchant_id: Optional[str] = None,
    card_type: Optional[str] = None,
    status: Optional[str] = None,
    user: dict = Depends(require_roles("SUPER_ADMIN", "OPERATIONS", "SUPPORT"))
):
    """Generate transaction report with filters"""
    query = {
        "created_at": {"$gte": start_date, "$lte": end_date}
    }
    if merchant_id:
        query["merchant_id"] = merchant_id
    if card_type:
        query["card_type"] = card_type
    if status:
        query["status"] = status
    
    transactions = await db.transactions.find(query, {"_id": 0}).sort("created_at", -1).to_list(10000)
    
    # Calculate summary
    total_amount = sum(tx.get("amount", 0) for tx in transactions)
    approved_count = sum(1 for tx in transactions if tx.get("status") == "approved")
    declined_count = sum(1 for tx in transactions if tx.get("status") == "declined")
    refund_amount = sum(tx.get("amount", 0) for tx in transactions if tx.get("transaction_type") == "refund")
    
    # Group by card type
    by_card_type = {}
    for tx in transactions:
        ct = tx.get("card_type", "Unknown")
        if ct not in by_card_type:
            by_card_type[ct] = {"count": 0, "amount": 0}
        by_card_type[ct]["count"] += 1
        by_card_type[ct]["amount"] += tx.get("amount", 0)
    
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
async def get_batch_report(
    start_date: str,
    end_date: str,
    merchant_id: Optional[str] = None,
    user: dict = Depends(require_roles("SUPER_ADMIN", "OPERATIONS", "SUPPORT"))
):
    """Generate batch/settlement report grouped by day"""
    query = {
        "created_at": {"$gte": start_date, "$lte": end_date},
        "status": "approved"
    }
    if merchant_id:
        query["merchant_id"] = merchant_id
    
    transactions = await db.transactions.find(query, {"_id": 0}).sort("created_at", 1).to_list(10000)
    
    # Group by date
    batches = {}
    for tx in transactions:
        date_str = tx["created_at"][:10]  # Extract YYYY-MM-DD
        if date_str not in batches:
            batches[date_str] = {
                "date": date_str,
                "transaction_count": 0,
                "sales_count": 0,
                "sales_amount": 0,
                "refund_count": 0,
                "refund_amount": 0,
                "net_amount": 0
            }
        
        batches[date_str]["transaction_count"] += 1
        
        if tx.get("transaction_type") == "refund":
            batches[date_str]["refund_count"] += 1
            batches[date_str]["refund_amount"] += tx.get("amount", 0)
        else:
            batches[date_str]["sales_count"] += 1
            batches[date_str]["sales_amount"] += tx.get("amount", 0)
    
    # Calculate net amounts
    for batch in batches.values():
        batch["net_amount"] = round(batch["sales_amount"] - batch["refund_amount"], 2)
        batch["sales_amount"] = round(batch["sales_amount"], 2)
        batch["refund_amount"] = round(batch["refund_amount"], 2)
    
    batch_list = sorted(batches.values(), key=lambda x: x["date"], reverse=True)
    
    # Summary totals
    total_sales = sum(b["sales_amount"] for b in batch_list)
    total_refunds = sum(b["refund_amount"] for b in batch_list)
    
    return {
        "summary": {
            "total_batches": len(batch_list),
            "total_sales": round(total_sales, 2),
            "total_refunds": round(total_refunds, 2),
            "net_settlement": round(total_sales - total_refunds, 2)
        },
        "batches": batch_list,
        "report_generated": datetime.now(timezone.utc).isoformat()
    }

@api_router.get("/reports/settlement")
async def get_settlement_report(
    start_date: str,
    end_date: str,
    user: dict = Depends(require_roles("SUPER_ADMIN", "OPERATIONS"))
):
    """Generate settlement report grouped by merchant"""
    query = {
        "created_at": {"$gte": start_date, "$lte": end_date},
        "status": "approved"
    }
    
    transactions = await db.transactions.find(query, {"_id": 0}).to_list(10000)
    merchants = await db.merchants.find({}, {"_id": 0}).to_list(1000)
    merchant_map = {m["id"]: m for m in merchants}
    
    # Group by merchant
    settlements = {}
    for tx in transactions:
        mid = tx.get("merchant_id")
        if mid not in settlements:
            merchant = merchant_map.get(mid, {})
            settlements[mid] = {
                "merchant_id": mid,
                "merchant_name": merchant.get("business_name", "Unknown"),
                "transaction_count": 0,
                "gross_amount": 0,
                "refund_amount": 0,
                "net_amount": 0,
                "fee_amount": 0  # Would be calculated based on merchant rate
            }
        
        if tx.get("transaction_type") == "refund":
            settlements[mid]["refund_amount"] += tx.get("amount", 0)
        else:
            settlements[mid]["gross_amount"] += tx.get("amount", 0)
        settlements[mid]["transaction_count"] += 1
    
    # Calculate net and fees (2.9% + $0.30 example rate)
    for s in settlements.values():
        s["net_amount"] = round(s["gross_amount"] - s["refund_amount"], 2)
        s["fee_amount"] = round(s["gross_amount"] * 0.029 + (s["transaction_count"] * 0.30), 2)
        s["payout_amount"] = round(s["net_amount"] - s["fee_amount"], 2)
        s["gross_amount"] = round(s["gross_amount"], 2)
        s["refund_amount"] = round(s["refund_amount"], 2)
    
    settlement_list = sorted(settlements.values(), key=lambda x: x["net_amount"], reverse=True)
    
    total_gross = sum(s["gross_amount"] for s in settlement_list)
    total_fees = sum(s["fee_amount"] for s in settlement_list)
    total_payout = sum(s["payout_amount"] for s in settlement_list)
    
    return {
        "summary": {
            "total_merchants": len(settlement_list),
            "total_gross": round(total_gross, 2),
            "total_fees": round(total_fees, 2),
            "total_payout": round(total_payout, 2)
        },
        "settlements": settlement_list,
        "report_generated": datetime.now(timezone.utc).isoformat()
    }

@api_router.get("/reports/export")
async def export_transactions_csv(
    start_date: str,
    end_date: str,
    merchant_id: Optional[str] = None,
    user: dict = Depends(require_roles("SUPER_ADMIN", "OPERATIONS", "SUPPORT"))
):
    """Export transactions as CSV-ready data"""
    query = {
        "created_at": {"$gte": start_date, "$lte": end_date}
    }
    if merchant_id:
        query["merchant_id"] = merchant_id
    
    transactions = await db.transactions.find(query, {"_id": 0}).sort("created_at", -1).to_list(10000)
    
    # Format for CSV export
    csv_data = []
    for tx in transactions:
        csv_data.append({
            "Transaction ID": tx.get("id"),
            "Date": tx.get("created_at", "")[:19],
            "Merchant ID": tx.get("merchant_id"),
            "Type": tx.get("transaction_type", "sale"),
            "Amount": tx.get("amount"),
            "Card Type": tx.get("card_type"),
            "Card Last 4": tx.get("card_last_four", "****"),
            "Status": tx.get("status"),
            "Auth Code": tx.get("auth_code", ""),
            "Entry Mode": tx.get("entry_mode", ""),
            "Cardholder": tx.get("cardholder_name", "")
        })
    
    # Audit log
    await create_audit_log(user["user_id"], user["email"], "EXPORT", "report", None, {"type": "transactions", "count": len(csv_data)})
    
    return {"data": csv_data, "count": len(csv_data)}

# ==================== DASHBOARD STATS ====================

@api_router.get("/dashboard/stats")
async def get_dashboard_stats(user: dict = Depends(get_current_user)):
    # Get counts
    total_merchants = await db.merchants.count_documents({})
    active_merchants = await db.merchants.count_documents({"status": "active"})
    pending_merchants = await db.merchants.count_documents({"status": "pending"})
    
    total_terminals = await db.terminal_profiles.count_documents({})
    live_terminals = await db.terminal_profiles.count_documents({"provisioning_status": "live"})
    
    total_transactions = await db.transactions.count_documents({})
    
    # Get recent transactions for chart
    recent_transactions = await db.transactions.find({}, {"_id": 0}).sort("created_at", -1).to_list(30)
    
    return {
        "merchants": {
            "total": total_merchants,
            "active": active_merchants,
            "pending": pending_merchants
        },
        "terminals": {
            "total": total_terminals,
            "live": live_terminals
        },
        "transactions": {
            "total": total_transactions,
            "recent": recent_transactions
        }
    }

# ==================== SYSTEM LOGS (AUDIT TRAIL) ====================

@api_router.get("/logs")
async def get_system_logs(
    limit: int = 100,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    user_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user: dict = Depends(require_roles("SUPER_ADMIN"))
):
    """Get audit trail logs with filters"""
    query = {}
    if action:
        query["action"] = action
    if resource_type:
        query["resource_type"] = resource_type
    if user_id:
        query["user_id"] = user_id
    if start_date:
        query["timestamp"] = {"$gte": start_date}
    if end_date:
        if "timestamp" in query:
            query["timestamp"]["$lte"] = end_date
        else:
            query["timestamp"] = {"$lte": end_date}
    
    # Get audit logs
    audit_logs = await db.audit_logs.find(query, {"_id": 0}).sort("timestamp", -1).to_list(limit)
    
    # Also get activity from other collections if no filters
    if not query:
        logs = audit_logs.copy()
        
        # Get recent varsheet uploads
        varsheets = await db.varsheet_uploads.find({}, {"_id": 0}).sort("created_at", -1).to_list(limit // 4)
        for v in varsheets:
            logs.append({
                "id": v["id"],
                "action": "UPLOAD",
                "resource_type": "varsheet",
                "resource_id": v["id"],
                "user_email": v.get("created_by", "system"),
                "details": {"filename": v.get("filename", "Unknown")},
                "timestamp": v["created_at"]
            })
        
        # Get recent provisions
        provisions = await db.block29_provisions.find({}, {"_id": 0}).sort("created_at", -1).to_list(limit // 4)
        for p in provisions:
            logs.append({
                "id": p["id"],
                "action": "PROVISION",
                "resource_type": "block29",
                "resource_id": p["id"],
                "user_email": p.get("created_by", "system"),
                "details": {"processor": p["processor"]},
                "timestamp": p["created_at"]
            })
        
        # Sort all logs by timestamp
        logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return logs[:limit]
    
    return audit_logs

@api_router.get("/logs/actions")
async def get_log_action_types(user: dict = Depends(require_roles("SUPER_ADMIN"))):
    """Get distinct action types for filtering"""
    actions = await db.audit_logs.distinct("action")
    resource_types = await db.audit_logs.distinct("resource_type")
    return {
        "actions": actions or ["CREATE", "UPDATE", "DELETE", "VIRTUAL_TERMINAL", "REFUND", "EXPORT", "LOGIN"],
        "resource_types": resource_types or ["merchant", "terminal", "transaction", "varsheet", "user", "report"]
    }

@api_router.get("/logs/export")
async def export_audit_logs(
    start_date: str,
    end_date: str,
    user: dict = Depends(require_roles("SUPER_ADMIN"))
):
    """Export audit logs for compliance"""
    query = {
        "timestamp": {"$gte": start_date, "$lte": end_date}
    }
    logs = await db.audit_logs.find(query, {"_id": 0}).sort("timestamp", -1).to_list(10000)
    
    csv_data = []
    for log in logs:
        csv_data.append({
            "Timestamp": log.get("timestamp"),
            "User": log.get("user_email"),
            "Action": log.get("action"),
            "Resource Type": log.get("resource_type"),
            "Resource ID": log.get("resource_id", ""),
            "IP Address": log.get("ip_address", ""),
            "Details": json.dumps(log.get("details", {}))
        })
    
    return {"data": csv_data, "count": len(csv_data)}

# ==================== ROOT ENDPOINT ====================

@api_router.get("/")
async def root():
    return {"message": "SalonBookin Admin API", "version": "1.0.0"}

@api_router.get("/health")
async def health():
    return {"status": "healthy"}

# Include router and middleware
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    # Create indexes
    await db.users.create_index("email", unique=True)
    await db.merchants.create_index("id", unique=True)
    await db.terminal_profiles.create_index("id", unique=True)
    await db.varsheet_uploads.create_index("id", unique=True)
    
    # Create default admin user if not exists
    admin = await db.users.find_one({"email": "admin@salonbookin.com"})
    if not admin:
        await db.users.insert_one({
            "id": str(uuid.uuid4()),
            "email": "admin@salonbookin.com",
            "password": hash_password("admin123"),
            "name": "Super Admin",
            "role": "SUPER_ADMIN",
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        logger.info("Default admin user created: admin@salonbookin.com / admin123")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
