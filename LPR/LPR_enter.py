import cv2
import math
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
PLATE_MODEL_PATH = r"G:\My Drive\FYP\LICENSE PLATE\outputs\License-Plate-Recognition-11\yolo11_run_02\weights\best.pt"
OCR_MODEL_PATH = r"G:\My Drive\FYP\OCR\outputs\OCR-license-plate-PL-2\yolo11_run_01\weights\best.pt"
INPUT_VIDEO = r"C:\Users\Tan Gyap Xun\Desktop\DEGREE\UTAR video\UTAR 5 CAR\UTAR 5 CAR-1.mp4"
OUTPUT_VIDEO = "lpr_entrance_output.mp4"
SAVE_VIDEO = True

HF_TOKEN = os.getenv("HF_TOKEN")
LARAVEL_API_URL = os.getenv("LARAVEL_API_URL", "http://127.0.0.1:8000")
QWEN_MODEL_ID = 'Qwen/Qwen3-VL-2B-Instruct'

# Application Settings
EXPANSION_FACTOR = 6.0
CONFIDENCE_THRESHOLD = 0.3
SECONDS_TO_CONFIRM = 1.5  # Wait this many seconds before triggering Qwen

# ==============================================================================================================
# 2. BACKGROUND WORKER FOR QWEN
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


def save_car_details(plate_number, color, model):
    """Send car entry details to the Laravel backend via HTTP POST."""
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
    """This function runs in the background. It calls Qwen locally and then simulates a DB save."""
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
        #convert image + prompt to Qwen input
        inputs = processor(
            text=[text], 
            images=[pil_image], 
            return_tensors="pt", 
            padding=True
        )
        
        inputs = {k: v.to(device) if isinstance(v, torch.Tensor) else v for k, v in inputs.items()}

        # generate response
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
        
        # 🟢 SAVE TO DATABASE VIA LARAVEL API
        save_car_details(plate_number, attributes['color'], attributes['model'])
        
    except Exception as e:
        print(f"\n❌ [QWEN ERROR] Failed to get attributes for {plate_number}: {e}")


# ==============================================================================================================
# 3. OCR EXTRACTION & SORTING
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
# 4. MAIN VIDEO LOOP
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
    
    # We use a ThreadPoolExecutor to run Qwen tasks without freezing the video
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    
    # State tracking
    processed_track_ids = set() # for checking if the car has already been processed
    track_history = {} # Keeps track of how many frames a car has been visible

    cap = cv2.VideoCapture(INPUT_VIDEO)
    if not cap.isOpened():
        print(f"Error opening video: {INPUT_VIDEO}")
        return

    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    if fps <= 0: fps = 30 # Fallback just in case
    
    # Calculate how many frames equals 2 seconds
    min_frames_to_confirm = int(fps * SECONDS_TO_CONFIRM)
    print(f"FPS detected as {fps}. Waiting {min_frames_to_confirm} frames (2 seconds) to confirm plates.")
    
    out = None
    if SAVE_VIDEO:
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(OUTPUT_VIDEO, fourcc, fps, (frame_width, frame_height))
        print(f"Saving video to: {OUTPUT_VIDEO}")

    print("\n--- STARTING LIVE LPR SYSTEM ---")
    print("Press 'q' to stop.")

    while cap.isOpened(): # Run loop and every loop process one frame
        ret, frame = cap.read() #take one picture from the video
        if not ret: break #if picture is not taken break the loop

        # 🚀 NO MORE SKIPPING! We run tracking on EVERY single frame now.
        results = plate_model.track(frame, persist=True, tracker="bytetrack.yaml", conf=CONFIDENCE_THRESHOLD, verbose=False)
        
        # using .track, every results[0].boxes.id is use to track the same car for multiple frames
        if results[0].boxes is not None and results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy().astype(int)
            track_ids = results[0].boxes.id.cpu().numpy().astype(int)

            for box, track_id in zip(boxes, track_ids):
                x1, y1, x2, y2 = box
                
                # Draw Plate Box
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                
                # Update track history counter for this specific car
                track_history[track_id] = track_history.get(track_id, 0) + 1 #EXP: .get(8, 2) mean track id with 8 has appear for 2 frames
                frames_seen = track_history[track_id]
                
                # If we've already fully processed this car, draw green text and skip
                if track_id in processed_track_ids:
                    cv2.putText(frame, "Processed", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    continue
                
                # Show loading progress over the plate (e.g. Tracking... 30/60)
                if frames_seen < min_frames_to_confirm:
                    cv2.putText(frame, f"Tracking... {frames_seen}/{min_frames_to_confirm}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)
                    continue
                
                # ==========================================
                # STABILITY THRESHOLD REACHED! NEW CAR CONFIRMED!
                # ==========================================
                
                # 1. CROP PLATE & OCR
                plate_crop = frame[max(0, y1):min(frame_height, y2), max(0, x1):min(frame_width, x2)]
                if plate_crop.size == 0: continue
                
                plate_text = extract_plate_text(ocr_model, plate_crop)
                
                if not plate_text: continue
                
                # Mark as processed immediately so we don't ask Qwen again next frame
                processed_track_ids.add(track_id)
                
                # 🟢 FAST ENTRY SIMULATION
                print(f"\n🚗 [SYSTEM] Stable Plate Detected: {plate_text} (Track ID: {track_id})")
                print(f"   [SYSTEM] Barrier Opened! Letting car enter immediately...")

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

                # 3. SEND TO QWEN (BACKGROUND THREAD)
                if car_crop_bgr.size > 0:
                    car_crop_rgb = cv2.cvtColor(car_crop_bgr, cv2.COLOR_BGR2RGB)
                    pil_image = Image.fromarray(car_crop_rgb)
                    
                    print(f"   [SYSTEM] Sending {plate_text} crop to LOCAL Qwen in background...")
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
