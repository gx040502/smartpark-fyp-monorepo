"""
LPR_exit_CAR.py — SmartPark Exit Gate License Plate Recognition Pipeline
═══════════════════════════════════════════════════════════════════════════════════
A standalone script that combines:
  1. Car Detection & Tracking  — YOLOv11
  2. License Plate Detection   — YOLOv11 (Runs inside Car Crop)
  3. Image Enhancement         — Isolate, Deskew, Invert, CLAHE, Sharpen, Gamma
  4. Character Recognition     — YOLOv11 OCR
  5. Car Attribute Extraction  — OpenCV HSV (Color) + YOLO Classification (Brand) [SYNCHRONOUS]
  6. Exit Verification         — HTTP POST to Laravel backend (allow / deny)

Usage:
    python LPR_exit_CAR.py
    python LPR_exit_CAR.py --video path/to/video.mp4
    python LPR_exit_CAR.py --video path/to/video.mp4 --output output.mp4
    python LPR_exit_CAR.py --no-save-video
"""

import argparse
import math
import os
import cv2
import numpy as np
import requests
from dotenv import load_dotenv
from ultralytics import YOLO

# ==============================================================================================================
# 1. CONFIGURATION
# ==============================================================================================================

load_dotenv()

# Model Paths
CAR_MODEL_PATH = "yolov8n.pt"
PLATE_MODEL_PATH = r"G:\My Drive\FYP\LICENSE PLATE\outputs\License-Plate-Recognition-11\yolo11_run_02\weights\best.pt"
OCR_MODEL_PATH = r"G:\My Drive\FYP\OCR\outputs\CatEye-ALPR-v3-3\yolo8_run_01\weights\best.pt"
BRAND_MODEL_PATH = r"G:\My Drive\FYP\CAR_CLASSIFICATION\outputs\version4_split\yolo_cls_run_01\weights\best.pt"  # <-- Your new YOLO brand classifier

# Video I/O  (overridable via CLI args)
INPUT_VIDEO = r"E:\BACKUP\UTAR video\ONE CAR\VQM568 black tesla 4.5.mp4"
OUTPUT_VIDEO = "lpr_exit_output.mp4"
SAVE_VIDEO = True

# API Config
LARAVEL_API_URL = os.getenv("LARAVEL_API_URL", "http://127.0.0.1:8000")

# Application Settings
CAR_CONFIDENCE_THRESHOLD = 0.5
PLATE_CONFIDENCE_THRESHOLD = 0.7
OCR_CONFIDENCE_THRESHOLD = 0.7
SECONDS_TO_CONFIRM = 4.5  # Wait this many frames based on FPS before triggering processing


# ==============================================================================================================
# 2. MODEL LOADING
# ==============================================================================================================

def load_all_models():
    """
    Load and return all four models used in the pipeline:
      - YOLO car detector
      - YOLO plate detector
      - YOLO OCR character recogniser
      - YOLO brand classification model
    """
    print("--- LOADING YOLO MODELS ---")

    car_model = YOLO(CAR_MODEL_PATH)
    print("✅ Loaded YOLO Car Model.")

    plate_model = YOLO(PLATE_MODEL_PATH)
    print("✅ Loaded YOLO Plate Model.")

    ocr_model = YOLO(OCR_MODEL_PATH)
    print("✅ Loaded YOLO OCR Model.")

    brand_model = YOLO(BRAND_MODEL_PATH)
    print("✅ Loaded YOLO Brand Classification Model.")

    return car_model, plate_model, ocr_model, brand_model


# ==============================================================================================================
# 3. IMAGE PROCESSING PIPELINE (ISOLATE, DESKEW, ENHANCE)
# ==============================================================================================================

