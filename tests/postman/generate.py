import json

collection = {
    "info": {
        "name": "SmartPark API Tests",
        "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
    },
    "item": []
}

def create_request(name, method, url, body=None, test_script=None, timeout=None):
    req = {
        "name": name,
        "request": {
            "method": method,
            "header": [
                {"key": "Accept", "value": "application/json"}
            ],
            "url": {
                "raw": url,
                "host": [url.split("/")[0]],
                "path": url.split("/")[1:]
            }
        },
        "response": []
    }
    
    if "api/" in url and not url.endswith("/login") and not url.endswith("/register") and not "parking-sessions/plate" in url and not "parking-sessions/car-" in url and not url.endswith("/pay") and not url.endswith("/pay-additional") and not url.endswith("/query") and not url.endswith("/congestion"):
        req["request"]["auth"] = {
            "type": "bearer",
            "bearer": [
                {"key": "token", "value": "{{token}}", "type": "string"}
            ]
        }
        
    if body:
        if isinstance(body, dict):
            req["request"]["body"] = {
                "mode": "raw",
                "raw": json.dumps(body),
                "options": {"raw": {"language": "json"}}
            }
        else:
            req["request"]["body"] = body
            
    events = []
    if test_script:
        events.append({
            "listen": "test",
            "script": {
                "exec": test_script.split("\n"),
                "type": "text/javascript"
            }
        })
        
    if events:
        req["event"] = events
        
    return req

# FOLDER 1 - Auth
f1 = {"name": "Folder 1 - Auth", "item": []}

f1["item"].append(create_request(
    "API-01 Register", "POST", "{{base_url}}/api/register",
    body={"name": "Test User", "email": "test@test.com", "password": "password", "password_confirmation": "password"},
    test_script="pm.test(\"Status code is 201\", function () { pm.response.to.have.status(201); });"
))

f1["item"].append(create_request(
    "API-02 Login", "POST", "{{base_url}}/api/login",
    body={"email": "test@test.com", "password": "password"},
    test_script="pm.test(\"Status code is 200\", function () { pm.response.to.have.status(200); });\npm.test(\"Has token\", function () { var d = pm.response.json(); pm.expect(d).to.have.property('token'); pm.environment.set('token', d.token); });"
))

f1["item"].append(create_request(
    "API-03 Login invalid password", "POST", "{{base_url}}/api/login",
    body={"email": "test@test.com", "password": "wrongpassword"},
    test_script="pm.test(\"Status code is 422\", function () { pm.response.to.have.status(422); });"
))

r4 = create_request(
    "API-04 Get User", "GET", "{{base_url}}/api/user",
    test_script="pm.test(\"Status code is 200\", function () { pm.response.to.have.status(200); });"
)
r4["request"]["auth"] = {"type": "bearer", "bearer": [{"key": "token", "value": "{{token}}", "type": "string"}]}
f1["item"].append(r4)

r5 = create_request(
    "API-05 Update Profile", "PUT", "{{base_url}}/api/user/profile",
    body={"name": "Test User Updated", "email": "test@test.com"},
    test_script="pm.test(\"Status code is 200\", function () { pm.response.to.have.status(200); });\npm.test(\"Name updated\", function () { var d = pm.response.json(); pm.expect(d.user.name).to.eql('Test User Updated'); });"
)
r5["request"]["auth"] = {"type": "bearer", "bearer": [{"key": "token", "value": "{{token}}", "type": "string"}]}
f1["item"].append(r5)

r6 = create_request(
    "API-06 Logout", "POST", "{{base_url}}/api/logout",
    test_script="pm.test(\"Status code is 200\", function () { pm.response.to.have.status(200); });"
)
r6["request"]["auth"] = {"type": "bearer", "bearer": [{"key": "token", "value": "{{token}}", "type": "string"}]}
f1["item"].append(r6)

# RELOGIN (Helper for rest of suite)
r_relogin = create_request(
    "API-06.5 Relogin", "POST", "{{base_url}}/api/login",
    body={"email": "test@test.com", "password": "password"},
    test_script="pm.environment.set('token', pm.response.json().token);"
)
f1["item"].append(r_relogin)


# FOLDER 2 - Parking Sessions
f2 = {"name": "Folder 2 - Parking Sessions", "item": []}

f2["item"].append(create_request(
    "API-07 Car Entry", "POST", "{{base_url}}/api/parking-sessions/car-entry",
    body={"license_plate": "TEST9999", "color": "Red", "model": "SUV"},
    test_script="pm.test(\"Status code is 201\", function () { pm.response.to.have.status(201); });\npm.test(\"Status is ENTER\", function () { var d = pm.response.json(); pm.expect(d.status).to.eql('ENTER'); pm.environment.set('session_id', d.id); });"
))

