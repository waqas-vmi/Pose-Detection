from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import requests
import uuid
import base64
import shutil
import logging
import os
from app.process import calculate_bmi
from app.process_images import calculate_bmi_from_images

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)

# Ensure the static directory and uploads directory exist
STATIC_DIR = "app/static"
UPLOAD_DIR = os.path.join(STATIC_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory="app/templates")

class ImagePayload(BaseModel):
    image: str
    height: float
    weight: float
    userId: int

class CollectDataPayload(BaseModel):
    side_image: str
    front_image: str
    height: float
    weight: float

@app.get("/", response_class=HTMLResponse)
async def form_get(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})

@app.post("/", response_class=HTMLResponse)
async def form_post(request: Request,
                    image: UploadFile = File(...),
                    height: float = Form(...),
                    weight: float = Form(...)):
    try:
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
async def process_image_api(payload: ImagePayload, request: Request):
    try:
        image = payload.image
        height = payload.height
        weight = payload.weight
        userId = payload.userId
        
        if not image or not height or not weight:
            return JSONResponse(status_code=400, content={"error": "Invalid input data"})
        # Check if image is a base64 string
        if not isinstance(image, str):
            return JSONResponse(status_code=400, content={"error": "Image must be a base64 string"})

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
        
        if(result["bmi_verified"] == True):
            logging.info(f"User {userId} BMI verified successfully.")
            try:
                api_response = requests.post(
                    "https://staging.mayfairweightlossclinic.co.uk/api/ImageVerify",
                    json={"user_id": userId, "status": True},
                    headers={"Content-Type": "application/json"},
                    timeout=5
                )
                api_response.raise_for_status()
                logging.info(f"Successfully called external API for user {userId}. Response: {api_response.json()}")
            except requests.RequestException as e:
                logging.error(f"Failed to call external API for user {userId}: {str(e)}")
        else:
            logging.warning(f"User {userId} BMI verification failed: {result['verification_result']}")

        return {
            "filename": filename,
            "bmi_result": result,
            "image_url": f"/static/uploads/{filename}"
        }

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    

@app.post("/collect-data")
async def collect_data_api(payload: CollectDataPayload, request: Request):
    try:
        side_image = payload.side_image
        front_image = payload.front_image
        height = payload.height
        weight = payload.weight
        
        if not side_image or not front_image or not height or not weight:
            return JSONResponse(status_code=400, content={"error": "Invalid input data"})
        # Check if image is a base64 string
        if not isinstance(side_image, str) or not isinstance(front_image, str):
            return JSONResponse(status_code=400, content={"error": "Images must be base64 strings"})

        if side_image.startswith("data:"):
            _, side_image = side_image.split(",", 1)
        if front_image.startswith("data:"):
            _, front_image = front_image.split(",", 1)

        # Decode base64 string
        side_image_data = base64.b64decode(side_image)
        front_image_data = base64.b64decode(front_image)
        # Save uploaded image
        side_filename = f"side_{uuid.uuid4().hex}.jpg"
        front_filename = f"front_{uuid.uuid4().hex}.jpg"
        side_path = os.path.join(UPLOAD_DIR, side_filename)
        front_path = os.path.join(UPLOAD_DIR, front_filename)
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        with open(side_path, "wb") as bf:
            bf.write(side_image_data)
        with open(front_path, "wb") as ff:
            ff.write(front_image_data)

        # Process image using your logic
        result = calculate_bmi_from_images(side_path, front_path, height, weight)

        # Return result
        if "error" in result:
            return JSONResponse(status_code=400, content={"error": result["error"]})

        return {
            "success": True,
        }

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})