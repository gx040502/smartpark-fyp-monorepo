import cv2
import torch
from ultralytics import YOLO
from PIL import Image
from transformers import AutoProcessor
import numpy as np
import os
import time
import re

# --- SAFE IMPORT FOR QWEN ---
try:
    from transformers import Qwen3VLForConditionalGeneration
except ImportError:
    from transformers import AutoModelForCausalLM as Qwen3VLForConditionalGeneration

from huggingface_hub import login

# ==========================================
# CONFIGURATION
# ==========================================
# 1. Paths
YOLO_MODEL_PATH = r"C:\Users\Tan Gyap Xun\FYP\training_job\1.Train\car-plate\detect\v11n\weights\best.pt"
INPUT_VIDEO = r"C:\Users\Tan Gyap Xun\FYP\video\Recording 2025-12-02 174133.mp4"       # Update this to your video path
OUTPUT_VIDEO = "live_qwen.mp4"    # Where to save the result

# 2. Hugging Face
HF_TOKEN = "" 
QWEN_MODEL_ID = 'Qwen/Qwen3-VL-2B-Instruct'

# 3. Settings
CONFIDENCE_THRESHOLD = 0.5  # Only OCR if YOLO is 50% sure it's a plate
SAVE_VIDEO = True

# ==========================================
# MODEL LOADING
# ==========================================

def load_models():
    print("--- LOADING MODELS ---")
    
    # 1. Load YOLO
    print(f"Loading YOLO from: {YOLO_MODEL_PATH}")
    if not os.path.exists(YOLO_MODEL_PATH):
        raise FileNotFoundError(f"YOLO weights not found at {YOLO_MODEL_PATH}")
    yolo_model = YOLO(YOLO_MODEL_PATH)

    # 2. Load Qwen
    if HF_TOKEN:
        login(token=HF_TOKEN)
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Loading Qwen ({QWEN_MODEL_ID}) on {device}...")

    try:
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
        print("Models loaded successfully!")
        return yolo_model, qwen_model, processor, device

    except Exception as e:
        print(f"Critical Error loading Qwen: {e}")
        exit()

# ==========================================
# HELPER FUNCTIONS
# ==========================================

def clean_text(text):
    """Clean Qwen output to be alphanumeric only."""
    text = text.strip().upper().replace("-", "").replace("\n", " ")
    return re.sub(r"[^A-Z0-9]", "", text)

def run_qwen_ocr(model, processor, device, pil_image):
    """Runs Qwen-VL on a specific image crop."""
    question = "Extract the car plate number. Return ONLY the alphanumeric characters."
    
    messages = [{
        "role": "user",
        "content": [
            {"type": "image", "image": pil_image},
            {"type": "text", "text": question},
        ],
    }]

    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    
    inputs = processor(
        text=[text], 
        images=[pil_image], 
        return_tensors="pt", 
        padding=True
    )
    
    inputs = {k: v.to(device) if isinstance(v, torch.Tensor) else v for k, v in inputs.items()}

    with torch.no_grad():
        generated_ids = model.generate(
            **inputs,
            max_new_tokens=20, # Short max tokens for speed
            do_sample=False,
            temperature=0.1,
        )

    generated_ids_trimmed = [
        out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs["input_ids"], generated_ids)
    ]
    
    response = processor.batch_decode(
        generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
    )[0]

    return clean_text(response)

# ==========================================
# MAIN VIDEO LOOP
# ==========================================

def process_video():
    # Load everything
    yolo, qwen, processor, device = load_models()

    # Open Video
    # It opens the file and points to Frame #0 (the very first photo). 
    # It pauses there, waiting for instructions.
    cap = cv2.VideoCapture(INPUT_VIDEO)
    if not cap.isOpened():
        print(f"Error opening video: {INPUT_VIDEO}")
        return

    # Setup Video Writer
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    
    out = None
    if SAVE_VIDEO:
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(OUTPUT_VIDEO, fourcc, fps, (width, height))
        print(f"Saving video to: {OUTPUT_VIDEO}")

    print("\n--- STARTING PROCESSING ---")
    print("Press 'q' to stop early.")

    frame_count = 0
    
    # Next Page Loop
    while cap.isOpened():
        # critical step where the "Video" becomes a "Photo."
        # It grabs the current image the video player is paused on.
        # It loads that image into the variable frame as a grid of pixels (a NumPy array)
        ret, frame = cap.read()
        if not ret:
            break

        # 1. Run YOLO detection on the whole frame
        results = yolo.predict(frame, conf=CONFIDENCE_THRESHOLD, verbose=False)
        
        # We need a list to store texts found in THIS frame
        frame_plate_texts = []

        # 2. Iterate through detections
        for box in results[0].boxes:
            # Get coordinates (x1, y1, x2, y2)
            coords = box.xyxy[0].cpu().numpy().astype(int)
            x1, y1, x2, y2 = coords
            
            # --- CROP THE PLATE ---
            # Safety check: ensure coordinates are within frame
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(width, x2), min(height, y2)
            
            # Extract the crop (OpenCV uses BGR)
            plate_crop_bgr = frame[y1:y2, x1:x2]
            
            if plate_crop_bgr.size == 0: continue

            # Convert BGR to RGB for Qwen/PIL
            plate_crop_rgb = cv2.cvtColor(plate_crop_bgr, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(plate_crop_rgb)

            # --- RUN QWEN OCR ---
            detected_text = run_qwen_ocr(qwen, processor, device, pil_image)
            frame_plate_texts.append(detected_text)

            # Draw Box on Frame (Visual feedback)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

        # 3. Display Text on Top Right
        for i, text in enumerate(frame_plate_texts):
            display_str = f"Plate {i+1}: {text}"
            
            # Calculate text size
            (text_w, text_h), baseline = cv2.getTextSize(display_str, cv2.FONT_HERSHEY_SIMPLEX, 1, 2)
            
            # Top right coordinates
            box_x = width - text_w - 20
            box_y = 20 + (i * (text_h + 20))
            
            # Draw background rectangle (White)
            cv2.rectangle(frame, 
                         (box_x - 5, box_y - 5), 
                         (width - 5, box_y + text_h + 5), 
                         (255, 255, 255), 
                         -1) # -1 means filled
            
            # Draw text (Blue)
            cv2.putText(frame, 
                       display_str, 
                       (box_x, box_y + text_h), 
                       cv2.FONT_HERSHEY_SIMPLEX, 
                       1, 
                       (255, 0, 0), # Blue in BGR
                       2)

        # 4. Save
        if out:
            out.write(frame)
            
        # --- DISPLAY ENABLED ---
        # This will now work because you fixed your OpenCV installation!
        cv2.imshow("YOLO + Qwen OCR", frame)
        
        # Press 'q' to stop
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        
        frame_count += 1
        print(f"Processed Frame {frame_count} | Detected: {frame_plate_texts}")

    # Cleanup
    cap.release()
    if out: out.release()
    cv2.destroyAllWindows()
    print("Processing Complete.")

if __name__ == "__main__":
    process_video()