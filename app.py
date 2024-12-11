from fastapi import FastAPI, File, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import cv2
import numpy as np
import face_recognition
import faiss
import os
from PIL import Image
import pillow_heif
import asyncio
from concurrent.futures import ThreadPoolExecutor
import uuid

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/dataset_images", StaticFiles(directory="dataset_images"), name="dataset_images")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/converted_images", StaticFiles(directory="converted_images"), name="converted_images")

templates = Jinja2Templates(directory="templates")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

index = faiss.read_index("face_index.bin")
metadata = np.load("metadata.npy")

THRESHOLD = 0.22

# ThreadPoolExecutor for parallel processing
executor = ThreadPoolExecutor(max_workers=4)

def calculate_accuracy(distance, threshold=THRESHOLD):
    if distance > threshold:
        return 0
    return round((1 - distance) * 100)

def convert_heic_to_jpeg(heic_bytes, output_path):
    """Convert HEIC image bytes to JPEG format and save it to the given output path."""
    heif_file = pillow_heif.read_heif(heic_bytes)
    image = Image.frombytes(
        heif_file.mode, heif_file.size, heif_file.data, "raw"
    )
    image.save(output_path, "JPEG")

def process_image(image_bytes):
    """Process the uploaded image for face matching."""
    print("Image processing started...")
    img_array = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    if image is None:
        return [], [], [], None
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    face_locations = face_recognition.face_locations(rgb_image, model="hog̀")
    face_encodings = face_recognition.face_encodings(rgb_image, face_locations)
    matches, matched_images, accuracies = [], [], []
    for face_encoding in face_encodings:
        face_encoding = np.array([face_encoding])
        distances, indices = index.search(face_encoding, k=len(metadata))
        for i, distance in enumerate(distances[0]):
            if distance < THRESHOLD:
                match_filename = metadata[indices[0][i]]
                matched_images.append(f"/dataset_images/{match_filename}")
                accuracy = calculate_accuracy(distance)
                accuracies.append(accuracy)
                matches.append(f"Match found with {match_filename} (Distance: {distance}, Accuracy: {accuracy}%)")
    return matches, matched_images, accuracies, image

@app.get("/", response_class=HTMLResponse)
async def serve_index(request: Request):
    """Serve the dynamic HTML page."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/process-image/")
async def process_uploaded_image(file: UploadFile = File(...)):
    """Process uploaded image."""
    file_extension = file.filename.split(".")[-1].lower()
    print(f"Processing image: {file.filename} ({file_extension})")
    image_bytes = await file.read()


    unique_id = str(uuid.uuid4())
    converted_path = f"uploads/{unique_id}_converted.jpg"
    processed_image_path = f"uploads/{unique_id}_processed.jpg"

    if file_extension == "heic":
        try:
            print("Converting HEIC to JPEG...")
            convert_heic_to_jpeg(image_bytes, converted_path)
            with open(converted_path, "rb") as f:
                image_bytes = f.read()
            print("HEIC converted successfully")
        except Exception as e:
            return JSONResponse(status_code=400, content={"error": f"HEIC conversion failed: {str(e)}"})

    # Offload CPU-intensive processing to a thread pool
    matches, matched_images, accuracies, processed_image = await asyncio.get_event_loop().run_in_executor(
        executor, process_image, image_bytes
    )

    if processed_image is None:
        return JSONResponse(status_code=400, content={"error": "Image processing failed"})
    if not matches:
        return JSONResponse(content={"message": "No matches found", "image": None, "matched_images": [], "accuracy": []})

    # Save the processed image
    cv2.imwrite(processed_image_path, processed_image)

    converted_matched_images = []
    for matched_image in matched_images:
        if matched_image.lower().endswith(".heic"):
            try:
                heic_path = matched_image.replace("/dataset_images/", "dataset_images/")
                with open(heic_path, "rb") as f:
                    heic_bytes = f.read()
                converted_image_path = f"converted_images/{unique_id}_{os.path.basename(matched_image).replace('.heic', '.jpg')}"
                convert_heic_to_jpeg(heic_bytes, converted_image_path)
                converted_matched_images.append(f"/converted_images/{os.path.basename(converted_image_path)}")
            except Exception as e:
                converted_matched_images.append(matched_image)
        else:
            converted_matched_images.append(matched_image)

    return JSONResponse(content={
        "matches": matches,
        "image_path": f"/{processed_image_path}",
        "matched_images": converted_matched_images,
        "accuracy": accuracies
    })
