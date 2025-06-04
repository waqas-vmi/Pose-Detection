from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
import uuid
import base64
import shutil
import logging
import os
from app.process import calculate_bmi

app = FastAPI()

# Configure logging
logging.basicConfig(
    filename="app.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Ensure the static directory and uploads directory exist
STATIC_DIR = "app/static"
UPLOAD_DIR = os.path.join(STATIC_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory="app/templates")

@app.get("/", response_class=HTMLResponse)
async def form_get(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})

@app.post("/", response_class=HTMLResponse)
async def form_post(request: Request,
                    image: UploadFile = File(...),
                    height: float = Form(...),
                    weight: float = Form(...)):
    try:

        # Log raw inputs (you may want to truncate the image string to avoid huge logs)
        logging.info("Request data=%s", request)
        logging.info("Received request with height=%s, weight=%s", height, weight)
        logging.info("Image (truncated): %s", image[:30])  # Only log the first 30 characters

        filename = f"{uuid.uuid4().hex}_{image.filename}"
        file_path = os.path.join(UPLOAD_DIR, filename)
        with open(file_path, "wb") as f:
            shutil.copyfileobj(image.file, f)

        # Use your logic from process.py
        result = calculate_bmi(file_path, height, weight)

        if "error" in result:
            return templates.TemplateResponse("upload.html", {
                "request": request,
                "error": result["error"]
            })

        return templates.TemplateResponse("upload.html", {
            "request": request,
            "result": result,
            "image_url": f"/static/uploads/{filename}"
        })

    except Exception as e:
        return templates.TemplateResponse("upload.html", {
            "request": request,
            "error": str(e)
        })

@app.post("/process-image")
async def process_image_api(
    image: str = Form(...),
    height: float = Form(...),
    weight: float = Form(...)
):
    try:
        if image.startswith("data:"):
            header, image = image.split(",", 1)

        # Decode base64 string
        image_data = base64.b64decode(image)
        # Save uploaded image
        filename = f"{uuid.uuid4().hex}.jpg"
        file_path = os.path.join(UPLOAD_DIR, filename)
        with open(file_path, "wb") as f:
            f.write(image_data)

        # Process image using your logic
        result = calculate_bmi(file_path, height, weight)

        # Return result
        if "error" in result:
            return JSONResponse(status_code=400, content={"error": result["error"]})

        return {
            "filename": filename,
            "bmi_result": result,
            "image_url": f"/static/uploads/{filename}"
        }

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})