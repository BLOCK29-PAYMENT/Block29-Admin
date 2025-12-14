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
    return transaction_doc

@api_router.get("/transactions")
async def list_transactions(
    merchant_id: Optional[str] = None,
    status: Optional[str] = None,
    user: dict = Depends(require_roles("SUPER_ADMIN", "OPERATIONS", "SUPPORT"))
):
    query = {}
    if merchant_id:
        query["merchant_id"] = merchant_id
    if status:
        query["status"] = status
    
    transactions = await db.transactions.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return transactions

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

# ==================== SYSTEM LOGS ====================

@api_router.get("/logs")
async def get_system_logs(
    limit: int = 100,
    user: dict = Depends(require_roles("SUPER_ADMIN"))
):
    # Aggregate logs from different collections
    logs = []
    
    # Get recent varsheet uploads
    varsheets = await db.varsheet_uploads.find({}, {"_id": 0}).sort("created_at", -1).to_list(limit // 3)
    for v in varsheets:
        logs.append({
            "type": "varsheet_upload",
            "id": v["id"],
            "description": f"VAR sheet uploaded: {v.get('filename', 'Unknown')}",
            "timestamp": v["created_at"]
        })
    
    # Get recent provisions
    provisions = await db.block29_provisions.find({}, {"_id": 0}).sort("created_at", -1).to_list(limit // 3)
    for p in provisions:
        logs.append({
            "type": "provision",
            "id": p["id"],
            "description": f"Block29 provision for {p['processor']}",
            "timestamp": p["created_at"]
        })
    
    # Get recent terminal status changes
    terminals = await db.terminal_profiles.find({}, {"_id": 0}).sort("created_at", -1).to_list(limit // 3)
    for t in terminals:
        logs.append({
            "type": "terminal",
            "id": t["id"],
            "description": f"Terminal {t.get('terminal_number', 'N/A')} - {t['provisioning_status']}",
            "timestamp": t["created_at"]
        })
    
    # Sort all logs by timestamp
    logs.sort(key=lambda x: x["timestamp"], reverse=True)
    return logs[:limit]

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
