"""
Traffic Impact Assessment System - Backend
==========================================
FastAPI server that receives ROI coordinates from the Next.js frontend,
processes video frames with YOLO + ByteTrack, and detects traffic congestion
based on vehicle density and dwell time inside the ROI polygon.

Architecture:
  [Next.js Frontend] --POST /roi/coordinates--> [This FastAPI Server] --> [cv2.imshow for demo]

Run with:
  cd traffic-congestion
  uvicorn main:app --host 0.0.0.0 --port 8002 --reload
"""

import cv2
import numpy as np
import time
import threading
import os
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from ultralytics import YOLO
import requests as http_requests

# ==============================================================================================================
# 1. CONFIGURATION
# ==============================================================================================================

# YOLO model for vehicle detection
YOLO_MODEL_PATH = r"G:\My Drive\FYP\CAR MODEL\outputs\car-1\yolo11_run_01\weights\best.pt"

# Directory to save uploaded videos
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Detection settings
CONFIDENCE_THRESHOLD = 0.2
IOU_THRESHOLD = 0.2  # Intersection Over Union threshold for NMS (overlap filtering)

# Congestion thresholds
MIN_VEHICLES_FOR_CONGESTION = 3     # Must have more than 3 vehicles in ROI
MIN_AVG_DWELL_TIME_SECONDS = 4    # Average dwell must exceed 10 seconds

# Laravel webhook for congestion grace extension
LARAVEL_WEBHOOK_URL = "http://127.0.0.1:8000/api/webhooks/congestion"
CONGESTION_COOLDOWN_SECONDS = 900  # 15 minutes between webhook calls

# Stability: How many seconds an object must appear before we consider it "confirmed"
SECONDS_TO_CONFIRM = 1.0

# ==============================================================================================================
# 2. FASTAPI APP & MODELS
# ==============================================================================================================

app = FastAPI(title="Traffic Congestion API")

# Allow requests from the Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Point(BaseModel):
    x: float  # Percentage (0 to 100)
    y: float  # Percentage (0 to 100)

class ROIPayload(BaseModel):
    points: List[Point]  # Exactly 4 points

# Global state
roi_polygon_px: np.ndarray | None = None
input_video_path: str | None = None   # Set dynamically when user uploads a video
video_thread: threading.Thread | None = None
stop_event = threading.Event()
global_is_congested: bool = False
last_congestion_webhook_time: float = 0  # Timestamp of last webhook call (for cooldown)

# ==============================================================================================================
# 3. API ENDPOINTS
# ==============================================================================================================

@app.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    """
    Receives the video file from the frontend and saves it locally.
    Must be called BEFORE /roi/coordinates.
    """
    global input_video_path

    # Save the uploaded file to the uploads directory
    save_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(save_path, "wb") as f:
        content = await file.read()
        f.write(content)

    input_video_path = save_path
    print(f"\n📁 [UPLOAD] Video saved to: {save_path} ({len(content) / 1024 / 1024:.1f} MB)")

    return {
        "status": "success",
        "message": f"Video '{file.filename}' uploaded successfully.",
        "path": save_path,
    }

@app.post("/roi/coordinates")
async def receive_roi(payload: ROIPayload):
    """
    Receives 4 ROI points as percentages (0-100) from the Next.js frontend.

    The frontend draws the ROI on an SVG overlay that uses percentage-based coordinates.
    We convert these percentages to absolute pixel coordinates based on the video resolution.

    Example payload from frontend:
    {
      "points": [
        {"x": 20.5, "y": 30.2},
        {"x": 80.1, "y": 30.2},
        {"x": 80.1, "y": 85.0},
        {"x": 20.5, "y": 85.0}
      ]
    }

    Conversion formula:
      pixel_x = (percentage_x / 100) * video_width
      pixel_y = (percentage_y / 100) * video_height

    For a 1920x1080 video, point (20.5, 30.2) becomes:
      pixel_x = (20.5 / 100) * 1920 = 393.6 -> 394
      pixel_y = (30.2 / 100) * 1080 = 326.16 -> 326
    """
    global roi_polygon_px, video_thread

    if input_video_path is None:
        return {"status": "error", "message": "No video uploaded yet. POST to /upload first."}

    if len(payload.points) != 4:
        return {"status": "error", "message": "Exactly 4 points are required."}

    # Open the video briefly just to read its resolution
    cap = cv2.VideoCapture(input_video_path)
    if not cap.isOpened():
        return {"status": "error", "message": f"Cannot open video: {input_video_path}"}

    video_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    video_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()

    # Convert percentage coordinates to absolute pixel coordinates
    # Each point: pixel_x = (x% / 100) * width, pixel_y = (y% / 100) * height
    pixel_points = []
    for p in payload.points:
        px = int((p.x / 100.0) * video_width)
        py = int((p.y / 100.0) * video_height)
        pixel_points.append([px, py])

    # Store as a NumPy array (required by cv2.fillPoly and cv2.pointPolygonTest)
    # Shape: (4, 1, 2) for OpenCV polygon functions
    roi_polygon_px = np.array(pixel_points, dtype=np.int32)

    print(f"\n✅ [ROI] Received ROI from frontend!")
    print(f"   Video Resolution: {video_width}x{video_height}")
    print(f"   Percentage Points: {[(p.x, p.y) for p in payload.points]}")
    print(f"   Pixel Points: {pixel_points}\n")

    # Start the video processing in a background thread (so FastAPI stays responsive)
    if video_thread is None or not video_thread.is_alive():
        stop_event.clear()
        video_thread = threading.Thread(target=process_video, daemon=True)
        video_thread.start()

    return {
        "status": "success",
        "message": "ROI received and video processing started.",
        "video_resolution": {"width": video_width, "height": video_height},
        "pixel_coordinates": pixel_points,
    }

