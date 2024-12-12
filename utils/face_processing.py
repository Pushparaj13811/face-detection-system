import os
import cv2
import numpy as np
import face_recognition
from concurrent.futures import ThreadPoolExecutor
from utils.logger import logger
from config import THRESHOLD, metadata, index as faiss_index
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

        face_locations = face_recognition.face_locations(rgb_image, model="mtcnn")
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

        with ThreadPoolExecutor() as executor:
            futures = []
            for encoding in face_encodings:
                encoding_array = np.array([encoding])

                futures.append(executor.submit(faiss_index.search, encoding_array, len(metadata)))

            for future in futures:
                distances, indices = future.result()

                for i, distance in enumerate(distances[0]):
                    image_path = f"/dataset_images/{metadata[indices[0][i]]}"
                    if distance < THRESHOLD:
                        matched_images.append(image_path)
                        accuracies.append(calculate_accuracy(distance))
                        matches.append(f"Match found: {metadata[indices[0][i]]} (Accuracy: {accuracies[-1]}%)")
        
        # Prepare a list to track original image names and conversion details
        final_matched_images = matched_images.copy()
        heic_images_to_convert = []
        heic_indices = []

        # Identify HEIC images and prepare for conversion
        for idx, image in enumerate(matched_images):
            if image.endswith(".heic") or image.endswith(".HEIC"):
                heic_images_to_convert.append(image)
                heic_indices.append(idx)

        # Convert HEIC images if any
        if heic_images_to_convert:
            converted_images = convert_heic_to_jpeg_bulk(heic_images_to_convert)
            
            # Ensure we don't go out of bounds
            for idx, original_heic_image in zip(heic_indices, heic_images_to_convert):
                # Find the corresponding converted image
                try:
                    converted_image_index = heic_images_to_convert.index(original_heic_image)
                    
                    # Check if we have a corresponding converted image
                    if converted_image_index < len(converted_images):
                        converted_image = converted_images[converted_image_index]
                        
                        # Preserve the original filename structure
                        original_basename = os.path.basename(original_heic_image)
                        converted_basename = os.path.basename(converted_image)
                        
                        final_converted_image = original_heic_image.replace(
                            os.path.splitext(original_basename)[0] + os.path.splitext(original_heic_image)[1],
                            os.path.splitext(original_basename)[0] + '.jpg'
                        )
                        
                        final_matched_images[idx] = final_converted_image
                    else:
                        logger.warning(f"Conversion failed for image: {original_heic_image}")
                
                except (ValueError, IndexError) as e:
                    logger.error(f"Error processing converted image: {e}")
        
        # Sort matched images, matches, and accuracies in descending order of accuracy
        sorted_data = sorted(
            zip(accuracies, matched_images, matches), 
            key=lambda x: x[0], 
            reverse=True
        )
        
        # Unpack the sorted data
        sorted_accuracies, sorted_matched_images, sorted_matches = zip(*sorted_data)

        logger.debug(f"Length of matched images: {len(sorted_matched_images)}")

        return {
            "image_path": path_of_image,
            "matches": list(sorted_matches),
            "matched_images": list(sorted_matched_images),
            "accuracies": list(sorted_accuracies),
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