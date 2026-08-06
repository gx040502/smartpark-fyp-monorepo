import cv2
import math
import numpy as np
from ultralytics import YOLO
from PIL import Image
import concurrent.futures
import threading
import torch
import os
import re
import requests
from dotenv import load_dotenv

load_dotenv()

try:
    from transformers import Qwen3VLForConditionalGeneration
except ImportError:
    from transformers import AutoModelForCausalLM as Qwen3VLForConditionalGeneration
from transformers import AutoProcessor
from huggingface_hub import login

# ==============================================================================================================
# 1. CONFIGURATION
# ==============================================================================================================
# Model Paths
CAR_MODEL_PATH = r"G:\My Drive\FYP\CAR MODEL\outputs\car_mixed\yolo11_run_01\weights\best.pt"
PLATE_MODEL_PATH = r"G:\My Drive\FYP\LICENSE PLATE\outputs\License-Plate-Recognition-11\yolo11_run_02\weights\best.pt"
OCR_MODEL_PATH = r"G:\My Drive\FYP\OCR\outputs\CatEye-ALPR-v3-3\yolo11_run_01\weights\best.pt"
INPUT_VIDEO = r"C:\Users\Tan Gyap Xun\Desktop\DEGREE\UTAR video\UTAR 3 CAR\UTAR 3 CAR-1.mp4"
OUTPUT_VIDEO = "lpr_entrance_output.mp4"
SAVE_VIDEO = True

HF_TOKEN = os.getenv("HF_TOKEN")
LARAVEL_API_URL = os.getenv("LARAVEL_API_URL", "http://127.0.0.1:8000")
QWEN_MODEL_ID = 'Qwen/Qwen3-VL-2B-Instruct'

# Application Settings
CAR_CONFIDENCE_THRESHOLD = 0.5
PLATE_CONFIDENCE_THRESHOLD = 0.3
OCR_CONFIDENCE_THRESHOLD = 0.7
SECONDS_TO_CONFIRM = 1  # Wait this many seconds before triggering Qwen

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
# 3. BACKGROUND WORKER FOR QWEN
# ==============================================================================================================
def parse_car_attributes(text):
    cleaned = text.strip().replace("\n", " ")
    
    if ' - ' in cleaned:
        parts = cleaned.split(' - ', 1)
        color = parts[0].strip()
        model = parts[1].strip()
    else:
        color = "Unknown"
        model = cleaned if cleaned else "Unknown"
    
    return {'color': color, 'model': model}

def save_car_details(plate_number, color, model):
    payload = {
        'license_plate': plate_number,
        'color': color,
        'model': model,
    }
    try:
        response = requests.post(
            f"{LARAVEL_API_URL}/api/parking-sessions/car-entry",
            json=payload,
            timeout=5
        )
        if response.status_code == 201:
            print(f"\n✅ [DATABASE] Parking session created! "
                  f"Plate: {plate_number} | Color: {color} | Model: {model}")
        else:
            print(f"\n⚠️ [DATABASE] Unexpected response ({response.status_code}): {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"\n❌ [DATABASE ERROR] Failed to save {plate_number}: {e}")

def fetch_qwen_attributes(qwen_model, processor, device, pil_image, plate_number):
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
        
        attributes = parse_car_attributes(response)
        save_car_details(plate_number, attributes['color'], attributes['model'])
        
    except Exception as e:
        print(f"\n❌ [QWEN ERROR] Failed to get attributes for {plate_number}: {e}")


# ==============================================================================================================
# 4. OCR EXTRACTION & SORTING
# ==============================================================================================================
def extract_plate_text(ocr_model, plate_crop_bgr):
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
# 5. MAIN VIDEO LOOP
# ==============================================================================================================
def load_all_models():
    print("--- LOADING MODELS (This may take a minute) ---")
    car_model = YOLO(CAR_MODEL_PATH)
    plate_model = YOLO(PLATE_MODEL_PATH)
    ocr_model = YOLO(OCR_MODEL_PATH)
    
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
    return car_model, plate_model, ocr_model, qwen_model, processor, device

def process_video():
    car_model, plate_model, ocr_model, qwen_model, processor, device = load_all_models()
    
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    
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

        # 🚀 TRACK CARS INSTEAD OF PLATES
        results = car_model.track(frame, persist=True, tracker="bytetrack.yaml", conf=CAR_CONFIDENCE_THRESHOLD, verbose=False)
        
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
                
                # Run plate model ONLY on the isolated car crop
                plate_results = plate_model(car_crop_bgr, conf=PLATE_CONFIDENCE_THRESHOLD, verbose=False)
                
                if plate_results[0].boxes is None or len(plate_results[0].boxes) == 0:
                    continue # Car is stable, but plate isn't visible yet. Wait for next frame.
                
                # Get the highest confidence plate
                plate_box = plate_results[0].boxes.xyxy[0].cpu().numpy().astype(int)
                px1, py1, px2, py2 = plate_box
                
                # Clamp plate coordinates to car crop boundaries
                px1, py1 = max(0, px1), max(0, py1)
                px2, py2 = min(car_crop_bgr.shape[1], px2), min(car_crop_bgr.shape[0], py2)
                
                plate_crop = car_crop_bgr[py1:py2, px1:px2]
                if plate_crop.size == 0: continue
                
                # Draw Plate Box on the main frame (Green) by offsetting car coordinates
                cv2.rectangle(frame, (cx1 + px1, cy1 + py1), (cx1 + px2, cy1 + py2), (0, 255, 0), 2)

                try:
                    enhanced_plate = process_plate_pipeline(plate_crop)
                except Exception as e:
                    print(f"⚠️ [SYSTEM] Skipping plate on car ID {track_id} due to enhancement failure: {e}")
                    continue
                
                # OCR EXTRACTION
                plate_text = extract_plate_text(ocr_model, enhanced_plate)
                if not plate_text: continue
                
                # Mark entire car sequence as processed
                processed_track_ids.add(track_id)
                
                print(f"\n🚗 [SYSTEM] Stable Car & Plate Detected: {plate_text} (Track ID: {track_id})")
                print(f"   [SYSTEM] Barrier Opened! Letting car enter immediately...")

                cv2.putText(frame, plate_text, (cx1, cy1 - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

                # SEND PERFECT CAR CROP DIRECTLY TO QWEN (No expansion needed)
                car_crop_rgb = cv2.cvtColor(car_crop_bgr, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(car_crop_rgb)
                
                print(f"   [SYSTEM] Sending {plate_text} car crop to LOCAL Qwen in background...")
                executor.submit(fetch_qwen_attributes, qwen_model, processor, device, pil_image, plate_text)

        if out: out.write(frame)
        cv2.imshow("SmartPark LPR", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Cleanup
    cap.release()
    if out: out.release()
    cv2.destroyAllWindows()
    
    print("\nWaiting for remaining background Qwen tasks to finish...")
    executor.shutdown(wait=True) 
    print("Processing Complete.")

if __name__ == "__main__":
    process_video()