r8 = create_request(
    "API-08 List Sessions", "GET", "{{base_url}}/api/parking-sessions?per_page=15",
    test_script="pm.test(\"Status code is 200\", function () { pm.response.to.have.status(200); });"
)
r8["request"]["auth"] = {"type": "bearer", "bearer": [{"key": "token", "value": "{{token}}", "type": "string"}]}
f2["item"].append(r8)

r9 = create_request(
    "API-09 Get Single Session", "GET", "{{base_url}}/api/parking-sessions/{{session_id}}",
    test_script="pm.test(\"Status code is 200\", function () { pm.response.to.have.status(200); });"
)
r9["request"]["auth"] = {"type": "bearer", "bearer": [{"key": "token", "value": "{{token}}", "type": "string"}]}
f2["item"].append(r9)

r10 = create_request(
    "API-10 Filter Options", "GET", "{{base_url}}/api/parking-sessions/filter-options",
    test_script="pm.test(\"Status code is 200\", function () { pm.response.to.have.status(200); });\npm.test(\"Has colors and models\", function () { var d = pm.response.json(); pm.expect(d).to.have.property('colors'); });"
)
r10["request"]["auth"] = {"type": "bearer", "bearer": [{"key": "token", "value": "{{token}}", "type": "string"}]}
f2["item"].append(r10)

f2["item"].append(create_request(
    "API-11 Find By Plate Active", "GET", "{{base_url}}/api/parking-sessions/plate/TEST9999",
    test_script="pm.test(\"Status code is 200\", function () { pm.response.to.have.status(200); });"
))

f2["item"].append(create_request(
    "API-12 Find By Plate Not Found", "GET", "{{base_url}}/api/parking-sessions/plate/ZZZ9999",
    test_script="pm.test(\"Status code is 404\", function () { pm.response.to.have.status(404); });"
))


# FOLDER 3 - Payment
f3 = {"name": "Folder 3 - Payment", "item": []}

f3["item"].append(create_request(
    "API-13 Pay Initial", "POST", "{{base_url}}/api/parking-sessions/{{session_id}}/pay",
    body={"payment_method": "Credit Card"},
    test_script="pm.test(\"Status code is 200\", function () { pm.response.to.have.status(200); });\npm.test(\"Session PAID\", function () { var d = pm.response.json(); pm.expect(d.session.status).to.eql('PAID'); });"
))

f3["item"].append(create_request(
    "API-14 Pay Initial Rejected", "POST", "{{base_url}}/api/parking-sessions/{{session_id}}/pay",
    body={"payment_method": "Credit Card"},
    test_script="pm.test(\"Status code is 400\", function () { pm.response.to.have.status(400); });"
))

r_get_21 = create_request(
    "API-14.1 Get TEST0021", "GET", "{{base_url}}/api/parking-sessions/plate/TEST0021",
    test_script="pm.environment.set('session_21_id', pm.response.json().id);"
)
f3["item"].append(r_get_21)

r_get_22 = create_request(
    "API-14.2 Get TEST0022", "GET", "{{base_url}}/api/parking-sessions/plate/TEST0022",
    test_script="pm.environment.set('session_22_id', pm.response.json().id);"
)
f3["item"].append(r_get_22)

f3["item"].append(create_request(
    "API-15 Pay Additional Accepted", "POST", "{{base_url}}/api/parking-sessions/{{session_21_id}}/pay-additional",
    body={"payment_method": "Credit Card"},
    test_script="pm.test(\"Status code is 200\", function () { pm.response.to.have.status(200); });"
))

f3["item"].append(create_request(
    "API-16 Pay Additional Rejected", "POST", "{{base_url}}/api/parking-sessions/{{session_22_id}}/pay-additional",
    body={"payment_method": "Credit Card"},
    test_script="pm.test(\"Status code is 400\", function () { pm.response.to.have.status(400); });"
))


# FOLDER 4 - Exit Gate
f4 = {"name": "Folder 4 - Exit Gate", "item": []}

f4["item"].append(create_request(
    "API-17 Free exit", "POST", "{{base_url}}/api/parking-sessions/car-exit",
    body={"license_plate": "TEST0016", "color": "White", "model": "Sedan"},
    test_script="pm.test(\"Status 200\", function () { pm.response.to.have.status(200); });\npm.test(\"free\", function () { var d = pm.response.json(); pm.expect(d.exit_type).to.eql(\"free\"); });"
))

f4["item"].append(create_request(
    "API-18 Normal paid exit", "POST", "{{base_url}}/api/parking-sessions/car-exit",
    body={"license_plate": "TEST0017", "color": "White", "model": "Sedan"},
    test_script="pm.test(\"Status 200\", function () { pm.response.to.have.status(200); });\npm.test(\"normal\", function () { var d = pm.response.json(); pm.expect(d.exit_type).to.eql(\"normal\"); });"
))

