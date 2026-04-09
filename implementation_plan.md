# Smart Parking Management System — Implementation Plan

## Overview

Build an Admin Dashboard for a Smart Parking Management System with LPR capabilities. The system consists of a **Laravel 11 API backend** and a **Next.js frontend**, structured as two separate repositories within the workspace.

```
FYP DEVELOPMENT/
├── backend/          ← Laravel 11 API (Sanctum auth, MySQL)
└── frontend/         ← Next.js App Router (TypeScript, Tailwind, shadcn/ui)
```

---

## Phase 1: Project Scaffolding & Database Layer (Immediate Task)

### 1.1 Initialize Laravel Backend

#### [NEW] `backend/` — Laravel 11 project

```bash
composer create-project laravel/laravel backend
cd backend
php artisan install:api   # Installs Sanctum + api.php route file
```

> [!IMPORTANT]
> After creation, the `.env` file must be configured with the MySQL database credentials (DB_DATABASE, DB_USERNAME, DB_PASSWORD) pointing to the WAMP MySQL instance.

---

### 1.2 Database Migrations

#### [NEW] `backend/database/migrations/xxxx_create_parking_sessions_table.php`

| Column | Type | Notes |
|---|---|---|
| `id` | bigIncrements | Primary Key |
| `license_plate` | string | e.g., `ABC 1234` |
| `color` | string | e.g., `White`, `Black` |
| `model` | string | e.g., `Toyota Camry` |
| `entry_time` | timestamp | When car entered |
| `exit_time` | timestamp, nullable | When car exited |
| `amount_due` | decimal(8,2), default 0 | Calculated from duration |
| `status` | enum(`ENTER`, `PAID`, `COMPLETED`) | Session lifecycle |
| timestamps | | Laravel standard |

#### [NEW] `backend/database/migrations/xxxx_create_payment_receipts_table.php`

| Column | Type | Notes |
|---|---|---|
| `id` | bigIncrements | Primary Key |
| `parking_session_id` | foreignId | FK → `parking_sessions.id`, cascadeOnDelete |
| `total_amount` | decimal(8,2) | Amount paid |
| `payment_date` | timestamp | When payment occurred |
| `payment_method` | string | `Credit Card`, `Debit Card`, `Touch n Go` |
| timestamps | | Laravel standard |

The existing `users` migration from Laravel scaffolding will be used as-is for admin accounts.

---

### 1.3 Eloquent Models

#### [MODIFY] `backend/app/Models/User.php`
- Standard Laravel User model (no changes needed beyond scaffold).

#### [NEW] `backend/app/Models/ParkingSession.php`
- `$casts`: `entry_time` → datetime, `exit_time` → datetime, `amount_due` → decimal.
- Enum cast for `status` using a `ParkingStatus` backed enum.
- **Relationship**: `hasOne(PaymentReceipt::class)`

#### [NEW] `backend/app/Models/PaymentReceipt.php`
- `$casts`: `payment_date` → datetime, `total_amount` → decimal.
- **Relationship**: `belongsTo(ParkingSession::class)`

#### [NEW] `backend/app/Enums/ParkingStatus.php`
- Backed string enum: `ENTER`, `PAID`, `COMPLETED`.

---

### 1.4 Factories & Seeders

#### [NEW] `backend/database/factories/ParkingSessionFactory.php`
- Generates realistic Malaysian license plates (e.g., `WA 1234 B`, `JHR 5678`).
- Random car colors and models from curated lists.
- Entry times distributed across the last 30 days with realistic hour distributions (peaks at 8-9 AM, 5-6 PM).
- Status distribution: ~20% `ENTER`, ~30% `PAID`, ~50% `COMPLETED`.
- `amount_due` calculated from duration at RM 2.00/hour.

#### [NEW] `backend/database/factories/PaymentReceiptFactory.php`
- Links to a ParkingSession.
- `total_amount` mirrors session's `amount_due`.
- `payment_method` randomly from: `Credit Card`, `Debit Card`, `Touch n Go`.
- `payment_date` is between `entry_time` and `exit_time`.

