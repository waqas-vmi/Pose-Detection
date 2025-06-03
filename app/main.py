from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uuid
import shutil
import os
from app.process import calculate_bmi

app = FastAPI()
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")
UPLOAD_DIR = "app/static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

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
        with open(filename, "wb") as f:
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
