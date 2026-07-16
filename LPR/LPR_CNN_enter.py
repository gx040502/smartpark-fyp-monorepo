"""
LPR.py — SmartPark License Plate Recognition Pipeline
══════════════════════════════════════════════════════
A standalone script that combines:
  1. License Plate Detection   — YOLOv11
  2. Character Segmentation    — OpenCV contours + vertical projection splitting
  3. Character Recognition     — Pre-trained CNN (OCR)
  4. Car Attribute Extraction   — Qwen3-VL (color & brand)
  5. Database Saving            — HTTP POST to Laravel backend

Usage:
    python LPR.py
    python LPR.py --video path/to/video.mp4
    python LPR.py --video path/to/video.mp4 --output output.mp4
    python LPR.py --no-save-video
"""

import argparse
import concurrent.futures
import math
import os
import sys

os.environ["TF_USE_LEGACY_KERAS"] = "1"

import cv2
import numpy as np
import requests
import torch
from dotenv import load_dotenv
from PIL import Image
from ultralytics import YOLO
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Flatten, MaxPooling2D, Dropout, Conv2D

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
PLATE_MODEL_PATH = r"G:\My Drive\FYP\LICENSE PLATE\outputs\License-Plate-Recognition-11\yolo11_run_02\weights\best.pt"
CNN_CHECKPOINT_PATH = "checkpoints/my_checkpoint"

# Video I/O  (overridable via CLI args)
INPUT_VIDEO = r"C:\Users\Tan Gyap Xun\Downloads\i_want_you_to_generate_a_video.mp4"
OUTPUT_VIDEO = "lpr_entrance_output.mp4"
SAVE_VIDEO = True

# API & Model Config
HF_TOKEN = os.getenv("HF_TOKEN")
LARAVEL_API_URL = os.getenv("LARAVEL_API_URL", "http://127.0.0.1:8000")
QWEN_MODEL_ID = "Qwen/Qwen3-VL-2B-Instruct"

# Application Settings
EXPANSION_FACTOR = 6.0
CONFIDENCE_THRESHOLD = 0.3
SECONDS_TO_CONFIRM = 1.5  # Wait this many seconds before triggering Qwen


# ==============================================================================================================
# 2. MODEL LOADING
# ==============================================================================================================

def load_all_models():
    """
    Load and return all three models used in the pipeline:
      - YOLO plate detector
      - CNN OCR character recogniser
      - Qwen3-VL vision-language model (for car color & brand)
    """
    print("--- LOADING MODELS (This may take a minute) ---")

    # 1. Load YOLO Plate Model
    plate_model = YOLO(PLATE_MODEL_PATH)
    print("✅ Loaded YOLO Plate Model.")

    # 2. Load CNN OCR Model
    loaded_model = Sequential()
    loaded_model.add(Conv2D(16, (22, 22), input_shape=(28, 28, 3), activation='relu', padding='same'))
    loaded_model.add(Conv2D(32, (16, 16), input_shape=(28, 28, 3), activation='relu', padding='same'))
    loaded_model.add(Conv2D(64, (8, 8), input_shape=(28, 28, 3), activation='relu', padding='same'))
    loaded_model.add(Conv2D(64, (4, 4), input_shape=(28, 28, 3), activation='relu', padding='same'))
    loaded_model.add(MaxPooling2D(pool_size=(4, 4)))
    loaded_model.add(Dropout(0.4))
    loaded_model.add(Flatten())
    loaded_model.add(Dense(128, activation='relu'))
    loaded_model.add(Dense(36, activation='softmax'))

    loaded_model.load_weights(CNN_CHECKPOINT_PATH)
    print("✅ Loaded CNN OCR Model.")

    # 3. Load Qwen Model
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

    return plate_model, loaded_model, qwen_model, processor, device


# ==============================================================================================================
# 3. CHARACTER SEGMENTATION (CONTOURS)
# ==============================================================================================================