@app.get("/status")
async def get_status():
    """Health check endpoint."""
    return {
        "roi_configured": roi_polygon_px is not None,
        "video_uploaded": input_video_path is not None,
        "video_processing": video_thread is not None and video_thread.is_alive(),
    }

@app.get("/congestion")
async def get_congestion():
    """Returns the real-time congestion status."""
    return {"is_congested": global_is_congested}


# ==============================================================================================================
# 4. VIDEO PROCESSING LOOP
# ==============================================================================================================

def process_video():
    """
    Main video processing loop. Runs in a background thread.

    Pipeline per frame:
      1. Read frame from video
      2. Run YOLO detection (vehicles only)
      3. Pass detections to ByteTrack for persistent ID assignment
      4. For each tracked vehicle, calculate centroid
      5. Check if centroid is inside the ROI polygon (cv2.pointPolygonTest)
      6. Track entry time for vehicles inside ROI (dwell time dictionary)
      7. Calculate density and average dwell time
      8. Flag congestion if both thresholds are exceeded
      9. Draw visual overlays and display
    """
    global roi_polygon_px, input_video_path, global_is_congested, last_congestion_webhook_time

    print("--- LOADING YOLO MODEL ---")
    model = YOLO(YOLO_MODEL_PATH)

    cap = cv2.VideoCapture(input_video_path)
    if not cap.isOpened():
        print(f"Error: Cannot open video {INPUT_VIDEO}")
        return

    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    if fps <= 0: fps = 30

    print(f"Video: {frame_width}x{frame_height} @ {fps} FPS")

    # Calculate how many frames equals SECONDS_TO_CONFIRM
    min_frames_to_confirm = int(fps * SECONDS_TO_CONFIRM)
    print(f"Stability: Objects must appear for {min_frames_to_confirm} frames ({SECONDS_TO_CONFIRM}s) to be confirmed.")
    print(f"Congestion triggers when: >{MIN_VEHICLES_FOR_CONGESTION} vehicles AND >{MIN_AVG_DWELL_TIME_SECONDS}s avg dwell")
    print("\n--- STARTING TRAFFIC MONITORING ---")
    print("Press 'q' on the video window to stop.\n")

    # ============================================================
    # DWELL TIME TRACKING DICTIONARY
    # ============================================================
    # Key: track_id (int)
    # Value: entry_timestamp (float, from time.time())
    #
    # When a vehicle's centroid enters the ROI for the first time,
    # we record the current timestamp. As long as the vehicle stays
    # inside, we calculate dwell_time = current_time - entry_time.
    # When the vehicle leaves the ROI (centroid outside), we remove it.
    vehicle_entry_times: dict[int, float] = {}

    # Frame counter: tracks how many frames each object has been visible
    track_frame_count: dict[int, int] = {}

    # Total unique vehicles that have ever entered the ROI
    total_vehicles_counted = 0
    counted_ids: set[int] = set()

    while cap.isOpened() and not stop_event.is_set():
        ret, frame = cap.read()
        if not ret:
            # Loop video for continuous demo
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue

        # If ROI hasn't been set yet, just show the raw frame
        if roi_polygon_px is None:
            cv2.putText(frame, "Waiting for ROI from frontend...", (30, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 165, 255), 2)
            cv2.imshow("Traffic Congestion Monitor", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            continue

        # ============================================================
        # STEP 1: Run YOLO + ByteTrack on the frame
        # ============================================================
        # model.track() integrates ByteTrack automatically.
        # persist=True tells ByteTrack to remember IDs across frames.
        results = model.track(
            frame,
            persist=True,
            tracker="bytetrack.yaml",
            conf=CONFIDENCE_THRESHOLD,
            iou=IOU_THRESHOLD,
            verbose=False,
        )

        # Current time for dwell calculations
        current_time = time.time()

        # Set of track IDs visible in THIS frame (to detect vehicles that left)
        current_frame_ids: set[int] = set()

        # Congestion calculation variables
        vehicles_in_roi = 0
        total_dwell_in_roi = 0.0

        # ============================================================
        # STEP 2: Process each tracked detection
        # ============================================================
        if results[0].boxes is not None and results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy().astype(int)
            track_ids = results[0].boxes.id.cpu().numpy().astype(int)
            confs = results[0].boxes.conf.cpu().numpy()

            for box, track_id, conf in zip(boxes, track_ids, confs):
                x1, y1, x2, y2 = box

                # ============================================================
                # STEP 3: Calculate centroid of the bounding box
                # ============================================================
                # The centroid is the geometric center of the bounding box.
                # We use this single point (instead of the whole box) to test
                # whether the vehicle is "inside" the ROI polygon.
                cx = int((x1 + x2) / 2)
                cy = int((y1 + y2) / 2)

                # ============================================================
                # STEP 4: Check if centroid is inside the ROI polygon
                # ============================================================
                # cv2.pointPolygonTest returns:
                #   > 0  if the point is INSIDE the polygon
                #   = 0  if the point is ON the edge
                #   < 0  if the point is OUTSIDE the polygon
                #
                # The ROI polygon must be reshaped to (N, 1, 2) for OpenCV.
                roi_contour = roi_polygon_px.reshape((-1, 1, 2))
                inside = cv2.pointPolygonTest(roi_contour, (cx, cy), False) >= 0

                current_frame_ids.add(track_id)

                # Update frame counter for this tracked object
                track_frame_count[track_id] = track_frame_count.get(track_id, 0) + 1
                frames_seen = track_frame_count[track_id]

                if inside:
                    # Count unique vehicles
                    if track_id not in counted_ids:
                        counted_ids.add(track_id)
                        total_vehicles_counted += 1

                    # Record entry time if this is the first time we see this vehicle inside
                    if track_id not in vehicle_entry_times:
                        vehicle_entry_times[track_id] = current_time

                    # Calculate individual dwell time
                    dwell_time = current_time - vehicle_entry_times[track_id]
                    vehicles_in_roi += 1
                    total_dwell_in_roi += dwell_time

                    # Format dwell time as "Xm Ys" or just "Xs"
                    dwell_minutes = int(dwell_time) // 60
                    dwell_seconds = int(dwell_time) % 60
                    if dwell_minutes > 0:
                        dwell_str = f"{dwell_minutes}m {dwell_seconds}s"
                    else:
                        dwell_str = f"{dwell_seconds}s"

                    # --- DRAW: Vehicle inside ROI (YELLOW box + BLUE dwell text) ---
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), 2)
                    cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)  # Red centroid dot
                    # Blue floating text showing dwell time
                    cv2.putText(frame, f"ID:{track_id} | Dwell: {dwell_str}",
                                (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 165, 0), 2)
                else:
                    # Vehicle is outside ROI - remove from dwell tracking if it was inside before
                    if track_id in vehicle_entry_times:
                        del vehicle_entry_times[track_id]

                    # --- DRAW: Vehicle outside ROI (GREEN box + ORANGE frame counter) ---
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 1)
                    # Orange floating text showing tracking progress (capped at min_frames_to_confirm)
                    display_frames = min(frames_seen, min_frames_to_confirm)
                    cv2.putText(frame, f"ID:{track_id} | Tracking... {display_frames}/{min_frames_to_confirm}",
                                (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 2)

        # Clean up vehicles that have completely disappeared from the frame
        disappeared_ids = set(vehicle_entry_times.keys()) - current_frame_ids
        for gone_id in disappeared_ids:
            del vehicle_entry_times[gone_id]

        # ============================================================
        # STEP 5: Calculate congestion metrics
        # ============================================================
        avg_dwell_time = (total_dwell_in_roi / vehicles_in_roi) if vehicles_in_roi > 0 else 0.0

        # Congestion is TRUE only if BOTH conditions are met:
        #   1. More than MIN_VEHICLES_FOR_CONGESTION vehicles currently inside ROI
        #   2. Their average dwell time exceeds MIN_AVG_DWELL_TIME_SECONDS
        is_congested = (
            vehicles_in_roi >= MIN_VEHICLES_FOR_CONGESTION
            and avg_dwell_time >= MIN_AVG_DWELL_TIME_SECONDS
        )
        global_is_congested = is_congested

        # ============================================================
        # STEP 5b: Fire webhook to Laravel when congestion is detected
        # ============================================================
        # Only fires once every CONGESTION_COOLDOWN_SECONDS (15 min)
        if is_congested:
            if current_time - last_congestion_webhook_time >= CONGESTION_COOLDOWN_SECONDS:
                last_congestion_webhook_time = current_time
                # Fire-and-forget in a daemon thread so video loop isn't blocked
                def _send_webhook():
                    try:
                        resp = http_requests.post(LARAVEL_WEBHOOK_URL, json={
                            "alert": "Traffic Congestion",
                            "vehicles_in_roi": vehicles_in_roi,
                            "avg_dwell_time": round(avg_dwell_time, 1),
                            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        }, timeout=5)
                        print(f"🚨 [WEBHOOK] Congestion alert sent → Laravel responded {resp.status_code}")
                    except Exception as e:
                        print(f"⚠️ [WEBHOOK] Failed to send congestion alert: {e}")
                threading.Thread(target=_send_webhook, daemon=True).start()

        # ============================================================
        # STEP 6: Draw the ROI polygon
        # ============================================================
        # Green = Normal, Red = Congestion detected
        roi_color = (0, 0, 255) if is_congested else (0, 255, 0)

        # Draw filled polygon with transparency
        overlay = frame.copy()
        cv2.fillPoly(overlay, [roi_polygon_px], roi_color)
        frame = cv2.addWeighted(overlay, 0.15, frame, 0.85, 0)

        # Draw polygon border
        cv2.polylines(frame, [roi_polygon_px], isClosed=True, color=roi_color, thickness=3)

        # ============================================================
        # STEP 6b: Draw Average Dwell Time at the top-right corner of the ROI
        # ============================================================
        # Find the top-right corner of the ROI polygon (the point with the largest x among the top points)
        roi_top_right_x = int(np.max(roi_polygon_px[:, 0]))
        roi_top_right_y = int(np.min(roi_polygon_px[:, 1]))

        # Format average dwell time
        avg_minutes = int(avg_dwell_time) // 60
        avg_seconds = int(avg_dwell_time) % 60
        if avg_minutes > 0:
            avg_str = f"Avg: {avg_minutes}m {avg_seconds}s"
        else:
            avg_str = f"Avg: {avg_seconds}s"

        # Draw background pill for the label
        (tw, th), _ = cv2.getTextSize(avg_str, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        label_x = roi_top_right_x - tw - 10
        label_y = roi_top_right_y - 10
        cv2.rectangle(frame, (label_x - 3, label_y - th - 3), (label_x + tw + 3, label_y + 3), (0, 0, 0), -1)
        cv2.rectangle(frame, (label_x - 3, label_y - th - 3), (label_x + tw + 3, label_y + 3), roi_color, 1)
        cv2.putText(frame, avg_str, (label_x, label_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        # ============================================================
        # STEP 7: Draw the HUD Dashboard (top-left corner)
        # ============================================================
        dashboard_lines = [
            f"Total Vehicles Counted: {total_vehicles_counted}",
            f"Current ROI Density:    {vehicles_in_roi}",
            f"Avg Dwell Time:         {avg_dwell_time:.1f}s",
            f"Congestion:             {'YES - ALERT!' if is_congested else 'No'}",
        ]

        # Draw dark background for dashboard
        dash_h = 30 + len(dashboard_lines) * 40
        cv2.rectangle(frame, (10, 10), (250, dash_h), (0, 0, 0), -1)
        cv2.rectangle(frame, (10, 10), (250, dash_h), roi_color, 2)

        for i, line in enumerate(dashboard_lines):
            color = (0, 0, 255) if "YES" in line else (255, 255, 255)
            cv2.putText(frame, line, (20, 40 + i * 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 2)

        # If congested, draw a big flashing warning
        if is_congested:
            cv2.putText(frame, "!!! TRAFFIC CONGESTION !!!",
                        (frame_width // 2 - 280, frame_height - 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)

        # ============================================================
        # STEP 8: Display the frame
        # ============================================================
        cv2.imshow("Traffic Congestion Monitor", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Cleanup
    cap.release()
    cv2.destroyAllWindows()
    print("Video processing stopped.")
