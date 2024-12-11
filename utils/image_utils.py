import os
from PIL import Image
import pillow_heif
from utils.logger import logger
from concurrent.futures import ThreadPoolExecutor, as_completed 

def convert_heic_to_jpeg_bulk(heic_paths, output_dir="converted_images"):
    """
    Converts a list of HEIC images to JPEG in bulk and returns a list of the converted image paths.
    Utilizes parallel processing for faster conversion.
    """
    try:
        project_root = os.getcwd()
        output_absolute_dir = os.path.join(project_root, output_dir)

        os.makedirs(output_absolute_dir, exist_ok=True)

        pillow_heif.register_heif_opener()

        converted_paths = []

        with ThreadPoolExecutor() as executor:
            futures = []
            for heic_path in heic_paths:
                heic_absolute_path = os.path.join(project_root, heic_path.lstrip("/"))
                futures.append(executor.submit(convert_heic_to_jpeg_single, heic_absolute_path, output_absolute_dir))

            for future in as_completed(futures):
                converted_path = future.result()
                if converted_path:
                    converted_paths.append(converted_path)
        logger.info(f"Bulk conversion completed. Converted {len(converted_paths)} images.")
        return converted_paths

    except Exception as e:
        logger.error(f"Error during bulk conversion: {e}")
        return []
def convert_heic_to_jpeg(heic_absolute_path, output_dir="uploads"):
    """
    Converts a single HEIC image to JPEG and returns the path of the converted image.
    """
    logger.debug(f"Converting HEIC image to JPEG: {heic_absolute_path}")
    try:
        project_root = os.getcwd()
        output_absolute_dir = os.path.join(project_root, output_dir)

        os.makedirs(output_absolute_dir, exist_ok=True)

        pillow_heif.register_heif_opener()

        return convert_heic_to_jpeg_single(heic_absolute_path, output_absolute_dir)

    except Exception as e:
        logger.error(f"Error during conversion: {e}")
        return None
def convert_heic_to_jpeg_single(heic_absolute_path, output_absolute_dir):
    """Converts a single HEIC image to JPEG."""
    try:
        if not os.path.exists(heic_absolute_path):
            logger.error(f"File not found: {heic_absolute_path}")
            return None

        with Image.open(heic_absolute_path) as img:
            jpeg_path = os.path.join(
                output_absolute_dir,
                os.path.basename(heic_absolute_path).replace('.heic', '.jpg').replace('.HEIC', '.jpg')
            )
            img.save(jpeg_path, "JPEG")
            jpeg_path_relative = os.path.relpath(jpeg_path, start=os.getcwd())
            return jpeg_path_relative
    except Exception as e:
        return None
