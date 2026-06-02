from fastapi import FastAPI, UploadFile, File
from classroom_uploader import get_classroom_service
from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

app = FastAPI()

templates = Jinja2Templates(directory="templates")

service = get_classroom_service()

@app.post("/upload-syllabus")
async def upload_syllabus(file: UploadFile = File(...)):

    content = await file.read()

    # STEP 1: parse PDF/text (you already have this)
    text = content.decode("utf-8", errors="ignore")

    # STEP 2: AI processing (plug your OpenAI logic here)

    return {"message": "uploaded", "preview": []}

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/upload")
async def upload(file: UploadFile = File(...)):

    content = await file.read()

    text = content.decode("utf-8", errors="ignore")

    # later: PDF + AI pipeline
    return {"message": "file received"}