def split_merged_contour(img, x, y, w, h, typical_width):
    """
    Split an oversized bounding box into individual characters using vertical
    projection.  When two or more characters are visually stuck together (due
    to dirt, shadows, etc.), this function finds the thinnest connecting points
    column-by-column and slices the merged block into individual character boxes.
    """
    region = img[y:y + h, x:x + w]
    # Count black pixels (0) per column — characters are black on white bg
    col_density = np.sum(region == 0, axis=0)

    n_chars = round(w / typical_width)
    if n_chars <= 1:
        return [(x, y, w, h)]

    target_width = w / n_chars
    split_points = [0]

    for i in range(1, n_chars):
        # Look for the local minimum (thinnest connection) near the expected split point
        expected = int(i * target_width)
        search_range = int(target_width * 0.3)
        lo = max(split_points[-1] + 1, expected - search_range)
        hi = min(w - 1, expected + search_range)
        if lo < hi:
            local_min_offset = np.argmin(col_density[lo:hi])
            split_points.append(lo + local_min_offset)
        else:
            split_points.append(expected)

    split_points.append(w)

    boxes = []
    for i in range(len(split_points) - 1):
        sub_x = x + split_points[i]
        sub_w = split_points[i + 1] - split_points[i]
        boxes.append((sub_x, y, sub_w, h))
    return boxes


