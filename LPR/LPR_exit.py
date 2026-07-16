import cv2
import math
from ultralytics import YOLO
from PIL import Image
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
PLATE_MODEL_PATH = r"G:\My Drive\FYP\LICENSE PLATE\outputs\License-Plate-Recognition-11\yolo11_run_02\weights\best.pt"
OCR_MODEL_PATH = r"G:\My Drive\FYP\OCR\outputs\OCR-license-plate-PL-2\yolo11_run_01\weights\best.pt"
INPUT_VIDEO = r"C:\Users\Tan Gyap Xun\Videos\Screen Recordings\Screen Recording 2026-05-31 235311.mp4"
OUTPUT_VIDEO = "lpr_exit_output.mp4"
SAVE_VIDEO = True

HF_TOKEN = os.getenv("HF_TOKEN")
LARAVEL_API_URL = os.getenv("LARAVEL_API_URL", "http://127.0.0.1:8000")
QWEN_MODEL_ID = 'Qwen/Qwen3-VL-2B-Instruct'

# Application Settings
EXPANSION_FACTOR = 4.0
CONFIDENCE_THRESHOLD = 0.3
SECONDS_TO_CONFIRM = 2  # Wait this many seconds before triggering Qwen


# ==============================================================================================================
# 2. QWEN ATTRIBUTE DETECTION (SYNCHRONOUS — exit requires results before API call)
# ==============================================================================================================
def parse_car_attributes(text):
    """
    Parse Qwen's response in '[Color] - [Brand]' format.
    Returns a dict: {'color': '...', 'model': '...'}
    """
    cleaned = text.strip().replace("\n", " ")
    
    # Try to split by ' - ' separator (expected Qwen format)
    if ' - ' in cleaned:
        parts = cleaned.split(' - ', 1)
        color = parts[0].strip()
        model = parts[1].strip()
    else:
        # Fallback: treat entire response as unknown
        color = "Unknown"
        model = cleaned if cleaned else "Unknown"
    
    return {'color': color, 'model': model}


