"""
LPR_exit_CAR.py — SmartPark Exit Gate License Plate Recognition Pipeline
═══════════════════════════════════════════════════════════════════════════════════
A standalone script that combines:
  1. Car Detection & Tracking  — YOLOv11
  2. License Plate Detection   — YOLOv11 (Runs inside Car Crop)
  3. Image Enhancement         — Isolate, Deskew, Invert, CLAHE, Sharpen, Gamma
  4. Character Recognition     — YOLOv11 OCR
  5. Car Attribute Extraction  — Qwen3-VL (color & brand) [SYNCHRONOUS]
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
import torch
from dotenv import load_dotenv
from PIL import Image
from ultrultralytics import YOLO

try:
    from transformers import Qwen3VLForConditionalGeneration
except ImportError:
    from transformers import AutoModelForCausalLM as Qwen3VLForConditionalGeneration
from transformers import AutoProcessor
from huggingface_hub import login


# ==============================================================================================================
# 1. CONFIGURATION
# ==============================================================================================================

load_dotenv()

# Model Paths
CAR_MODEL_PATH = r"G:\My Drive\FYP\CAR MODEL\outputs\car_mixed\yolo11_run_01\weights\best.pt"
PLATE_MODEL_PATH = r"G:\My Drive\FYP\LICENSE PLATE\outputs\License-Plate-Recognition-11\yolo11_run_02\weights\best.pt"
OCR_MODEL_PATH = r"G:\My Drive\FYP\OCR\outputs\CatEye-ALPR-v3-3\yolo11_run_01\weights\best.pt"

# Video I/O  (overridable via CLI args)
INPUT_VIDEO = r"C:\Users\Tan Gyap Xun\Desktop\DEGREE\UTAR video\UTAR 3 CAR\UTAR 3 CAR-1.mp4"
OUTPUT_VIDEO = "lpr_exit_output.mp4"
SAVE_VIDEO = True

# API & Model Config
HF_TOKEN = os.getenv("HF_TOKEN")
LARAVEL_API_URL = os.getenv("LARAVEL_API_URL", "http://127.0.0.1:8000")
QWEN_MODEL_ID = "Qwen/Qwen3-VL-2B-Instruct"

# Application Settings
CAR_CONFIDENCE_THRESHOLD = 0.5
PLATE_CONFIDENCE_THRESHOLD = 0.3
OCR_CONFIDENCE_THRESHOLD = 0.7
SECONDS_TO_CONFIRM = 1  # Wait this many seconds before triggering Qwen


# ==============================================================================================================
# 2. MODEL LOADING
# ==============================================================================================================

def load_all_models():
    """
    Load and return all four models used in the pipeline:
      - YOLO car detector
      - YOLO plate detector
      - YOLO OCR character recogniser
      - Qwen3-VL vision-language model (for car color & brand)
    """
    print("--- LOADING MODELS (This may take a minute) ---")

    car_model = YOLO(CAR_MODEL_PATH)
    print("✅ Loaded YOLO Car Model.")

    plate_model = YOLO(PLATE_MODEL_PATH)
    print("✅ Loaded YOLO Plate Model.")

    ocr_model = YOLO(OCR_MODEL_PATH)
    print("✅ Loaded YOLO OCR Model.")

    if HF_TOKEN:
        login(token=HF_TOKEN)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Loading Qwen ({QWEN_MODEL_ID}) on {device}...")

    if device == "cuda":
        qwen_model = Qwen3VLForConditionalGeneration.from_pretrained(
            QWEN_MODEL_ID,
            torch_dtype=torch.bfloat16,
            trust_remote_code=True
        ).to(device)
    else:
        qwen_model = Qwen3VLForConditionalGeneration.from_pretrained(
            QWEN_MODEL_ID,
            torch_dtype=torch.float32,
            trust_remote_code=True
        )

    processor = AutoProcessor.from_pretrained(QWEN_MODEL_ID, trust_remote_code=True)
    print("✅ Loaded Qwen Model.")

    return car_model, plate_model, ocr_model, qwen_model, processor, device


# ==============================================================================================================
# 3. IMAGE PROCESSING PIPELINE (ISOLATE, DESKEW, ENHANCE)
# ==============================================================================================================

def isolate_and_get_corners(plate_crop):
    """
    Finds the plate's outline silently, returns a tight crop (color) containing just
    the plate, AND the left/right corner points of its true rectangle.
    """
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
    """Rotates ROI level using two known edge points via simple trigonometry."""
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
    """Runs the cropped plate through isolation, deskew, and color enhancement."""
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
# 4. YOLO OCR EXTRACTION
# ==============================================================================================================

def extract_plate_text(ocr_model, plate_crop_bgr):
    """Runs OCR on the cropped plate and sorts characters from left to right."""
    results = ocr_model.predict(plate_crop_bgr, conf=OCR_CONFIDENCE_THRESHOLD, verbose=False)
    
    detected_chars = []
    for box in results[0].boxes:
        x1 = float(box.xyxy[0][0])
        cls_id = int(box.cls[0])
        char_name = ocr_model.names[cls_id]
        detected_chars.append((x1, char_name))
    
    detected_chars.sort(key=lambda item: item[0])
    return "".join([char for _, char in detected_chars])


# ==============================================================================================================
# 5. QWEN ATTRIBUTE DETECTION (SYNCHRONOUS)
# ==============================================================================================================

def parse_car_attributes(text):
    """
    Parse Qwen's response in '[Color] - [Brand]' format.
    Returns a dict: {'color': '...', 'model': '...'}
    """
    cleaned = text.strip().replace("\n", " ")

    if ' - ' in cleaned:
        parts = cleaned.split(' - ', 1)
        color = parts[0].strip()
        model = parts[1].strip()
    else:
        color = "Unknown"
        model = cleaned if cleaned else "Unknown"

    return {'color': color, 'model': model}


def get_qwen_attributes(qwen_model, processor, device, pil_image):
    """
    Runs Qwen SYNCHRONOUSLY and returns the parsed attributes.
    Unlike the entry gate which fires-and-forgets, exit verification
    MUST wait for the result before calling the backend.
    """
    question = (
        "Look at the car in this image. Identify its primary color and its brand/make "
        "(e.g., Mercedes, Proton, Perodua, Honda, Toyota). "
        "Return ONLY the result in this exact format: [Color] - [Brand]. "
        "Do not include any other words."
    )

    messages = [
        {"role": "user", "content": [
            {"type": "image", "image": pil_image},
            {"type": "text", "text": question}
        ]}
    ]

    try:
        text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = processor(
            text=[text],
            images=[pil_image],
            return_tensors="pt",
            padding=True
        )

        inputs = {k: v.to(device) if isinstance(v, torch.Tensor) else v for k, v in inputs.items()}

        with torch.no_grad():
            generated_ids = qwen_model.generate(
                **inputs,
                max_new_tokens=20,
                do_sample=False,
                temperature=0.1,
            )

        generated_ids_trimmed = [
            out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs["input_ids"], generated_ids)
        ]

        response = processor.batch_decode(
            generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
        )[0]

        return parse_car_attributes(response)

    except Exception as e:
        print(f"\n❌ [QWEN ERROR] Failed to get attributes: {e}")
        return None


# ==============================================================================================================
# 6. EXIT VERIFICATION
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
    car_model, plate_model, ocr_model, qwen_model, processor, device = load_all_models()

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
            frame, persist=True, tracker="bytetrack.yaml",
            conf=CAR_CONFIDENCE_THRESHOLD, verbose=False
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

                # SEND PERFECT CAR CROP DIRECTLY TO QWEN
                car_crop_rgb = cv2.cvtColor(car_crop_bgr, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(car_crop_rgb)

                print(f"   [SYSTEM] Running Qwen to identify {plate_text} (synchronous)...")
                attributes = get_qwen_attributes(qwen_model, processor, device, pil_image)

                if attributes:
                    print(f"   [SYSTEM] Detected: {attributes['color']} - {attributes['model']}")
                    print(f"   [SYSTEM] Verifying with backend...")

                    # 5. VERIFY AND EXIT
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
                else:
                    print(f"   [SYSTEM] Qwen failed — cannot verify exit for {plate_text}")
                    cv2.putText(frame, "VERIFY FAILED", (cx1, cy1 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)

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
        description="SmartPark Exit Gate LPR — License Plate Recognition with YOLO + YOLO OCR + Qwen Attributes"
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