f4["item"].append(create_request(
    "API-19 Unpaid", "POST", "{{base_url}}/api/parking-sessions/car-exit",
    body={"license_plate": "TEST0018", "color": "White", "model": "Sedan"},
    test_script="pm.test(\"Status 403\", function () { pm.response.to.have.status(403); });\npm.test(\"unpaid\", function () { var d = pm.response.json(); pm.expect(d.exit_type).to.eql(\"unpaid\"); });"
))

f4["item"].append(create_request(
    "API-20 Grace expired", "POST", "{{base_url}}/api/parking-sessions/car-exit",
    body={"license_plate": "TEST0019", "color": "White", "model": "Sedan"},
    test_script="pm.test(\"Status 403\", function () { pm.response.to.have.status(403); });\npm.test(\"grace_expired\", function () { var d = pm.response.json(); pm.expect(d.exit_type).to.eql(\"grace_expired\"); });"
))

f4["item"].append(create_request(
    "API-21 Attribute mismatch", "POST", "{{base_url}}/api/parking-sessions/car-exit",
    body={"license_plate": "TEST0020", "color": "Green", "model": "Sedan"},
    test_script="pm.test(\"Status 403\", function () { pm.response.to.have.status(403); });\npm.test(\"color_mismatch\", function () { var d = pm.response.json(); pm.expect(d.alert_type).to.eql(\"color_mismatch\"); });"
))

f4["item"].append(create_request(
    "API-22 Plate not found", "POST", "{{base_url}}/api/parking-sessions/car-exit",
    body={"license_plate": "ZZZ9999", "color": "White", "model": "Sedan"},
    test_script="pm.test(\"Status 404\", function () { pm.response.to.have.status(404); });\npm.test(\"plate_not_found\", function () { var d = pm.response.json(); pm.expect(d.alert_type).to.eql(\"plate_not_found\"); });"
))


# FOLDER 5 - Dashboard & Alerts
f5 = {"name": "Folder 5 - Dashboard & Exit Alerts", "item": []}

f5["item"].append(create_request(
    "API-23 Metrics", "GET", "{{base_url}}/api/dashboard/metrics",
    test_script="pm.test(\"Status code is 200\", function () { pm.response.to.have.status(200); });"
))

f5["item"].append(create_request(
    "API-24 Peak Hours", "GET", "{{base_url}}/api/dashboard/peak-hours",
    test_script="pm.test(\"Status code is 200\", function () { pm.response.to.have.status(200); });"
))

f5["item"].append(create_request(
    "API-25 Revenue Trends", "GET", "{{base_url}}/api/dashboard/revenue-trends",
    test_script="pm.test(\"Status code is 200\", function () { pm.response.to.have.status(200); });"
))

f5["item"].append(create_request(
    "API-26 Demographics", "GET", "{{base_url}}/api/dashboard/demographics",
    test_script="pm.test(\"Status code is 200\", function () { pm.response.to.have.status(200); });"
))

f5["item"].append(create_request(
    "API-27 Payment Insights", "GET", "{{base_url}}/api/dashboard/payment-insights",
    test_script="pm.test(\"Status code is 200\", function () { pm.response.to.have.status(200); });"
))

r28 = create_request(
    "API-28 List Alerts", "GET", "{{base_url}}/api/exit-alerts",
    test_script="pm.test(\"Status code is 200\", function () { pm.response.to.have.status(200); });\npm.test(\"Capture Alert ID\", function () { var d = pm.response.json(); pm.environment.set(\"alert_id\", d[0].id); pm.environment.set(\"alert_id_2\", d[1].id); });"
)
f5["item"].append(r28)

f5["item"].append(create_request(
    "API-29 Dismiss Alert", "PUT", "{{base_url}}/api/exit-alerts/{{alert_id}}/dismiss",
    test_script="pm.test(\"Status code is 200\", function () { pm.response.to.have.status(200); });"
))

f5["item"].append(create_request(
    "API-30 Override Alert", "PUT", "{{base_url}}/api/exit-alerts/{{alert_id_2}}/override",
    test_script="pm.test(\"Status code is 200\", function () { pm.response.to.have.status(200); });"
))

for req in f5["item"]:
    req["request"]["auth"] = {"type": "bearer", "bearer": [{"key": "token", "value": "{{token}}", "type": "string"}]}


# FOLDER 6 - ROI & AI Query
f6 = {"name": "Folder 6 - ROI and AI Query", "item": []}

