"""
Evaluation dataset for the SmartPark Text-to-SQL AI Agent.
All reference SQL verified against the fyp_parking snapshot (2026-08-18).
Expected row counts noted per case.
"""

DATASET = [
    # ---------------- EASY ----------------
    {
        "id": "E01", "category": "Easy",
        "context": "parking_sessions(license_plate, color, model, entry_time, status)",
        "question": "Show me all the vehicles that are currently still parked in the facility.",
        "reference_sql": "SELECT license_plate, color, model, entry_time FROM parking_sessions WHERE status = 'ENTER';"
    },  # 1 row
    {
        "id": "E02", "category": "Easy",
        "context": "parking_sessions(license_plate, color, model, entry_time, status)",
        "question": "List every black car recorded in the system.",
        "reference_sql": "SELECT license_plate, model, entry_time, status FROM parking_sessions WHERE color = 'Black';"
    },  # 5 rows
    {
        "id": "E03", "category": "Easy",
        "context": "parking_sessions(license_plate, entry_time, exit_time, status)",
        "question": "Which vehicles have already completed their parking session and left?",
        "reference_sql": "SELECT license_plate, entry_time, exit_time FROM parking_sessions WHERE status = 'COMPLETED';"
    },  # 9 rows
    {
        "id": "E04", "category": "Easy",
        "context": "parking_sessions(license_plate, color, model, entry_time, status)",
        "question": "Show me all Proton vehicles in the system.",
        "reference_sql": "SELECT license_plate, color, entry_time, status FROM parking_sessions WHERE model = 'proton';"
    },  # 4 rows
    {
        "id": "E05", "category": "Easy",
        "context": "parking_sessions(license_plate, color, model, entry_time)",
        "question": "Give me the 5 most recent vehicle entries.",
        "reference_sql": "SELECT license_plate, model, color, entry_time FROM parking_sessions ORDER BY entry_time DESC LIMIT 5;"
    },  # 5 rows, order-sensitive
    {
        "id": "E06", "category": "Easy",
        "context": "parking_sessions(license_plate, color, model, entry_time, exit_time, amount_due, status)",
        "question": "What are the details of the vehicle with plate number AMF9050?",
        "reference_sql": "SELECT license_plate, color, model, entry_time, exit_time, amount_due, status FROM parking_sessions WHERE license_plate = 'AMF9050';"
    },  # 1 row
    {
        "id": "E07", "category": "Easy",
        "context": "parking_sessions(license_plate, model, amount_due, grace_end_time, status)",
        "question": "List all vehicles that have paid but have not left the facility yet.",
        "reference_sql": "SELECT license_plate, model, amount_due, grace_end_time FROM parking_sessions WHERE status = 'PAID';"
    },  # 3 rows
    {
        "id": "E08", "category": "Easy",
        "context": "payment_receipts(receipt_number, total_amount, payment_date, payment_method)",
        "question": "Show all payment records made using Touch n Go.",
        "reference_sql": "SELECT receipt_number, total_amount, payment_date FROM payment_receipts WHERE payment_method = 'Touch n Go';"
    },  # 4 rows — REWRITTEN: 'ewallet' does not exist
    {
        "id": "E09", "category": "Easy",
        "context": "exit_alerts(alert_type, license_plate, status, created_at)",
        "question": "List all exit alerts that are still pending.",
        "reference_sql": "SELECT alert_type, license_plate, created_at FROM exit_alerts WHERE status = 'PENDING';"
    },  # 1 row
    {
        "id": "E10", "category": "Easy",
        "context": "parking_sessions(model)",
        "question": "What distinct car makes have been recorded in the parking system?",
        "reference_sql": "SELECT DISTINCT model FROM parking_sessions;"
    },  # 5 rows

    # ---------------- MEDIUM ----------------
    {
        "id": "M01", "category": "Medium",
        "context": "parking_sessions(status)",
        "question": "How many vehicles are currently parked in the facility?",
        "reference_sql": "SELECT COUNT(*) AS total_parked FROM parking_sessions WHERE status = 'ENTER';"
    },  # 1 row, value 1
    {
        "id": "M02", "category": "Medium",
        "context": "parking_sessions(entry_time)",
        "question": "How many vehicles entered the facility today?",
        "reference_sql": "SELECT COUNT(*) AS total_entries FROM parking_sessions WHERE DATE(entry_time) = CURDATE();"
    },  # 1 row, value 4 (as of 2026-08-18)
    {
        "id": "M03", "category": "Medium",
        "context": "parking_sessions(model)",
        "question": "Count the number of vehicles for each car make, sorted from most to least.",
        "reference_sql": "SELECT model AS car_make, COUNT(*) AS total_sessions FROM parking_sessions GROUP BY model ORDER BY total_sessions DESC;"
    },  # 5 rows, order-sensitive
    {
        "id": "M04", "category": "Medium",
        "context": "payment_receipts(total_amount, payment_date)",
        "question": "What is the total revenue collected today?",
        "reference_sql": "SELECT SUM(total_amount) AS total_revenue FROM payment_receipts WHERE DATE(payment_date) = CURDATE();"
    },  # 1 row
    {
        "id": "M05", "category": "Medium",
        "context": "parking_sessions(entry_time)",
        "question": "Show the number of vehicle entries for each hour of the day.",
        "reference_sql": "SELECT HOUR(entry_time) AS hour_of_day, COUNT(*) AS total_entries FROM parking_sessions GROUP BY HOUR(entry_time) ORDER BY hour_of_day;"
    },  # 6 rows
    {
        "id": "M06", "category": "Medium",
        "context": "parking_sessions(entry_time, exit_time, status)",
        "question": "What is the average parking duration in minutes for completed sessions?",
        "reference_sql": "SELECT ROUND(AVG(TIMESTAMPDIFF(MINUTE, entry_time, exit_time)), 2) AS avg_duration_minutes FROM parking_sessions WHERE status = 'COMPLETED' AND exit_time IS NOT NULL;"
    },  # 1 row
    {
        "id": "M07", "category": "Medium",
        "context": "payment_receipts(payment_method, total_amount)",
        "question": "Break down the total payments collected by payment method.",
        "reference_sql": "SELECT payment_method, SUM(total_amount) AS total_collected FROM payment_receipts GROUP BY payment_method;"
    },  # 2 rows
    {
        "id": "M08", "category": "Medium",
        "context": "payment_receipts(payment_type, total_amount)",
        "question": "How many payments of each payment type have been recorded, and what is the total for each?",
        "reference_sql": "SELECT payment_type, COUNT(*) AS total_payments, SUM(total_amount) AS total_collected FROM payment_receipts GROUP BY payment_type;"
    },  # 2 rows — REWRITTEN: exit_alerts too sparse to aggregate
    {
        "id": "M09", "category": "Medium",
        "context": "parking_sessions(model)",
        "question": "Which car makes have more than two recorded parking sessions?",
        "reference_sql": "SELECT model AS car_make FROM parking_sessions GROUP BY model HAVING COUNT(*) > 2;"
    },  # 2 rows — threshold lowered from 5
    {
        "id": "M10", "category": "Medium",
        "context": "payment_receipts(total_amount, payment_date)",
        "question": "What was the total revenue collected on each day in August 2026?",
        "reference_sql": "SELECT DATE(payment_date) AS payment_day, SUM(total_amount) AS daily_revenue FROM payment_receipts WHERE payment_date >= '2026-08-01' AND payment_date < '2026-09-01' GROUP BY DATE(payment_date);"
    },  # 6 rows — fixed range, more stable than rolling 7 days

    # ---------------- HARD ----------------
    {
        "id": "H01", "category": "Hard",
        "context": "parking_sessions(id, model, entry_time, exit_time, status) JOIN payment_receipts(parking_session_id, total_amount)",
        "question": "For each car make, show the total amount collected and the average parking duration in minutes for completed sessions.",
        "reference_sql": "SELECT ps.model AS car_make, SUM(pr.total_amount) AS total_collected, ROUND(AVG(TIMESTAMPDIFF(MINUTE, ps.entry_time, ps.exit_time)), 2) AS avg_duration_minutes FROM parking_sessions ps JOIN payment_receipts pr ON pr.parking_session_id = ps.id WHERE ps.status = 'COMPLETED' GROUP BY ps.model;"
    },  # 4 rows — over-specified COUNT(*) removed
    {
        "id": "H02", "category": "Hard",
        "context": "parking_sessions(id, license_plate, model, status) LEFT JOIN payment_receipts(id, parking_session_id)",
        "question": "List the vehicles that are currently parked and have no payment receipt recorded.",
        "reference_sql": "SELECT ps.license_plate, ps.model, ps.entry_time FROM parking_sessions ps LEFT JOIN payment_receipts pr ON pr.parking_session_id = ps.id WHERE ps.status = 'ENTER' AND pr.id IS NULL;"
    },  # 1 row — REWRITTEN: all COMPLETED sessions have receipts
    {
        "id": "H03", "category": "Hard",
        "context": "parking_sessions(id, license_plate, model) JOIN payment_receipts(parking_session_id, total_amount)",
        "question": "Show the license plate, car make, and total amount paid for the three highest-paying sessions.",
        "reference_sql": "SELECT ps.license_plate, ps.model AS car_make, SUM(pr.total_amount) AS total_paid FROM parking_sessions ps JOIN payment_receipts pr ON pr.parking_session_id = ps.id GROUP BY ps.id, ps.license_plate, ps.model ORDER BY total_paid DESC LIMIT 3;"
    },  # 3 rows, order-sensitive
    {
        "id": "H04", "category": "Hard",
        "context": "exit_alerts(license_plate, alert_type, expected_model, detected_model, session_id) JOIN parking_sessions(id, entry_time)",
        "question": "Which vehicles triggered a car make mismatch alert, showing the expected versus detected make together with the entry time of that session?",
        "reference_sql": "SELECT ea.license_plate, ea.expected_model, ea.detected_model, ps.entry_time FROM exit_alerts ea JOIN parking_sessions ps ON ea.session_id = ps.id WHERE ea.alert_type = 'model_mismatch';"
    },  # 1 row
    {
        "id": "H05", "category": "Hard",
        "context": "exit_alerts(session_id, alert_type, status) JOIN parking_sessions(id, license_plate, model, color)",
        "question": "For every exit alert raised, show the alert type together with the car make and colour recorded for that session.",
        "reference_sql": "SELECT ea.alert_type, ps.model AS car_make, ps.color FROM exit_alerts ea JOIN parking_sessions ps ON ea.session_id = ps.id;"
    },  # 1 row — REWRITTEN: aggregation meaningless with one alert
    {
        "id": "H06", "category": "Hard",
        "context": "parking_sessions(license_plate, model, amount_due, status)",
        "question": "Show every session whose amount due is higher than the average amount due across all sessions.",
        "reference_sql": "SELECT license_plate, model, amount_due, status FROM parking_sessions WHERE amount_due > (SELECT AVG(amount_due) FROM parking_sessions);"
    },  # 8 rows
    {
        "id": "H07", "category": "Hard",
        "context": "parking_sessions(id, model) LEFT JOIN exit_alerts(session_id)",
        "question": "For each car make, what percentage of its sessions have triggered an exit alert?",
        "reference_sql": "SELECT ps.model AS car_make, ROUND(COUNT(DISTINCT ea.session_id) * 100.0 / COUNT(DISTINCT ps.id), 2) AS alert_percentage FROM parking_sessions ps LEFT JOIN exit_alerts ea ON ea.session_id = ps.id GROUP BY ps.model;"
    },  # 5 rows — over-specified columns removed
    {
        "id": "H08", "category": "Hard",
        "context": "parking_sessions(id, license_plate, model) JOIN payment_receipts(parking_session_id, total_amount, payment_type) x2",
        "question": "List the sessions that received an additional payment, showing both the initial amount and the additional amount.",
        "reference_sql": "SELECT ps.license_plate, ps.model AS car_make, initial_pay.total_amount AS initial_amount, extra_pay.total_amount AS additional_amount FROM parking_sessions ps JOIN payment_receipts initial_pay ON initial_pay.parking_session_id = ps.id AND initial_pay.payment_type = 'initial' JOIN payment_receipts extra_pay ON extra_pay.parking_session_id = ps.id AND extra_pay.payment_type = 'additional';"
    },  # 1 row — REWRITTEN: 'penalty' does not exist, 'additional' does
    {
        "id": "H09", "category": "Hard",
        "context": "payment_receipts(total_amount, payment_date)",
        "question": "Which day in August 2026 had the highest revenue, and how much was collected?",
        "reference_sql": "SELECT DATE(payment_date) AS payment_day, SUM(total_amount) AS daily_revenue FROM payment_receipts WHERE payment_date >= '2026-08-01' AND payment_date < '2026-09-01' GROUP BY DATE(payment_date) ORDER BY daily_revenue DESC LIMIT 1;"
    },  # 1 row
    {
        "id": "H10", "category": "Hard",
        "context": "parking_sessions(model, entry_time, exit_time)",
        "question": "Show the car makes whose average parking duration is longer than the overall average parking duration.",
        "reference_sql": "SELECT model AS car_make, ROUND(AVG(TIMESTAMPDIFF(MINUTE, entry_time, exit_time)), 2) AS avg_duration_minutes FROM parking_sessions WHERE exit_time IS NOT NULL GROUP BY model HAVING AVG(TIMESTAMPDIFF(MINUTE, entry_time, exit_time)) > (SELECT AVG(TIMESTAMPDIFF(MINUTE, entry_time, exit_time)) FROM parking_sessions WHERE exit_time IS NOT NULL);"
    },  # 2 rows
]