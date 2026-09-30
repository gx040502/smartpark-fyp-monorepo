# SmartPark API Testing Results

This document records the actual execution results of the 42 API test cases across the SmartPark microservices using Postman and Newman.

**Environment:**
- **Backend (Laravel):** `http://127.0.0.1:8000/api`
- **AI Service (FastAPI):** `http://localhost:8001`
- **Congestion Service (FastAPI):** `http://localhost:8002`
- **Database:** MySQL (Switched from SQLite; this fixed the `DATE_ADD` defect in `RoiController`)

## Summary
- **Total Requests:** 42
- **Executed Automatically:** 39
- **Excluded (Streaming):** 3 (API-35, API-37, API-42) - Must be executed manually to avoid timeout hanging.
- **Failures Detected:** 0

---

## Detailed Results

### Folder 1 - Auth
- **API-01 Register:** Passed (201 Created)
- **API-02 Login:** Passed (200 OK, token received)
- **API-03 Login invalid password:** Passed (422 Unprocessable Entity)
- **API-04 Get User:** Passed (200 OK)
- **API-05 Update Profile:** Passed (200 OK, name updated)
- **API-06 Logout:** Passed (200 OK)

### Folder 2 - Parking Sessions
- **API-07 Car Entry:** Passed (201 Created, status ENTER)
- **API-08 List Sessions:** Passed (200 OK)
- **API-09 Get Single Session:** Passed (200 OK)
- **API-10 Filter Options:** Passed (200 OK, returns colors and models)
- **API-11 Find By Plate Active:** Passed (200 OK)
- **API-12 Find By Plate Not Found:** Passed (404 Not Found)

### Folder 3 - Payment
- **API-13 Pay Initial:** Passed (200 OK, session became PAID)
- **API-14 Pay Initial Rejected:** Passed (400 Bad Request)
- **API-15 Pay Additional Accepted:** Passed (200 OK, using seeded TEST0021)
- **API-16 Pay Additional Rejected:** Passed (400 Bad Request, using seeded TEST0022)

### Folder 4 - Exit Gate
- **API-17 Free exit:** Passed (200 OK, exit_type `free`)
- **API-18 Normal paid exit:** Passed (200 OK, exit_type `normal`)
- **API-19 Unpaid:** Passed (403 Forbidden, exit_type `unpaid`)
- **API-20 Grace expired:** Passed (403 Forbidden, exit_type `grace_expired`)
- **API-21 Attribute mismatch:** Passed (403 Forbidden, alert_type `color_mismatch`)
- **API-22 Plate not found:** Passed (404 Not Found, alert_type `plate_not_found`)

### Folder 5 - Dashboard & Exit Alerts
- **API-23 Metrics:** Passed (200 OK)
- **API-24 Peak Hours:** Passed (200 OK)
- **API-25 Revenue Trends:** Passed (200 OK)
- **API-26 Demographics:** Passed (200 OK)
- **API-27 Payment Insights:** Passed (200 OK)
- **API-28 List Alerts:** Passed (200 OK)
- **API-29 Dismiss Alert:** Passed (200 OK)
- **API-30 Override Alert:** Passed (200 OK)

### Folder 6 - ROI and AI Query
- **API-31 Set ROI:** Passed (200 OK)
- **API-32 AI Query Select:** Passed (200 OK, returned data payload)
- **API-33 AI Query Drop Table:** Passed (403 Forbidden). 
  - *Database Verification:* Executing `SHOW TABLES LIKE 'users'` confirms that the `users` table **still exists** and was not dropped. The text-to-SQL layer successfully blocked the destructive command.
- **API-34 Webhook Congestion:** Passed (200 OK). 
  - *Observation:* This succeeded because the project was switched back to MySQL. If run on SQLite, this would fail with a 500 error due to `DATE_ADD`.

### Folder 7 - Supporting Services
- **API-36 AI Health:** Passed (200 OK).
- **API-38 Congestion Upload:** Passed (200 OK).
- **API-39 Congestion Set ROI:** Passed (200 OK)
- **API-40 Congestion Status:** Passed (200 OK)
- **API-41 Congestion Check:** Passed (200 OK)

## Streaming Endpoints (Manual Execution Required)
Because Newman does not natively support holding streaming connections without halting the entire test suite, the following endpoints were omitted from the automated collection and must be tested manually:
- **API-35 AI Streaming Query:** POST `/api/ai/query-stream`
- **API-37 Congestion Live Feed:** GET `http://localhost:8002/feed`
- **API-42 Congestion Metrics Stream:** GET `http://localhost:8002/metrics-stream`
