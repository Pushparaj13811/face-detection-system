from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from middlewares import setup_middlewares
from utils.logger import logger
from tasks.processing_tasks import router as tasks_router
from utils.async_utils import shutdown_executor
from fastapi.responses import HTMLResponse
from fastapi.requests import Request

app = FastAPI(
    title="Face Recognition API",
    description="Concurrent Face Recognition Service",
    docs_url="/docs",
)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/dataset_images", StaticFiles(directory="dataset_images"), name="dataset_images")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/converted_images", StaticFiles(directory="converted_images"), name="converted_images")

# Jinja2 templates
templates = Jinja2Templates(directory="templates")

# Apply middlewares
setup_middlewares(app)

# Include routers
app.include_router(tasks_router)

@app.get("/", response_class=HTMLResponse)
async def serve_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
@app.on_event("shutdown")
async def shutdown_event():
    await shutdown_executor()
    logger.info("Application shutting down...")