#### [MODIFY] `backend/database/seeders/DatabaseSeeder.php`
- Creates 1 admin user: `admin@smartpark.com` / `password`.
- Creates 50 ParkingSession records with appropriate status distribution.
- For each `PAID` or `COMPLETED` session, creates a corresponding PaymentReceipt.

---

### 1.5 Initialize Next.js Frontend

#### [NEW] `frontend/` — Next.js project

```bash
npx -y create-next-app@latest ./frontend --typescript --tailwind --eslint --app --src-dir --import-alias "@/*" --use-npm
```

Post-init setup:
```bash
cd frontend
npx -y shadcn@latest init -d    # Default shadcn/ui setup
npm install apexcharts react-apexcharts flatpickr react-flatpickr zod react-hook-form @hookform/resolvers
```

---

## Phase 2: Laravel API Endpoints (After DB is established)

### API Routes (`routes/api.php`)

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/login` | Sanctum auth login |
| POST | `/register` | Register new admin |
| POST | `/logout` | Logout (auth:sanctum) |
| GET | `/user` | Get authenticated user |
| GET | `/dashboard/metrics` | Occupancy, revenue, dwell time |
| GET | `/dashboard/peak-hours` | Entry/exit frequency chart data |
| GET | `/dashboard/revenue-trends` | Last 7 days revenue |
| POST | `/roi/coordinates` | Forward ROI coords to Python microservice |
| GET | `/parking-sessions` | Paginated list with filters |
| GET | `/parking-sessions/{id}` | Single session with receipt |
| PUT | `/user/profile` | Update admin profile |

---

## Phase 3: Frontend Pages

### Page 1: Dashboard (`/dashboard`)
- Metric cards (occupancy, daily revenue, avg dwell time)
- Peak Hours line chart with date filter (Today / This Week / Custom via Flatpickr)
- Revenue Trends bar chart (7 days)
- Live Exit Camera Simulation container with video upload + ROI polygon drawing tool
- Traffic congestion alert UI (webhook-triggered)

### Page 2: AI Agent (`/ai-agent`)
- Static chat interface mockup — no backend logic
- Chat history window, message bubbles, input field, send button

### Page 3: Cars Directory (`/cars`)
- Data table of ParkingSessions joined with PaymentReceipts
- Search by license plate, filter by model/color/status
- Row-click modal with full details

### Page 4: Profile (`/profile`)
- Admin account management form (name, email, password change)

### Page 5 & 6: Login & Register (`/login`, `/register`)
- Zod validation schemas
- React Hook Form integration
- Sanctum API authentication

---

## User Review Required

> [!IMPORTANT]
> **MySQL Configuration**: What are your WAMP MySQL credentials? I'll assume `DB_DATABASE=smart_parking`, `DB_USERNAME=root`, `DB_PASSWORD=` (empty) on `127.0.0.1:3306`. Please confirm or correct.

> [!IMPORTANT]
> **Parking Rate**: I'll use **RM 2.00 per hour** for the seeder calculations. Confirm if this rate is correct.

> [!IMPORTANT]
> **Folder Structure**: The plan uses `backend/` and `frontend/` subdirectories within `FYP DEVELOPMENT/`. Confirm this is acceptable.

---

## Verification Plan

### Automated Tests
```bash
# After Phase 1
cd backend
php artisan migrate
php artisan db:seed
php artisan tinker --execute="echo App\Models\ParkingSession::count();"   # Expect: 50
php artisan tinker --execute="echo App\Models\PaymentReceipt::count();"   # Expect: ~40 (PAID + COMPLETED)
```

### Manual Verification
- Run `php artisan serve` and verify API endpoints via browser/Postman
- Run `npm run dev` in frontend and verify pages render correctly
- Visual inspection of charts, tables, and UI components
