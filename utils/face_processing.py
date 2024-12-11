import os
import cv2
import numpy as np
import face_recognition
from concurrent.futures import ThreadPoolExecutor
from utils.logger import logger
from config import THRESHOLD, metadata, index
from utils.image_utils import convert_heic_to_jpeg_bulk

os.makedirs("converted_images", exist_ok=True)

def calculate_accuracy(distance, threshold=THRESHOLD):
    return max(0, round((1 - distance) * 100)) if distance < threshold else 0

def process_image(image_bytes, path_of_image=None):
    try:
        logger.info("Processing image...")
        if not image_bytes:
            raise ValueError("Empty image data")


        img_array = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("Image decoding failed")

        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        face_locations = face_recognition.face_locations(rgb_image, model="hog")
        face_encodings = face_recognition.face_encodings(rgb_image, face_locations)

        logger.debug(f"Detected {len(face_encodings)} face(s)")
        for i, encoding in enumerate(face_encodings):
            logger.debug(f"Encoding {i}: Type: {type(encoding)}, Shape: {getattr(encoding, 'shape', 'N/A')}")

        if not face_encodings:
            logger.warning("No faces detected in the image")
            return {
                "image_path": path_of_image,
                "matches": [],
                "matched_images": [],
                "accuracies": [],
                "message": "No faces detected",
                "success": False,
            }

        matches, matched_images, accuracies = [], [], []
        image_to_convert = []
        filtered_matched_images = []


        with ThreadPoolExecutor() as executor:
            futures = []
            for encoding in face_encodings:
                encoding_array = np.array([encoding])

                futures.append(executor.submit(index.search, encoding_array, len(metadata)))

            for future in futures:
                distances, indices = future.result()

                for i, distance in enumerate(distances[0]):
                    image_path = f"/dataset_images/{metadata[indices[0][i]]}"
                    if distance < THRESHOLD:
                        matched_images.append(image_path)
                        accuracies.append(calculate_accuracy(distance))
                        matches.append(f"Match found: {metadata[indices[0][i]]} (Accuracy: {accuracies[-1]}%)")
        
        for image in matched_images:
            if image.endswith(".heic") or image.endswith(".HEIC"):
                image_to_convert.append(image)
            else:
                filtered_matched_images.append(image)

        if image_to_convert:
            converted_images = convert_heic_to_jpeg_bulk(image_to_convert)
            matched_images = filtered_matched_images + converted_images
        else:
            matched_images = filtered_matched_images
        
        logger.debug(f"Length of matched images: {len(matched_images)}")

        return {
            "image_path": path_of_image,
            "matches": matches,
            "matched_images": matched_images,
            "accuracies": accuracies,
            "message": "Processing completed successfully",
            "success": True,
        }

    except Exception as e:
        logger.error(f"Image processing failed: {e}")
        return {
            "image_path": path_of_image,
            "matches": [],
            "matched_images": [],
            "accuracies": [],
            "message": f"Image processing failed: {e}",
            "success": False,
        }