r31 = create_request(
    "API-31 Set ROI", "POST", "{{base_url}}/api/roi/coordinates",
    body={"points": [{"x": 10, "y": 10}, {"x": 90, "y": 10}, {"x": 90, "y": 90}, {"x": 10, "y": 90}]},
    test_script="pm.test(\"Status code is 200\", function () { pm.response.to.have.status(200); });"
)
r31["request"]["auth"] = {"type": "bearer", "bearer": [{"key": "token", "value": "{{token}}", "type": "string"}]}
f6["item"].append(r31)

f6["item"].append(create_request(
    "API-32 AI Query Select", "POST", "{{base_url}}/api/ai/query",
    body={"sql": "SELECT COUNT(*) FROM parking_sessions"},
    test_script="pm.test(\"Status code is 200\", function () { pm.response.to.have.status(200); });\npm.test(\"Has data\", function () { var d = pm.response.json(); pm.expect(d).to.have.property(\"data\"); });"
))

f6["item"].append(create_request(
    "API-33 AI Query Drop Table", "POST", "{{base_url}}/api/ai/query",
    body={"sql": "DROP TABLE users"},
    test_script="pm.test(\"Status code is 403\", function () { pm.response.to.have.status(403); });\npm.test(\"Forbidden\", function () { var d = pm.response.json(); pm.expect(d.error).to.include(\"Only SELECT queries are allowed.\"); });"
))

f6["item"].append(create_request(
    "API-34 Webhook Congestion", "POST", "{{base_url}}/api/webhooks/congestion",
    body={"alert": True, "vehicles_in_roi": 5, "avg_dwell_time": 10},
    test_script="pm.test(\"Status is 200\", function () { pm.response.to.have.status(200); });"
))


# FOLDER 7 - Supporting Services
f7 = {"name": "Folder 7 - Supporting Services", "item": []}

f7["item"].append({
    "name": "API-38 Congestion Upload",
    "request": {
        "method": "POST",
        "url": {
            "raw": "{{congestion_url}}/upload",
            "host": ["{{congestion_url}}"],
            "path": ["upload"]
        },
        "body": {
            "mode": "formdata",
            "formdata": [
                {"key": "file", "type": "file", "src": "C:/Users/Tan Gyap Xun/Desktop/DEGREE/FYP/FYP DEVELOPMENT/tests/postman/dummy.mp4"}
            ]
        }
    },
    "event": [{"listen": "test", "script": {"type": "text/javascript", "exec": ["pm.test(\"Status code is 200\", function () { pm.response.to.have.status(200); });"]}}]
})

f7["item"].append(create_request(
    "API-39 Congestion Set ROI", "POST", "{{congestion_url}}/roi/coordinates",
    body={"points": [{"x": 10, "y": 10}, {"x": 90, "y": 10}, {"x": 90, "y": 90}, {"x": 10, "y": 90}]},
    test_script="pm.test(\"Status code is 200\", function () { pm.response.to.have.status(200); });"
))

f7["item"].append(create_request(
    "API-40 Congestion Status", "GET", "{{congestion_url}}/status",
    test_script="pm.test(\"Status code is 200\", function () { pm.response.to.have.status(200); });"
))

f7["item"].append(create_request(
    "API-41 Congestion Check", "GET", "{{congestion_url}}/congestion",
    test_script="pm.test(\"Status code is 200\", function () { pm.response.to.have.status(200); });"
))

f7["item"].append(create_request(
    "API-36 AI Health", "GET", "{{ai_url}}/health",
    test_script="pm.test(\"Status code is 200\", function () { pm.response.to.have.status(200); });"
))

# Note: API-35, 37, 42 excluded from the automated run as requested, to prevent hanging.

collection["item"] = [f1, f2, f3, f4, f5, f6, f7]

with open("tests/postman/smartpark.postman_collection.json", "w") as f:
    json.dump(collection, f, indent=4)
    
env = {
    "id": "e22709e1-6ab9-42b3-8208-ec47ccdf348e",
    "name": "SmartPark Local",
    "values": [
        {"key": "base_url", "value": "http://127.0.0.1:8000", "enabled": True},
        {"key": "next_url", "value": "http://localhost:3000", "enabled": True},
        {"key": "ai_url", "value": "http://localhost:8001", "enabled": True},
        {"key": "congestion_url", "value": "http://localhost:8002", "enabled": True},
        {"key": "token", "value": "", "enabled": True},
        {"key": "session_id", "value": "", "enabled": True},
        {"key": "session_21_id", "value": "", "enabled": True},
        {"key": "session_22_id", "value": "", "enabled": True},
        {"key": "alert_id", "value": "", "enabled": True},
        {"key": "alert_id_2", "value": "", "enabled": True}
    ]
}

with open("tests/postman/smartpark.postman_environment.json", "w") as f:
    json.dump(env, f, indent=4)
    
with open("tests/postman/dummy.mp4", "w") as f:
    f.write("dummy video content")