def isolate_and_get_corners(plate_crop):
    gray = cv2.cvtColor(plate_crop, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    h, w = binary.shape
    margin_y = int(h * 0.1)
    margin_x = int(w * 0.1)
    
    center_region = binary[margin_y:h-margin_y, margin_x:w-margin_x]
    
    if np.mean(center_region) < 127:
        binary = cv2.bitwise_not(binary)
        
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return plate_crop, None

    largest = max(contours, key=cv2.contourArea)
    x, y, w, h_box = cv2.boundingRect(largest)
    
    if w * h_box < 0.15 * plate_crop.shape[0] * plate_crop.shape[1]:
        return plate_crop, None

    cropped = plate_crop[y:y+h_box, x:x+w]
    rect = cv2.minAreaRect(largest)      
    box = cv2.boxPoints(rect)            

    box_shifted = box - [x, y]
    box_sorted = sorted(box_shifted, key=lambda p: p[0])
    left_pts, right_pts = box_sorted[:2], box_sorted[2:]
    left_x, left_y = np.mean(left_pts, axis=0)
    right_x, right_y = np.mean(right_pts, axis=0)

    return cropped, (left_x, left_y, right_x, right_y)

def deskew_by_corners(ROI, left_x, left_y, right_x, right_y):
    opp = right_y - left_y
    hyp = ((left_x - right_x)**2 + (left_y - right_y)**2)**0.5

    if hyp == 0:
        return ROI 

    sin = opp / hyp
    sin = max(-1.0, min(1.0, sin))
    theta = math.asin(sin) * 57.2958

    if abs(theta) < 0.5 or abs(theta) > 45:
        return ROI

    image_center = tuple(np.array(ROI.shape[1::-1]) / 2)
    rot_mat = cv2.getRotationMatrix2D(image_center, theta, 1.0)
    result = cv2.warpAffine(ROI, rot_mat, ROI.shape[1::-1],
                             flags=cv2.INTER_LINEAR,
                             borderMode=cv2.BORDER_CONSTANT,
                             borderValue=255)

    if opp > 0:
        h = result.shape[0] - int(opp) // 2
    else:
        h = result.shape[0] + int(opp) // 2

    h = max(1, min(h, result.shape[0])) 
    result = result[0:h, :]
    return result

def process_plate_pipeline(plate_crop):
    plate_crop, corners = isolate_and_get_corners(plate_crop)

    if corners is not None:
        plate_crop = deskew_by_corners(plate_crop, *corners)

    gray_for_check = cv2.cvtColor(plate_crop, cv2.COLOR_BGR2GRAY)
    _, binary_for_check = cv2.threshold(gray_for_check, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    if np.mean(binary_for_check) < 127:
        plate_crop = cv2.bitwise_not(plate_crop)

    height, width = plate_crop.shape[:2]
    plate_crop = cv2.resize(plate_crop, (int(width * 1.5), int(height * 1.5)), interpolation=cv2.INTER_CUBIC)

    lab = cv2.cvtColor(plate_crop, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    cl = clahe.apply(l_channel)
    merged_lab = cv2.merge((cl, a_channel, b_channel))
    plate_crop = cv2.cvtColor(merged_lab, cv2.COLOR_LAB2BGR)

    gaussian = cv2.GaussianBlur(plate_crop, (0, 0), sigmaX=3)
    plate_crop = cv2.addWeighted(plate_crop, 1.5, gaussian, -0.5, 0)

    gamma = 2.0 
    table = np.array([((i / 255.0) ** gamma) * 255 for i in np.arange(0, 256)]).astype("uint8")
    plate_crop = cv2.LUT(plate_crop, table)

    gray_clean = cv2.cvtColor(plate_crop, cv2.COLOR_BGR2GRAY)
    plate_crop = cv2.cvtColor(gray_clean, cv2.COLOR_GRAY2BGR)
    
    return plate_crop


# ==============================================================================================================
# 4. COLOR DETECTION ENGINE (HSV MATH)
# ==============================================================================================================

HUE_BANDS = {
    "Red":    [(0, 9), (160, 179)],
    "Yellow": [(10, 33)],
    "Green":  [(34, 85)],
    "Blue":   [(86, 135)],
    "Purple": [(136, 159)],
}

def build_glare_shadow_mask(roi_bgr, v_high=248, s_low=15, v_low=12, bright_percentile_cut=70):
    hsv = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)

    is_blown_highlight = (v >= v_high) & (s <= s_low)
    is_crushed_shadow = (v <= v_low)
    keep_mask = ~(is_blown_highlight | is_crushed_shadow)

    if keep_mask.sum() < 0.05 * keep_mask.size:
        keep_mask[:] = True 

    v_cutoff = np.percentile(v[keep_mask], bright_percentile_cut)
    keep_mask = keep_mask & (v.astype(np.float32) <= v_cutoff)

    if keep_mask.sum() < 0.05 * keep_mask.size:
        keep_mask[:] = True 

    return keep_mask

def classify_hue(median_h):
    for name, ranges in HUE_BANDS.items():
        for lo, hi in ranges:
            if lo <= median_h <= hi:
                return name
    return "Unknown"

def detect_car_color(car_crop, roi_box=None, sat_thresh=35, white_v_thresh=170, black_v_thresh=95):
    height, width = car_crop.shape[:2]

    if roi_box is None:
        start_y, end_y = int(height * 0.25), int(height * 0.42)
        start_x, end_x = int(width * 0.30), int(width * 0.70)
    else:
        start_x, start_y, end_x, end_y = roi_box

    roi = car_crop[start_y:end_y, start_x:end_x]
    if roi.size == 0:
        return "Unknown"

    keep_mask = build_glare_shadow_mask(roi)

    hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    h_ch, s_ch, v_ch = cv2.split(hsv_roi)
    
    median_h = np.median(h_ch[keep_mask])
    median_s = np.median(s_ch[keep_mask])
    median_v = np.median(v_ch[keep_mask])

    if median_v <= black_v_thresh:
        return "Black"
    elif median_s < sat_thresh:
        if median_v >= white_v_thresh:
            return "White"
        else:
            return "Gray"
    else:
        return classify_hue(median_h)


# ==============================================================================================================
# 5. SYNCHRONOUS ATTRIBUTE EXTRACTION & OCR
# ==============================================================================================================

def get_car_attributes(brand_model, car_crop_bgr):
    """
    Extracts Color via OpenCV HSV (using BGR crop) and Brand via YOLO (using Grayscale crop).
    """
    try:
        # 1. Get Color
        color = detect_car_color(car_crop_bgr)

        # 2. Get Brand (Convert to Grayscale -> 3-channel for YOLO)
        gray_crop = cv2.cvtColor(car_crop_bgr, cv2.COLOR_BGR2GRAY)
        gray_3ch_crop = cv2.cvtColor(gray_crop, cv2.COLOR_GRAY2BGR)
        
        results = brand_model(gray_3ch_crop, verbose=False)
        top1_idx = results[0].probs.top1
        brand = results[0].names[top1_idx]

        return {'color': color, 'model': brand}
    except Exception as e:
        print(f"\n❌ [ATTRIBUTE ERROR] Failed to extract details: {e}")
        return {'color': 'Unknown', 'model': 'Unknown'}

def extract_plate_text(ocr_model, plate_crop_bgr):
    """Runs OCR on the cropped plate and sorts characters from left to right."""
    results = ocr_model.predict(plate_crop_bgr, conf=OCR_CONFIDENCE_THRESHOLD, verbose=False)
    
    detected_chars = []
    for box in results[0].boxes:
        x1 = float(box.xyxy[0][0])
        cls_id = int(box.cls[0])
        char_name = ocr_model.names[cls_id]
        if len(char_name) == 2:
            char_name = char_name[1] 
        detected_chars.append((x1, char_name))
    
    detected_chars.sort(key=lambda item: item[0])
    return "".join([char for _, char in detected_chars])


# ==============================================================================================================
# 6. EXIT VERIFICATION (BACKEND)
# ==============================================================================================================

def verify_and_exit(plate_number, color, model, car_crop_bgr):
    """Send exit verification request to Laravel backend with image."""
    success, buffer = cv2.imencode('.jpg', car_crop_bgr)
    if not success:
        print(f"\n❌ [EXIT ERROR] Failed to encode image for {plate_number}")
        return None
    
    files = {
        'image': ('alert.jpg', buffer.tobytes(), 'image/jpeg')
    }
    data = {
        'license_plate': plate_number,
        'color': color,
        'model': model,
    }
    
    try:
        response = requests.post(
            f"{LARAVEL_API_URL}/api/parking-sessions/car-exit",
            data=data,
            files=files,
            timeout=10
        )
        resp_data = response.json()

        if response.status_code == 200:
            if resp_data.get('exit_type') == 'free':
                print(f"\n✅ [EXIT] Barrier Opened! {plate_number} exiting for free (within 15 min).")
            else:
                print(f"\n✅ [EXIT] Barrier Opened! {plate_number} verified and exiting.")
            return resp_data
            
        elif response.status_code == 403:
            message = resp_data.get('message', 'Exit denied.')
            print(f"\n🚫 [EXIT] Barrier CLOSED for {plate_number}: {message}")

            if resp_data.get('exit_type') == 'grace_expired':
                print(f"   Overdue: {resp_data['overdue_minutes']} minutes | Extra charge: RM {resp_data['extra_charge']}")
                print(f"   Driver must pay additional charge via the mobile app.")
            elif resp_data.get('alert_type'):
                print(f"   ⚠️ Vehicle mismatch ({resp_data['alert_type']}). Admin has been notified.")
            return resp_data
            
        elif response.status_code == 404:
            print(f"\n⚠️ [EXIT] No active session found for {plate_number}.")
            return resp_data
            
        else:
            print(f"\n⚠️ [EXIT] Unexpected response ({response.status_code}): {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"\n❌ [EXIT ERROR] Failed to verify {plate_number}: {e}")
        return None


# ==============================================================================================================
# 7. MAIN VIDEO PROCESSING LOOP
# ==============================================================================================================

def process_video(input_video, output_video, save_video):
    car_model, plate_model, ocr_model, brand_model = load_all_models()

    processed_track_ids = set()  
    track_history = {}           

    cap = cv2.VideoCapture(input_video)
    if not cap.isOpened():
        print(f"Error opening video: {input_video}")
        return

    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    if fps <= 0:
        fps = 30  

    min_frames_to_confirm = int(fps * SECONDS_TO_CONFIRM)
    print(f"FPS detected as {fps}. Waiting {min_frames_to_confirm} frames to confirm cars.")

    out = None
    if save_video:
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_video, fourcc, fps, (frame_width, frame_height))
        print(f"Saving video to: {output_video}")

    print("\n--- STARTING EXIT GATE LPR SYSTEM ---")
    print("Press 'q' to stop.")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # 🚀 TRACK CARS INSTEAD OF PLATES
        results = car_model.track(
            frame, 
            persist=True, 
            tracker="bytetrack.yaml",
            conf=CAR_CONFIDENCE_THRESHOLD, 
            classes=[2],  # <-- Uncomment this if you switch to default yolov8n.pt
            verbose=False
        )

        if results[0].boxes is not None and results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy().astype(int)
            track_ids = results[0].boxes.id.cpu().numpy().astype(int)

            for box, track_id in zip(boxes, track_ids):
                cx1, cy1, cx2, cy2 = box
                
                # Clamp car coordinates to frame boundaries
                cx1, cy1 = max(0, cx1), max(0, cy1)
                cx2, cy2 = min(frame_width, cx2), min(frame_height, cy2)

                # Draw Car Box (Blue)
                cv2.rectangle(frame, (cx1, cy1), (cx2, cy2), (255, 0, 0), 2)

                track_history[track_id] = track_history.get(track_id, 0) + 1
                frames_seen = track_history[track_id]

                if track_id in processed_track_ids:
                    cv2.putText(frame, "Processed", (cx1, cy1 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    continue

                if frames_seen < min_frames_to_confirm:
                    cv2.putText(frame, f"Tracking Car... {frames_seen}/{min_frames_to_confirm}",
                                (cx1, cy1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)
                    continue

                # ==========================================
                # CAR IS STABLE! FIND PLATE INSIDE CAR CROP
                # ==========================================
                car_crop_bgr = frame[cy1:cy2, cx1:cx2]
                if car_crop_bgr.size == 0:
                    continue
                
                # Run plate model ONLY on the isolated car crop
                plate_results = plate_model(car_crop_bgr, conf=PLATE_CONFIDENCE_THRESHOLD, verbose=False)
                
                if plate_results[0].boxes is None or len(plate_results[0].boxes) == 0:
                    continue  # Car is stable, but plate isn't visible yet.
                    
                # Get the highest confidence plate
                plate_box = plate_results[0].boxes.xyxy[0].cpu().numpy().astype(int)
                px1, py1, px2, py2 = plate_box
                
                # Clamp plate coordinates to car crop boundaries
                px1, py1 = max(0, px1), max(0, py1)
                px2, py2 = min(car_crop_bgr.shape[1], px2), min(car_crop_bgr.shape[0], py2)
                
                plate_crop = car_crop_bgr[py1:py2, px1:px2]
                if plate_crop.size == 0:
                    continue
                    
                # Draw Plate Box on the main frame (Green) by offsetting car coordinates
                cv2.rectangle(frame, (cx1 + px1, cy1 + py1), (cx1 + px2, cy1 + py2), (0, 255, 0), 2)

                try:
                    enhanced_plate = process_plate_pipeline(plate_crop)
                except Exception as e:
                    print(f"⚠️ [SYSTEM] Skipping plate on car ID {track_id} due to enhancement failure: {e}")
                    continue

                # OCR EXTRACTION
                plate_text = extract_plate_text(ocr_model, enhanced_plate)

                if not plate_text:
                    continue

                processed_track_ids.add(track_id)
                print(f"\n🚗 [EXIT GATE] Stable Car & Plate Detected: {plate_text} (Track ID: {track_id})")
                
                cv2.putText(frame, plate_text, (cx1, cy1 - 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

                # ==========================================
                # GET ATTRIBUTES (COLOR + BRAND) SYNCHRONOUSLY
                # ==========================================
                print(f"   [SYSTEM] Identifying attributes for {plate_text}...")
                attributes = get_car_attributes(brand_model, car_crop_bgr)

                print(f"   [SYSTEM] Detected: {attributes['color']} - {attributes['model']}")
                print(f"   [SYSTEM] Verifying with backend...")

                # ==========================================
                # VERIFY AND EXIT
                # ==========================================
                resp_data = verify_and_exit(plate_text, attributes['color'], attributes['model'], car_crop_bgr)

                if resp_data:
                    allowed = resp_data.get('allowed', False)
                    if allowed:
                        if resp_data.get('exit_type') == 'free':
                            cv2.putText(frame, f"{plate_text} - FREE EXIT OK", (cx1, cy1 - 10),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                        else:
                            cv2.putText(frame, f"{plate_text} - EXIT OK", (cx1, cy1 - 10),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                    else:
                        exit_type = resp_data.get('exit_type')
                        alert_type = resp_data.get('alert_type')
                        
                        if exit_type == 'unpaid':
                            cv2.putText(frame, f"{plate_text} - PLEASE PAY FIRST", (cx1, cy1 - 10),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                        elif exit_type == 'grace_expired':
                            cv2.putText(frame, f"{plate_text} - GRACE EXPIRED", (cx1, cy1 - 10),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                        elif alert_type in ['color_mismatch', 'model_mismatch']:
                            cv2.putText(frame, f"{plate_text} - VEHICLE MISMATCH", (cx1, cy1 - 10),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                        elif alert_type == 'plate_not_found':
                            cv2.putText(frame, f"{plate_text} - PLATE NOT FOUND", (cx1, cy1 - 10),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                        else:
                            cv2.putText(frame, f"{plate_text} - EXIT DENIED", (cx1, cy1 - 10),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

        if out:
            out.write(frame)
        cv2.imshow("SmartPark LPR - Exit Gate", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Cleanup
    cap.release()
    if out:
        out.release()
    cv2.destroyAllWindows()
    print("Exit Gate Processing Complete.")


# ==============================================================================================================
# 8. ENTRY POINT
# ==============================================================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="SmartPark Exit Gate LPR — Pure YOLO Pipeline + OpenCV Color Engine"
    )
    parser.add_argument("--video", type=str, default=INPUT_VIDEO,
                        help="Path to the input video file.")
    parser.add_argument("--output", type=str, default=OUTPUT_VIDEO,
                        help="Path for the output annotated video.")
    parser.add_argument("--no-save-video", action="store_true",
                        help="Disable saving the output video.")
    args = parser.parse_args()

    process_video(
        input_video=args.video,
        output_video=args.output,
        save_video=not args.no_save_video,
    )