from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import cv2
import numpy as np
import face_recognition
import base64
import faiss
import os

app = FastAPI()

origins = [
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "http://127.0.0.1:5500/index.html"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

index = faiss.read_index("face_index.bin")
metadata = np.load("metadata.npy")


THRESHOLD = 0.3

def calculate_accuracy(distance, threshold=THRESHOLD):
    if distance > threshold:
        return 0
    return round((1 - distance) * 100)

def process_image(image_bytes):
    img_array = np.frombuffer(image_bytes, np.uint8)
    
    image = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    print(f"Image shape: {image.shape}")

    if image is None:
        print("Error: Failed to decode the image")
        return [], [], [], None
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    

    face_locations = face_recognition.face_locations(rgb_image, model="cnn")
    print(f"Detected {len(face_locations)} faces in the uploaded image.")

    if not face_locations:
        print("No faces detected in the image.")

    face_encodings = face_recognition.face_encodings(rgb_image, face_locations)

    matches = []
    matched_images = []
    accuracies = []

    print(f"Detected {len(face_encodings)} faces in the uploaded image.")

    for face_encoding in face_encodings:
        face_encoding = np.array([face_encoding])
        distances, indices = index.search(face_encoding, k=len(metadata))

        for i, distance in enumerate(distances[0]):
            if distance < THRESHOLD:
                match_filename = metadata[indices[0][i]]
                matched_images.append(f"dataset_images/{match_filename}")
                accuracy = calculate_accuracy(distance)
                accuracies.append(accuracy)
                matches.append(f"Match found with {match_filename} (Distance: {distance}, Accuracy: {accuracy}%)")
    return matches, matched_images, accuracies, image

@app.post("/process-image/")
async def process_uploaded_image(file: UploadFile = File(...)):
    print(f"Processing image: {file.filename}")
    image_bytes = await file.read()
    print(f"Image size: {len(image_bytes)} bytes")

    matches, matched_images, accuracies, processed_image = process_image(image_bytes)


    if processed_image is None:
        return JSONResponse(status_code=400, content={"error": "Image processing failed"})

    if not matches:
        return JSONResponse(content={
            "message": "No matches found",
            "image": None,
            "matched_images": [],
            "accuracy": []
        })

    _, buffer = cv2.imencode('.jpg', processed_image)
    image_base64 = base64.b64encode(buffer).decode('utf-8')

    matched_images_base64 = []
    for matched_image in matched_images:
        if os.path.exists(matched_image):
            with open(matched_image, "rb") as img_file:
                img_base64 = base64.b64encode(img_file.read()).decode('utf-8')
                matched_images_base64.append(img_base64)
        else:
            print(f"Error: Matched image {matched_image} not found")

    return JSONResponse(content={
        "matches": matches,
        "image": image_base64,
        "matched_images": matched_images_base64,
        "accuracy": accuracies
    })
