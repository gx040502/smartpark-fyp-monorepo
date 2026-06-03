import cv2
import math
from ultralytics import YOLO
from PIL import Image
import concurrent.futures
import threading
import torch
import os
import re
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
OUTPUT_VIDEO = "lpr_output.mp4"
SAVE_VIDEO = True

HF_TOKEN = os.getenv("HF_TOKEN")
QWEN_MODEL_ID = 'Qwen/Qwen3-VL-2B-Instruct'

# Application Settings
EXPANSION_FACTOR = 4.0
CONFIDENCE_THRESHOLD = 0.3
SECONDS_TO_CONFIRM = 2  # Wait this many seconds before triggering Qwen

# ==============================================================================================================
# 2. BACKGROUND WORKER FOR QWEN
# ==============================================================================================================
def parse_car_attributes(text):
    return text.strip().replace("\n", " ")

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
        
        # 🟢 SIMULATE DATABASE SAVE AFTER DELAY
        print(f"\n✅ [DATABASE] Update successful! Plate: {plate_number} | Attributes added: {attributes}\n")
        
    except Exception as e:
        print(f"\n❌ [DATABASE ERROR] Failed to get attributes for {plate_number}: {e}\n")


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
    processed_track_ids = set()
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

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break

        # 🚀 NO MORE SKIPPING! We run tracking on EVERY single frame now.
        results = plate_model.track(frame, persist=True, tracker="bytetrack.yaml", conf=CONFIDENCE_THRESHOLD, verbose=False)
        
        if results[0].boxes is not None and results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy().astype(int)
            track_ids = results[0].boxes.id.cpu().numpy().astype(int)

            for box, track_id in zip(boxes, track_ids):
                x1, y1, x2, y2 = box
                
                # Draw Plate Box
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                
                # Update track history counter for this specific car
                track_history[track_id] = track_history.get(track_id, 0) + 1
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
