import cv2
import math
import numpy as np
from ultralytics import YOLO
import concurrent.futures
import os
import requests
from dotenv import load_dotenv

load_dotenv()

# ==============================================================================================================
# 1. CONFIGURATION
# ==============================================================================================================
# Model Paths (relative to project root)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAR_MODEL_PATH = "yolov8n.pt"
PLATE_MODEL_PATH = os.path.join(_PROJECT_ROOT, "plate.pt")
OCR_MODEL_PATH = os.path.join(_PROJECT_ROOT, "OCR.pt")
BRAND_MODEL_PATH = os.path.join(_PROJECT_ROOT, "car make.pt")

INPUT_VIDEO = r"C:\Users\Tan Gyap Xun\Desktop\DEGREE\FYP\FYP PROJECT 2\PRESENTATION\VNT2602 black proton 3.mp4"
OUTPUT_VIDEO = "lpr_entrance_output.mp4"
SAVE_VIDEO = True

LARAVEL_API_URL = os.getenv("LARAVEL_API_URL", "http://127.0.0.1:8000")

# Application Settings
CAR_CONFIDENCE_THRESHOLD = 0.5
PLATE_CONFIDENCE_THRESHOLD = 0.7
OCR_CONFIDENCE_THRESHOLD = 0.7
SECONDS_TO_CONFIRM = 3

