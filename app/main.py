from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import uuid
import shutil
import os
from app.process import calculate_bmi

app = FastAPI()
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
        filename = f"temp_{uuid.uuid4().hex}.jpg"
        with open(filename, "wb") as f:
            shutil.copyfileobj(image.file, f)

        # Use your logic from process.py
        result = calculate_bmi(filename, height, weight)
        os.remove(filename)

        if "error" in result:
            return templates.TemplateResponse("upload.html", {
                "request": request,
                "error": result["error"]
            })

        return templates.TemplateResponse("upload.html", {
            "request": request,
            "result": result
        })

    except Exception as e:
        return templates.TemplateResponse("upload.html", {
            "request": request,
            "error": str(e)
        })
