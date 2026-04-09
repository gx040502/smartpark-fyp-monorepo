# Smart Parking System — Phase 1 Walkthrough

## What Was Built

### Backend (`backend/`)

| Item | Details |
|---|---|
| **Framework** | Laravel (composer installed v13.4.0 with PHP 8.4) |
| **Auth** | Laravel Sanctum v4.3.1 (token-based) |
| **Database** | MySQL `smart_parking` on `127.0.0.1:3306` |

#### Database Schema (6 migrations ran successfully)

```
users                    → Standard Laravel auth (+ HasApiTokens)
personal_access_tokens   → Sanctum tokens
cache / jobs             → Laravel infrastructure
parking_sessions         → Core parking tracking
payment_receipts         → Financial transactions (FK → parking_sessions)
```

#### Files Created

| File | Purpose |
|---|---|
| [ParkingStatus.php](file:///c:/Users/Tan%20Gyap%20Xun/Desktop/DEGREE/Y3S2/FYP%20DEVELOPMENT/backend/app/Enums/ParkingStatus.php) | Backed string enum: `ENTER`, `PAID`, `COMPLETED` |
| [ParkingSession.php](file:///c:/Users/Tan%20Gyap%20Xun/Desktop/DEGREE/Y3S2/FYP%20DEVELOPMENT/backend/app/Models/ParkingSession.php) | Model with enum cast, datetime casts, `hasOne(PaymentReceipt)` |
| [PaymentReceipt.php](file:///c:/Users/Tan%20Gyap%20Xun/Desktop/DEGREE/Y3S2/FYP%20DEVELOPMENT/backend/app/Models/PaymentReceipt.php) | Model with `belongsTo(ParkingSession)` |
| [ParkingSessionFactory.php](file:///c:/Users/Tan%20Gyap%20Xun/Desktop/DEGREE/Y3S2/FYP%20DEVELOPMENT/backend/database/factories/ParkingSessionFactory.php) | Malaysian plates, local car models, peak-hour weighting, RM 2/hr |
| [PaymentReceiptFactory.php](file:///c:/Users/Tan%20Gyap%20Xun/Desktop/DEGREE/Y3S2/FYP%20DEVELOPMENT/backend/database/factories/PaymentReceiptFactory.php) | `forSession()` helper mirrors amount & realistic payment dates |
| [DatabaseSeeder.php](file:///c:/Users/Tan%20Gyap%20Xun/Desktop/DEGREE/Y3S2/FYP%20DEVELOPMENT/backend/database/seeders/DatabaseSeeder.php) | 1 admin + 50 sessions + receipts for PAID/COMPLETED |

#### Seeding Results

```
Users:            1    (admin@smartpark.com / password)
Parking Sessions: 50
  - ENTER:        11
  - PAID:         20
  - COMPLETED:    19
Payment Receipts: 39
```

#### Bug Fix Applied
- Added `Schema::defaultStringLength(191)` in [AppServiceProvider.php](file:///c:/Users/Tan%20Gyap%20Xun/Desktop/DEGREE/Y3S2/FYP%20DEVELOPMENT/backend/app/Providers/AppServiceProvider.php) to resolve MySQL utf8mb4 key length error.

---

### Frontend (`frontend/`)

| Item | Details |
|---|---|
| **Framework** | Next.js (App Router, TypeScript, Tailwind CSS v4) |
| **UI Library** | shadcn/ui (14 components installed) |
| **Charts** | apexcharts + react-apexcharts |
| **Date Picker** | flatpickr + react-flatpickr |
| **Form Handling** | react-hook-form + @hookform/resolvers + zod |

#### shadcn/ui Components Installed
`button`, `card`, `badge`, `table`, `dialog`, `input`, `label`, `select`, `separator`, `dropdown-menu`, `avatar`, `sheet`, `tabs`, `textarea`, `scroll-area`

---

## Next Steps (Phase 2)
Build the Laravel API endpoints (auth, dashboard metrics, parking sessions CRUD) and then the frontend pages.