# ==============================================================================================================
# 2. IMAGE PROCESSING PIPELINE (ISOLATE, DESKEW, ENHANCE)
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
# 3. COLOR DETECTION ENGINE (SILENT BACKGROUND MODE)
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
# 4. YOLO BRAND DETECTION & DATABASE SAVING
# ==============================================================================================================
def save_car_details(plate_number, color, model, car_crop_bgr):
    payload = {
        'license_plate': plate_number,
        'color': color,
        'model': model,
    }
    
    files = None
    if car_crop_bgr is not None:
        # Encode the image to JPEG format in memory
        _, img_encoded = cv2.imencode('.jpg', car_crop_bgr)
        files = {
            'image': ('car.jpg', img_encoded.tobytes(), 'image/jpeg')
        }
        
    try:
        response = requests.post(
            f"{LARAVEL_API_URL}/api/parking-sessions/car-entry",
            data=payload,
            files=files,
            timeout=5
        )
        if response.status_code == 201:
            print(f"\n✅ [DATABASE] Parking session created! "
                  f"Plate: {plate_number} | Color: {color} | Brand: {model}")
        else:
            print(f"\n⚠️ [DATABASE] Unexpected response ({response.status_code}): {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"\n❌ [DATABASE ERROR] Failed to save {plate_number}: {e}")

def extract_car_attributes(brand_model, car_crop_bgr, plate_number):
    """Background worker: Color uses full BGR crop; Brand classification uses Grayscale crop."""
    try:
        # 1. Color Detection (Uses original BGR color crop)
        detected_color = detect_car_color(car_crop_bgr)
        
        # 2. Brand Detection (Converts crop to Grayscale for YOLO classification)
        gray_crop = cv2.cvtColor(car_crop_bgr, cv2.COLOR_BGR2GRAY)
        gray_3ch_crop = cv2.cvtColor(gray_crop, cv2.COLOR_GRAY2BGR)  # Convert back to 3-channel gray for YOLO input tensor
        
        results = brand_model(gray_3ch_crop, verbose=False)
        top1_idx = results[0].probs.top1
        detected_brand = results[0].names[top1_idx]
        
        # 3. Fire to Database
        save_car_details(plate_number, detected_color, detected_brand, car_crop_bgr)
        
    except Exception as e:
        print(f"\n❌ [ATTRIBUTE ERROR] Failed to extract details for {plate_number}: {e}")


# ==============================================================================================================
# 5. OCR EXTRACTION
# ==============================================================================================================
def extract_plate_text(ocr_model, plate_crop_bgr):
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
# 6. MAIN VIDEO LOOP
# ==============================================================================================================
def load_all_models():
    print("--- LOADING YOLO MODELS ---")
    car_model = YOLO(CAR_MODEL_PATH)
    plate_model = YOLO(PLATE_MODEL_PATH)
    ocr_model = YOLO(OCR_MODEL_PATH)
    brand_model = YOLO(BRAND_MODEL_PATH)
    
    return car_model, plate_model, ocr_model, brand_model

def process_video():
    car_model, plate_model, ocr_model, brand_model = load_all_models()
    
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
    
    processed_track_ids = set() 
    track_history = {} 

    cap = cv2.VideoCapture(INPUT_VIDEO)
    if not cap.isOpened():
        print(f"Error opening video: {INPUT_VIDEO}")
        return

    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    if fps <= 0: fps = 30 
    
    min_frames_to_confirm = int(fps * SECONDS_TO_CONFIRM)
    print(f"FPS detected as {fps}. Waiting {min_frames_to_confirm} frames to confirm cars.")
    
    out = None
    if SAVE_VIDEO:
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(OUTPUT_VIDEO, fourcc, fps, (frame_width, frame_height))
        print(f"Saving video to: {OUTPUT_VIDEO}")

    print("\n--- STARTING LIVE LPR SYSTEM ---")
    print("Press 'q' to stop.")

    while cap.isOpened(): 
        ret, frame = cap.read() 
        if not ret: break 

        # TRACK CARS
        results = car_model.track(frame, persist=True, tracker="bytetrack.yaml", conf=CAR_CONFIDENCE_THRESHOLD, verbose=False, classes=[2])
        
        if results[0].boxes is not None and results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy().astype(int)
            track_ids = results[0].boxes.id.cpu().numpy().astype(int)

            for box, track_id in zip(boxes, track_ids):
                cx1, cy1, cx2, cy2 = box
                
                cx1, cy1 = max(0, cx1), max(0, cy1)
                cx2, cy2 = min(frame_width, cx2), min(frame_height, cy2)
                
                cv2.rectangle(frame, (cx1, cy1), (cx2, cy2), (255, 0, 0), 2)
                
                track_history[track_id] = track_history.get(track_id, 0) + 1 
                frames_seen = track_history[track_id]
                
                if track_id in processed_track_ids:
                    cv2.putText(frame, "Processed", (cx1, cy1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    continue
                
                if frames_seen < min_frames_to_confirm:
                    cv2.putText(frame, f"Tracking Car... {frames_seen}/{min_frames_to_confirm}", (cx1, cy1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)
                    continue
                
                # ==========================================
                # CAR IS STABLE! FIND PLATE INSIDE CAR CROP
                # ==========================================
                car_crop_bgr = frame[cy1:cy2, cx1:cx2]
                if car_crop_bgr.size == 0: continue
                
                plate_results = plate_model(car_crop_bgr, conf=PLATE_CONFIDENCE_THRESHOLD, verbose=False)
                
                if plate_results[0].boxes is None or len(plate_results[0].boxes) == 0:
                    continue 
                
                plate_box = plate_results[0].boxes.xyxy[0].cpu().numpy().astype(int)
                px1, py1, px2, py2 = plate_box
                
                px1, py1 = max(0, px1), max(0, py1)
                px2, py2 = min(car_crop_bgr.shape[1], px2), min(car_crop_bgr.shape[0], py2)
                
                plate_crop = car_crop_bgr[py1:py2, px1:px2]
                if plate_crop.size == 0: continue
                
                cv2.rectangle(frame, (cx1 + px1, cy1 + py1), (cx1 + px2, cy1 + py2), (0, 255, 0), 2)

                try:
                    enhanced_plate = process_plate_pipeline(plate_crop)
                except Exception as e:
                    print(f"⚠️ [SYSTEM] Skipping plate on car ID {track_id} due to enhancement failure: {e}")
                    continue
                
                plate_text = extract_plate_text(ocr_model, enhanced_plate)
                if not plate_text: continue
                
                processed_track_ids.add(track_id)
                
                print(f"\n🚗 [SYSTEM] Stable Car & Plate Detected: {plate_text} (Track ID: {track_id})")
                print(f"   [SYSTEM] Barrier Opened! Letting car enter immediately...")

                cv2.putText(frame, plate_text, (cx1, cy1 - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

                # Send a copy of the car crop to the background thread
                safe_car_crop = car_crop_bgr.copy()
                executor.submit(extract_car_attributes, brand_model, safe_car_crop, plate_text)

        if out: out.write(frame)
        cv2.imshow("SmartPark LPR", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Cleanup
    cap.release()
    if out: out.release()
    cv2.destroyAllWindows()
    
    print("\nWaiting for remaining background attribute tasks to finish...")
    executor.shutdown(wait=True) 
    print("Processing Complete.")

if __name__ == "__main__":
    process_video()