def find_contours(dimensions, img):
    """
    Find bounding boxes around potential characters in a binary plate image.
    Filters by expected width/height, splits oversized boxes via
    split_merged_contour(), then extracts, resizes, inverts, and pads each
    character into a standardised 44×24 image sorted left-to-right.
    """
    cntrs, _ = cv2.findContours(img.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    lower_width = dimensions[0]
    upper_width = dimensions[1]
    lower_height = dimensions[2]
    upper_height = dimensions[3]

    LP_WIDTH = img.shape[1]  # width of the whole plate image

    cntrs = sorted(cntrs, key=cv2.contourArea, reverse=True)[:15]

    # --- Pass 1: find typical single-character width from valid boxes ---
    candidate_widths = []
    for cntr in cntrs:
        x, y, w, h = cv2.boundingRect(cntr)
        if lower_width < w < upper_width and lower_height < h < upper_height:
            candidate_widths.append(w)

    typical_width = np.median(candidate_widths) if candidate_widths else (lower_width + upper_width) / 2

    # --- Pass 2: build the final list of character boxes, splitting oversized ones ---
    final_boxes = []
    for cntr in cntrs:
        x, y, w, h = cv2.boundingRect(cntr)
        if lower_height < h < upper_height:
            if lower_width < w < upper_width:
                final_boxes.append((x, y, w, h))
            elif w >= upper_width and w < LP_WIDTH * 0.8:  # oversized but not the plate border
                final_boxes.extend(split_merged_contour(img, x, y, w, h, typical_width))

    # --- Extract, resize, invert, and pad each character box ---
    x_cntr_list = []
    img_res = []
    for (intX, intY, intWidth, intHeight) in final_boxes:
        x_cntr_list.append(intX)

        char_copy = np.zeros((44, 24))
        char = img[intY:intY + intHeight, intX:intX + intWidth]
        char = cv2.resize(char, (20, 40))
        char = cv2.subtract(255, char)

        char_copy[2:42, 2:22] = char
        char_copy[0:2, :] = 0
        char_copy[:, 0:2] = 0
        char_copy[42:44, :] = 0
        char_copy[:, 22:24] = 0

        img_res.append(char_copy)

    # Sort left-to-right by x position
    indices = sorted(range(len(x_cntr_list)), key=lambda k: x_cntr_list[k])
    img_res_copy = [img_res[idx] for idx in indices]
    img_res = np.array(img_res_copy)

    return img_res


def deskew_binary_plate(binary_img):
    """
    Detect and correct tilt in a binary plate image.
    Uses cv2.minAreaRect() on the combined text contours to find the rotation
    angle, then rotates to straighten using cv2.getRotationMatrix2D +
    cv2.warpAffine.  Only corrects tilts between 0.5° and 45°.
    """
    # Invert so text pixels are white (foreground) for findContours
    inverted = cv2.bitwise_not(binary_img)
    contours, _ = cv2.findContours(inverted, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return binary_img  # No contours found, return as-is

    # Filter out tiny noise contours, then combine the rest
    valid_contours = [c for c in contours if cv2.contourArea(c) > 10]
    if not valid_contours:
        return binary_img

    # Combine all valid contours into one point cloud
    all_points = np.concatenate(valid_contours)

    # minAreaRect returns ((cx, cy), (w, h), angle)
    rect = cv2.minAreaRect(all_points)
    angle = rect[2]

    # Normalize angle: minAreaRect returns angle in [-90, 0) range
    if rect[1][0] < rect[1][1]:
        angle = angle + 90

    # Only correct if the tilt is meaningful (> 0.5°) but not extreme (< 45°)
    if abs(angle) < 0.5 or abs(angle) > 45:
        return binary_img

    # Rotate to correct the tilt
    (h, w) = binary_img.shape[:2]
    center = (w // 2, h // 2)
    rot_mat = cv2.getRotationMatrix2D(center, angle, 1.0)
    deskewed = cv2.warpAffine(
        binary_img, rot_mat, (w, h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=255  # White fill for binary bg
    )
    return deskewed


def segment_characters(image):
    """
    Main controller for character extraction from a cropped license plate image.
    Steps:
      1. Resize to 333×75
      2. Convert to grayscale → binary threshold (Otsu)
      3. Normalise polarity (white bg, black text)
      4. Deskew (straighten tilt)
      5. Erode + Dilate (morphological cleaning)
      6. Whiten borders
      7. Call find_contours() to extract individual character images
    """
    # Preprocess cropped license plate image
    img_lp = cv2.resize(image, (333, 75))
    img_gray_lp = cv2.cvtColor(img_lp, cv2.COLOR_BGR2GRAY)
    _, img_binary_lp = cv2.threshold(img_gray_lp, 200, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    if np.mean(img_binary_lp) < 127:
        img_binary_lp = cv2.bitwise_not(img_binary_lp)

    # Deskew: correct tilt so characters align horizontally
    img_binary_lp = deskew_binary_plate(img_binary_lp)

    img_binary_lp = cv2.erode(img_binary_lp, (3, 3))
    img_binary_lp = cv2.dilate(img_binary_lp, (3, 3))

    LP_WIDTH = img_binary_lp.shape[0]
    LP_HEIGHT = img_binary_lp.shape[1]

    # Make borders white
    img_binary_lp[0:3, :] = 255
    img_binary_lp[:, 0:3] = 255
    img_binary_lp[72:75, :] = 255
    img_binary_lp[:, 330:333] = 255

    # Estimations of character contour sizes of cropped license plates
    dimensions = [LP_WIDTH / 6, LP_WIDTH / 2, LP_HEIGHT / 14, 2 * LP_HEIGHT / 3]

    # Get contours within cropped license plate
    char_list = find_contours(dimensions, img_binary_lp)

    return char_list


# ==============================================================================================================
# 4. CNN OCR
# ==============================================================================================================

def fix_dimension(img):
    """
    The CNN model expects 3-channel (28×28×3) input but segmented characters
    are single-channel grayscale.  This duplicates the grayscale channel
    three times to match the expected input shape.
    """
    new_img = np.zeros((28, 28, 3))
    for i in range(3):
        new_img[:, :, i] = img
    return new_img


def predict_plate_text(char_list, cnn_model):
    """
    Run CNN inference on each segmented character image and concatenate
    the predictions into the final license plate string (e.g. 'ABC1234').
    """
    if len(char_list) == 0:
        return ""

    dic = {}
    characters = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    for i, c in enumerate(characters):
        dic[i] = c

    output = []
    for ch in char_list:
        img_ = cv2.resize(ch, (28, 28), interpolation=cv2.INTER_AREA)
        img = fix_dimension(img_)
        img_input = img.reshape(1, 28, 28, 3)

        # The model was trained with ImageDataGenerator(rescale=1./255)
        img_input = img_input / 255.0

        predictions = cnn_model.predict(img_input, verbose=0)
        y_ = np.argmax(predictions, axis=-1)[0]

        character = dic[y_]
        output.append(character)

    plate_number = ''.join(output)
    return plate_number


# ==============================================================================================================
# 5. QWEN ATTRIBUTE EXTRACTION & DATABASE SAVING
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
    """
    Run Qwen3-VL inference on a car crop to identify color and brand,
    then save results to the Laravel backend.  Designed to run in a
    background thread so the video loop is not blocked.
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
        # Convert image + prompt to Qwen input
        inputs = processor(
            text=[text],
            images=[pil_image],
            return_tensors="pt",
            padding=True
        )

        inputs = {k: v.to(device) if isinstance(v, torch.Tensor) else v for k, v in inputs.items()}

        # Generate response
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
# 6. MAIN VIDEO PROCESSING LOOP
# ==============================================================================================================

def process_video(input_video, output_video, save_video):
    """
    Main orchestrator that ties the entire pipeline together:
      1. Opens the video stream
      2. Tracks license plates across frames using YOLO + ByteTrack
      3. Waits until a plate is stable for SECONDS_TO_CONFIRM seconds
      4. Crops the plate → segment_characters() → predict_plate_text()
      5. Expands the bounding box to capture the car body
      6. Spawns a background thread for Qwen inference + database saving
      7. Displays the annotated video in real time
    """
    plate_model, cnn_ocr_model, qwen_model, processor, device = load_all_models()

    # Use a ThreadPoolExecutor to run Qwen tasks without freezing the video
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

    # State tracking
    processed_track_ids = set()   # cars that have already been processed
    track_history = {}            # how many frames each car has been visible

    cap = cv2.VideoCapture(input_video)
    if not cap.isOpened():
        print(f"Error opening video: {input_video}")
        return

    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    if fps <= 0:
        fps = 30  # Fallback

    # Calculate how many frames equals the confirmation delay
    min_frames_to_confirm = int(fps * SECONDS_TO_CONFIRM)
    print(f"FPS detected as {fps}. Waiting {min_frames_to_confirm} frames to confirm plates.")

    out = None
    if save_video:
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_video, fourcc, fps, (frame_width, frame_height))
        print(f"Saving video to: {output_video}")

    print("\n--- STARTING LIVE LPR SYSTEM ---")
    print("Press 'q' to stop.")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        results = plate_model.track(
            frame, persist=True, tracker="bytetrack.yaml",
            conf=CONFIDENCE_THRESHOLD, verbose=False
        )

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
                    cv2.putText(frame, "Processed", (x1, y1 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    continue

                # Show loading progress over the plate
                if frames_seen < min_frames_to_confirm:
                    cv2.putText(frame, f"Tracking... {frames_seen}/{min_frames_to_confirm}",
                                (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)
                    continue

                # ==========================================
                # STABILITY THRESHOLD REACHED! NEW CAR CONFIRMED!
                # ==========================================

                # 1. CROP PLATE & OCR
                plate_crop = frame[max(0, y1):min(frame_height, y2),
                                   max(0, x1):min(frame_width, x2)]
                if plate_crop.size == 0:
                    continue

                # SEGMENT CHARACTERS
                char_list = segment_characters(plate_crop)

                # CNN OCR
                plate_text = predict_plate_text(char_list, cnn_ocr_model)

                if not plate_text:
                    continue

                # Mark as processed immediately so we don't ask Qwen again next frame
                processed_track_ids.add(track_id)

                # 🟢 FAST ENTRY
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
                cv2.putText(frame, plate_text, (x1, y1 - 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

                # 3. SEND TO QWEN (BACKGROUND THREAD)
                if car_crop_bgr.size > 0:
                    car_crop_rgb = cv2.cvtColor(car_crop_bgr, cv2.COLOR_BGR2RGB)
                    pil_image = Image.fromarray(car_crop_rgb)

                    print(f"   [SYSTEM] Sending {plate_text} crop to LOCAL Qwen in background...")
                    executor.submit(
                        fetch_qwen_attributes,
                        qwen_model, processor, device, pil_image, plate_text
                    )

        if out:
            out.write(frame)
        cv2.imshow("SmartPark LPR", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Cleanup
    cap.release()
    if out:
        out.release()
    cv2.destroyAllWindows()

    print("\nWaiting for remaining background Qwen tasks to finish...")
    executor.shutdown(wait=True)
    print("Processing Complete.")


# ==============================================================================================================
# 7. ENTRY POINT
# ==============================================================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="SmartPark LPR — License Plate Recognition with YOLO + CNN OCR + Qwen Attributes"
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
