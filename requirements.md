# SalonBookin Admin Platform - Requirements & Architecture

## Original Problem Statement
Build an internal admin platform using Python FastAPI and MongoDB for SalonBookin. The system manages POS software customers, merchant processing through an internal Block29 gateway, and terminal provisioning using Luqra VAR sheets.

## Features Implemented

### 1. Authentication & Authorization
- JWT-based authentication
- Role-based access control (SUPER_ADMIN, OPERATIONS, SUPPORT, RISK, READ_ONLY)
- Default admin user: admin@salonbookin.com / admin123

### 2. Dashboard
- Stats overview (merchants, terminals, transactions, pending reviews)
- Transactions overview chart
- Merchant status pie chart
- Recent activity feed

### 3. Merchants Management
- Full CRUD operations
- Status management (pending, active, suspended)
- Search and filter functionality
- Contact information management

### 4. VAR Sheet Setup (Luqra)
- PDF upload functionality
- Automatic field extraction using regex patterns
- Editable parsed results with tabs:
  - Merchant Info
  - Terminal IDs
  - Card Types & Networks
  - Debit/Comments
- Terminal profile creation from parsed data
- Draft save and live marking

### 5. Terminals & Devices
- Terminal profile management
- Provisioning workflow (draft → ready → provisioned → live)
- Pairing token generation
- Support for Luqra provider

### 6. Transactions & Batches
- Transaction listing with filters
- Summary cards (total, volume, approval rate)
- Merchant and status filtering

### 7. Block29 Internal Gateway
- Routing architecture visualization
- Terminal provisioning to processors (Clover, Dejavoo, Valor PayTech)
- Provisioning history tracking

### 8. Affiliates & Agents
- Agent-merchant assignment
- Commission rate management
- Multi-level commission support

### 9. Users & Roles
- User management
- Role assignment and updates
- Permission-based access control

### 10. Settings
- Profile settings
- Notification preferences
- Security settings (2FA toggle)
- System information

## Technical Architecture

### Backend (FastAPI + MongoDB)
- **server.py**: Main application with all endpoints
- **Collections**: users, merchants, terminal_profiles, varsheet_uploads, pos_terminal_links, block29_provisions, agent_merchants, transactions

### Frontend (React + Tailwind CSS)
- Dark sidebar navigation
- Light content area
- Shadcn UI components
- Recharts for data visualization

### API Endpoints
- `/api/auth/*` - Authentication
- `/api/merchants/*` - Merchant CRUD
- `/api/admin/varsheet/*` - VAR sheet operations
- `/api/admin/terminals/*` - Terminal management
- `/api/block29/*` - Gateway provisioning
- `/api/agents/*` - Affiliate management
- `/api/transactions` - Transaction listing
- `/api/users/*` - User management
- `/api/dashboard/stats` - Dashboard statistics

## Design Theme
- Primary Color: Enterprise Blue (#0066CC)
- Sidebar: Dark Navy (#0F172A)
- Content: Light gray background (#F8FAFC)
- Typography: Manrope (headings), Inter (body), JetBrains Mono (monospace)

## Next Action Items
1. Implement actual PDF parsing with more advanced extraction (OCR if needed)
2. Add real-time notifications using WebSockets
3. Implement actual payment processor integrations (Clover, Dejavoo, Valor APIs)
4. Add audit logging for compliance
5. Implement data export functionality (CSV/Excel)
6. Add batch transaction processing
7. Implement email notifications for status changes

## Test Results
- Backend: 100% (20/20 tests passed)
- Frontend: 90%+ functional
