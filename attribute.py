import cv2
from ultralytics import YOLO
from PIL import Image
from huggingface_hub import InferenceClient
import numpy as np
import os
import re
import base64
import io

# ==============================================================================================================
# 1. CONFIGURATION OF PATH & VARIABLES
# ==============================================================================================================
# a. Paths
YOLO_MODEL_PATH = r"C:\Users\Tan Gyap Xun\FYP\training_job\1.Train\car-plate\detect\v11n\weights\best.pt"
INPUT_VIDEO = r"C:\Users\Tan Gyap Xun\FYP\video\Recording 2025-12-02 174133.mp4"       # Update this to your video path
OUTPUT_VIDEO = "live_qwen.mp4"    # Where to save the result

# b. Hugging Face
HF_TOKEN = "" 
QWEN_MODEL_ID = 'Qwen/Qwen3-VL-2B-Instruct'

# c. Settings
CONFIDENCE_THRESHOLD = 0.5  # Only OCR if YOLO is 50% sure it's a plate
SAVE_VIDEO = True

# ==============================================================================================================
# 2. LOAD MODELS (YOLO & QWEN)
# ==============================================================================================================
def load_models():
    print("--- LOADING MODELS ---")
    
    # 1. Load YOLO (Still runs locally for speed)
    print(f"Loading YOLO from: {YOLO_MODEL_PATH}")
    if not os.path.exists(YOLO_MODEL_PATH):
        raise FileNotFoundError(f"YOLO weights not found at {YOLO_MODEL_PATH}")
    yolo_model = YOLO(YOLO_MODEL_PATH)

    # 2. Load Qwen via HTTP InferenceClient
    print(f"Connecting to Qwen ({QWEN_MODEL_ID}) via Hugging Face API...")
    qwen_client = InferenceClient(model=QWEN_MODEL_ID, token=HF_TOKEN)
    
    print("Models loaded successfully!")
    return yolo_model, qwen_client

# ==============================================================================================================
# 3. PASSING IMAGE TO QWEN FOR EXTRACTING CAR ATTRIBUTES
# ==============================================================================================================
def parse_car_attributes(text):
    """Clean the text to ensure it looks nice on the screen."""
    # Just strip extra newlines and spaces, keep the natural text
    return text.strip().replace("\n", " ")

def run_qwen_car_analysis(client, pil_image):
    """Runs Qwen-VL to extract Car Color and Brand."""
    
    buffered = io.BytesIO()
    pil_image.save(buffered, format="JPEG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    image_url = f"data:image/jpeg;base64,{img_str}"

    # THE NEW PROMPT: Force Qwen to use a strict, predictable format
    question = (
        "Look at the car in this image. Identify its primary color and its brand/make "
        "(e.g., Mercedes, Proton, Perodua, Honda, Toyota). "
        "Return ONLY the result in this exact format: [Color] - [Brand]. "
        "Do not include any other words."
    )
    
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": image_url}},
                {"type": "text", "text": question}
            ]
        }
    ]

    try:
        response = client.chat.completions.create(
            messages=messages,
            max_tokens=20, # Keep it short since we only want "Red - Toyota"
            temperature=0.1
        )
        
        raw_text = response.choices[0].message.content
        return parse_car_attributes(raw_text)
    
    except Exception as e:
        print(f"API Error during Car Analysis: {e}")
        return "Unknown - Unknown"

# ==============================================================================================================
# 4. MAIN VIDEO LOOP
# ==============================================================================================================
def process_video():
    # a. Load everything
    yolo, qwen_client = load_models()

    # b. Open Video
    # It opens the file and points to Frame #0 (the very first photo). 
    # It pauses there, waiting for instructions.
    cap = cv2.VideoCapture(INPUT_VIDEO)
    if not cap.isOpened():
        print(f"Error opening video: {INPUT_VIDEO}")
        return

    # c. Setup Video Writer
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
    
    # Calculate how many frames make up 1 second
    frames_per_second = int(cap.get(cv2.CAP_PROP_FPS))
    # Or set this manually, e.g., PROCESS_EVERY_N_FRAMES = 15 (process twice a second)
    PROCESS_EVERY_N_FRAMES = frames_per_second
    
    # d. Next Page Loop
    while cap.isOpened():
        # critical step where the "Video" becomes a "Photo."
        # It grabs the current image the video player is paused on.
        # It loads that image into the variable frame as a grid of pixels (a NumPy array)
        ret, frame = cap.read()
        if not ret:
            break
            
        # Increment counter and check if we should process this frame
        frame_count += 1
        if frame_count % PROCESS_EVERY_N_FRAMES != 0:
            if out:
                out.write(frame) # Still write the frame to video to keep timing right
            continue

        # e. Run YOLO detection on the whole frame
        results = yolo.predict(frame, conf=CONFIDENCE_THRESHOLD, verbose=False)
        
        # f. We need a list to store texts found in THIS frame
        frame_car_attributes = []

        # g. Iterate through detections
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

            # --- RUN QWEN CAR ANALYSIS ---
            # Changed from run_qwen_ocr to our new function
            detected_attributes = run_qwen_car_analysis(qwen_client, pil_image)
            frame_car_attributes.append(detected_attributes) # You might want to rename this list to frame_car_attributes!

            # Draw Box on Frame (Visual feedback)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

        # h. Display Text on Top Right
        for i, text in enumerate(frame_car_attributes):
            display_str = f"Car {i+1}: {text}"
            
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
        print(f"Processed Frame {frame_count} | Detected: {frame_car_attributes}")

    # Cleanup
    cap.release()
    if out: out.release()
    cv2.destroyAllWindows()
    print("Processing Complete.")

if __name__ == "__main__":
    process_video()