def get_qwen_attributes(qwen_model, processor, device, pil_image):
    """
    Runs Qwen SYNCHRONOUSLY and returns the parsed attributes.
    Unlike LPR_enter.py which fires-and-forgets, exit verification
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
# 3. EXIT VERIFICATION — send detected details to Laravel for verification
# ==============================================================================================================
def verify_and_exit(plate_number, color, model):
    """Send exit verification request to Laravel backend."""
    payload = {
        'license_plate': plate_number,
        'color': color,
        'model': model,
    }
    try:
        response = requests.post(
            f"{LARAVEL_API_URL}/api/parking-sessions/car-exit",
            json=payload,
            timeout=10
        )
        data = response.json()

        if response.status_code == 200:
            print(f"\n✅ [EXIT] Barrier Opened! {plate_number} verified and exiting.")
            print(f"   Session completed successfully.")
            return True
        elif response.status_code == 403:
            message = data.get('message', 'Exit denied.')
            print(f"\n🚫 [EXIT] Barrier CLOSED for {plate_number}: {message}")
            
            if data.get('overdue_minutes'):
                print(f"   Overdue: {data['overdue_minutes']} minutes | Extra charge: RM {data['extra_charge']}")
                print(f"   Driver must pay additional charge via the mobile app.")
            elif data.get('mismatch_type'):
                print(f"   ⚠️ Vehicle mismatch ({data['mismatch_type']}). Admin has been notified.")
            return False
        elif response.status_code == 404:
            print(f"\n⚠️ [EXIT] No paid session found for {plate_number}.")
            return False
        else:
            print(f"\n⚠️ [EXIT] Unexpected response ({response.status_code}): {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"\n❌ [EXIT ERROR] Failed to verify {plate_number}: {e}")
        return False


# ==============================================================================================================
# 4. OCR EXTRACTION & SORTING
# ==============================================================================================================
def extract_plate_text(ocr_model, plate_crop_bgr):
    """Runs OCR on the cropped plate and sorts characters from left to right."""
    results = ocr_model.predict(plate_crop_bgr, conf=0.5, verbose=False)
    
    detected_chars = []
    for box in results[0].boxes:
        x1 = float(box.xyxy[0][0])
        cls_id = int(box.cls[0])
        char_name = ocr_model.names[cls_id]
        
        # Save the x-coordinate to sort later
        detected_chars.append((x1, char_name))
    
    # Sort characters based on their x1 coordinate (left to right)
    detected_chars.sort(key=lambda item: item[0])
    
    # Join into a single string
    plate_text = "".join([char for _, char in detected_chars])
    return plate_text


# ==============================================================================================================
# 5. MAIN VIDEO LOOP
# ==============================================================================================================
def load_all_models():
    print("--- LOADING MODELS (This may take a minute) ---")
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
    return plate_model, ocr_model, qwen_model, processor, device

def process_video():
    plate_model, ocr_model, qwen_model, processor, device = load_all_models()
    
    # State tracking
    processed_track_ids = set()  # for checking if the car has already been processed
    track_history = {}  # Keeps track of how many frames a car has been visible

    cap = cv2.VideoCapture(INPUT_VIDEO)
    if not cap.isOpened():
        print(f"Error opening video: {INPUT_VIDEO}")
        return

    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    if fps <= 0: fps = 30  # Fallback just in case
    
    # Calculate how many frames equals 2 seconds
    min_frames_to_confirm = int(fps * SECONDS_TO_CONFIRM)
    print(f"FPS detected as {fps}. Waiting {min_frames_to_confirm} frames (2 seconds) to confirm plates.")
    
    out = None
    if SAVE_VIDEO:
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(OUTPUT_VIDEO, fourcc, fps, (frame_width, frame_height))
        print(f"Saving video to: {OUTPUT_VIDEO}")

    print("\n--- STARTING EXIT GATE LPR SYSTEM ---")
    print("Press 'q' to stop.")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break

        results = plate_model.track(frame, persist=True, tracker="bytetrack.yaml", conf=CONFIDENCE_THRESHOLD, verbose=False)
        
        if results[0].boxes is not None and results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy().astype(int)
            track_ids = results[0].boxes.id.cpu().numpy().astype(int)

            for box, track_id in zip(boxes, track_ids):
                x1, y1, x2, y2 = box
                
                # Draw Plate Box
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                
                # Update track history counter
                track_history[track_id] = track_history.get(track_id, 0) + 1
                frames_seen = track_history[track_id]
                
                # Already processed this car
                if track_id in processed_track_ids:
                    cv2.putText(frame, "Processed", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    continue
                
                # Show loading progress
                if frames_seen < min_frames_to_confirm:
                    cv2.putText(frame, f"Tracking... {frames_seen}/{min_frames_to_confirm}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)
                    continue
                
                # ==========================================
                # STABILITY THRESHOLD REACHED! PROCESS EXIT
                # ==========================================
                
                # 1. CROP PLATE & OCR
                plate_crop = frame[max(0, y1):min(frame_height, y2), max(0, x1):min(frame_width, x2)]
                if plate_crop.size == 0: continue
                
                plate_text = extract_plate_text(ocr_model, plate_crop)
                
                if not plate_text: continue
                
                # Mark as processed immediately
                processed_track_ids.add(track_id)
                
                print(f"\n🚗 [EXIT GATE] Stable Plate Detected: {plate_text} (Track ID: {track_id})")

                # 2. EXPAND BOX FOR CAR CROP
                w = x2 - x1
                h = y2 - y1
                
                car_x1 = max(0, int(x1 - (w * EXPANSION_FACTOR)))
                car_x2 = min(frame_width, int(x2 + (w * EXPANSION_FACTOR)))
                car_y1 = max(0, int(y1 - (h * EXPANSION_FACTOR)))
                car_y2 = min(frame_height, int(y2 + (h * EXPANSION_FACTOR)))
                
                car_crop_bgr = frame[car_y1:car_y2, car_x1:car_x2]
                
                cv2.rectangle(frame, (car_x1, car_y1), (car_x2, car_y2), (255, 0, 0), 2)
                cv2.putText(frame, plate_text, (x1, y1 - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

                # 3. GET QWEN ATTRIBUTES (SYNCHRONOUS — must wait before verifying exit)
                if car_crop_bgr.size > 0:
                    car_crop_rgb = cv2.cvtColor(car_crop_bgr, cv2.COLOR_BGR2RGB)
                    pil_image = Image.fromarray(car_crop_rgb)
                    
                    print(f"   [SYSTEM] Running Qwen to identify {plate_text} (synchronous)...")
                    attributes = get_qwen_attributes(qwen_model, processor, device, pil_image)
                    
                    if attributes:
                        print(f"   [SYSTEM] Detected: {attributes['color']} - {attributes['model']}")
                        print(f"   [SYSTEM] Verifying with backend...")
                        
                        # 4. VERIFY AND EXIT
                        allowed = verify_and_exit(plate_text, attributes['color'], attributes['model'])
                        
                        if allowed:
                            cv2.putText(frame, "EXIT OK", (car_x1, car_y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 3)
                        else:
                            cv2.putText(frame, "EXIT DENIED", (car_x1, car_y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)
                    else:
                        print(f"   [SYSTEM] Qwen failed — cannot verify exit for {plate_text}")
                        cv2.putText(frame, "VERIFY FAILED", (car_x1, car_y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)

        if out: out.write(frame)
        cv2.imshow("SmartPark LPR - Exit Gate", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Cleanup
    cap.release()
    if out: out.release()
    cv2.destroyAllWindows()
    print("Exit Gate Processing Complete.")

if __name__ == "__main__":
    process_video()
