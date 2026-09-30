SELECT '=== ROW COUNTS ===' AS section;
SELECT 'parking_sessions' AS tbl, COUNT(*) AS rows_count FROM parking_sessions
UNION ALL SELECT 'payment_receipts', COUNT(*) FROM payment_receipts
UNION ALL SELECT 'exit_alerts', COUNT(*) FROM exit_alerts;

SELECT '=== PARKING SESSIONS ===' AS section;
SELECT id, license_plate, color, model, entry_time, exit_time,
       grace_end_time, amount_due, status
FROM parking_sessions ORDER BY id LIMIT 60;

SELECT '=== PAYMENT RECEIPTS ===' AS section;
SELECT id, receipt_number, parking_session_id, total_amount,
       payment_date, payment_method, payment_type
FROM payment_receipts ORDER BY id LIMIT 60;

SELECT '=== EXIT ALERTS ===' AS section;
SELECT id, alert_type, license_plate, detected_color, detected_model,
       expected_color, expected_model, session_id, status, created_at
FROM exit_alerts ORDER BY id LIMIT 60;

SELECT '=== DISTINCT MODEL ===' AS section;
SELECT DISTINCT model FROM parking_sessions;

SELECT '=== DISTINCT COLOR ===' AS section;
SELECT DISTINCT color FROM parking_sessions;

SELECT '=== DISTINCT PAYMENT METHOD ===' AS section;
SELECT DISTINCT payment_method FROM payment_receipts;

SELECT '=== DISTINCT PAYMENT TYPE ===' AS section;
SELECT DISTINCT payment_type FROM payment_receipts;

SELECT '=== DISTINCT ALERT TYPE / STATUS ===' AS section;
SELECT DISTINCT alert_type, status FROM exit_alerts;

SELECT '=== DATE RANGE CHECK ===' AS section;
SELECT MIN(entry_time) AS earliest_entry, MAX(entry_time) AS latest_entry,
       CURDATE() AS today FROM parking_sessions;