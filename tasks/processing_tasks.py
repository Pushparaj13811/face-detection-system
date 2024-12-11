import os
import uuid
import aiofiles
from utils.logger import logger
from fastapi import APIRouter, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from utils.async_utils import run_in_executor
from utils.face_processing import process_image
from asyncio import create_task, Task
from utils.image_utils import convert_heic_to_jpeg

router = APIRouter()
processing_tasks: dict[str, Task] = {}

VALID_EXTENSIONS = (".png", ".jpg", ".jpeg", ".heic")
os.makedirs("uploads", exist_ok=True)

@router.post("/process-image/")
async def process_uploaded_image(file: UploadFile):
    if not file.filename.lower().endswith(VALID_EXTENSIONS):
        raise HTTPException(status_code=400, detail="Unsupported file type")

    filename = f"{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join("uploads", filename)

    try:
        async with aiofiles.open(file_path, "wb") as f:
            content = await file.read()
            await f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    if file.filename.lower().endswith(".heic"):
        logger.debug("Converting HEIC image to JPEG")
        try:
            converted_image = convert_heic_to_jpeg(file_path, "uploads")
            if not converted_image:
                raise ValueError("Conversion failed")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Conversion error: {str(e)}")
        
        try:
            os.remove(file_path)
        except OSError as e:
            logger.error(f"Error deleting file: {file_path} - {e}")

        file_path = converted_image
        logger.debug(f"HEIC image converted to JPEG: {file_path}")

    task_id = str(uuid.uuid4())
    try:
        async with aiofiles.open(file_path, "rb") as f:
            file_contents = await f.read()
        task = create_task(run_in_executor(process_image, file_contents, file_path))
        processing_tasks[task_id] = task
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start processing: {e}")

    return JSONResponse({"task_id": task_id, "message": "Processing started"})

@router.get("/task-status/{task_id}")
async def get_task_status(task_id: str):
    task = processing_tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.done():
        try:
            results = await task
            del processing_tasks[task_id]
            image_path = results.get("image_path", "Image path not found")
            try:
                os.remove(image_path)
            except OSError as e:
                logger.error(f"Error deleting file: {image_path} - {e}")

            return JSONResponse({"status": "completed", "results": results})
        except Exception as e:
            del processing_tasks[task_id]
            logger.error(f"Task {task_id} failed: {e}")
            return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

    return JSONResponse({"status": "processing"})
