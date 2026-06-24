from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from syllabus_parser import parse_syllabus
from classroom_uploader import (
    create_assignment,
    make_fingerprint,
    normalize_due_date,
)
from normalizer import normalize_item
from validator import validate_item
from google_auth import get_classroom_service
import pdfplumber
import io
import os
import sys
import threading
import webbrowser

print("SERVER STARTED")

app = FastAPI()


def get_runtime_base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def get_templates_dir():
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, "templates")
    return os.path.join(get_runtime_base_dir(), "templates")


templates = Jinja2Templates(directory=get_templates_dir())

service = get_classroom_service()


def fetch_courses():
    try:
        response = service.courses().list(pageSize=100).execute()
        courses = response.get("courses", [])
        courses = sorted(courses, key=lambda c: c.get("name", "").lower())
        return courses, None
    except Exception as e:
        return [], str(e)


def fetch_existing_fingerprints(course_id: str):
    fingerprints = set()
    page_token = None

    while True:
        response = service.courses().courseWork().list(
            courseId=course_id,
            pageToken=page_token,
            pageSize=100,
        ).execute()

        assignments = response.get("courseWork", [])

        for assignment in assignments:
            existing_title = assignment.get("title", "")
            due = assignment.get("dueDate")

            if due:
                existing_due = (
                    f"{due['year']}-"
                    f"{due['month']:02d}-"
                    f"{due['day']:02d}"
                )
            else:
                existing_due = ""

            fingerprints.add(make_fingerprint(existing_title, existing_due))

        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return fingerprints


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    courses, courses_error = fetch_courses()

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "courses": courses,
            "courses_error": courses_error,
        }
    )


@app.post("/preview", response_class=HTMLResponse)
async def preview(
    request: Request,
    file: UploadFile = File(...),
    course_id: str = Form(...),
    allow_openai: str | None = Form(None),
):
    print("PREVIEW ENDPOINT CALLED")

    pdf_bytes = await file.read()

    pdf_file = io.BytesIO(pdf_bytes)

    syllabus_text = ""

    with pdfplumber.open(pdf_file) as pdf:

        for page in pdf.pages:

            page_text = page.extract_text()

            if page_text:
                syllabus_text += page_text + "\n"


    print(syllabus_text[:2000])
    
    with open("debug_extracted_text.txt", "w", encoding="utf-8") as f:
        f.write(syllabus_text)
    
    openai_allowed = allow_openai == "yes"

    assignments = parse_syllabus(syllabus_text, allow_openai=openai_allowed)

    selected_course_name = ""
    courses, _ = fetch_courses()
    for course in courses:
        if str(course.get("id", "")) == str(course_id):
            selected_course_name = course.get("name", "")
            break

    return templates.TemplateResponse(
        "preview.html",
        {
            "request": request,
            "assignments": assignments,
            "course_id": course_id,
            "course_name": selected_course_name,
            "openai_allowed": openai_allowed,
        },
    )


@app.post("/upload", response_class=HTMLResponse)
async def upload(request: Request):
    form = await request.form()

    course_id = str(form.get("course_id", "")).strip()
    course_name = str(form.get("course_name", "")).strip()

    titles = form.getlist("title")
    descriptions = form.getlist("description")
    due_dates = form.getlist("due_date")

    edited_items = []
    for i in range(len(titles)):
        edited_items.append(
            {
                "title": str(titles[i]).strip(),
                "description": str(descriptions[i]).strip() if i < len(descriptions) else "",
                "due_date": str(due_dates[i]).strip() if i < len(due_dates) else "",
            }
        )

    report = {
        "course_name": course_name,
        "course_id": course_id,
        "attempted": 0,
        "uploaded": 0,
        "duplicates_skipped": 0,
        "failed": 0,
    }
    failed_items = []

    if not course_id:
        failed_items.append(
            {
                "item": {"title": "N/A", "due_date": "N/A"},
                "error": "Missing course selection.",
            }
        )
        report["failed"] = 1
        return templates.TemplateResponse(
            "upload_report.html",
            {
                "request": request,
                "report": report,
                "failed_items": failed_items,
            },
        )

    try:
        existing_fingerprints = fetch_existing_fingerprints(course_id)
    except Exception as e:
        failed_items.append(
            {
                "item": {"title": "N/A", "due_date": "N/A"},
                "error": f"Unable to read existing coursework for this class: {str(e)}",
            }
        )
        report["failed"] = 1
        return templates.TemplateResponse(
            "upload_report.html",
            {
                "request": request,
                "report": report,
                "failed_items": failed_items,
            },
        )

    for raw_item in edited_items:
        if not any(raw_item.values()):
            continue

        report["attempted"] += 1

        try:
            item = normalize_item(raw_item)
            validate_item(item)

            normalized_due = normalize_due_date(item["due_date"])
            fingerprint = make_fingerprint(item["title"], normalized_due)

            if fingerprint in existing_fingerprints:
                report["duplicates_skipped"] += 1
                continue

            create_assignment(
                service,
                course_id=course_id,
                title=item["title"],
                description=item["description"],
                due_date=item["due_date"],
            )

            existing_fingerprints.add(fingerprint)
            report["uploaded"] += 1

        except Exception as e:
            failed_items.append(
                {
                    "item": {
                        "title": raw_item.get("title") or "Untitled Assignment",
                        "due_date": raw_item.get("due_date") or "N/A",
                    },
                    "error": str(e),
                }
            )

    report["failed"] = len(failed_items)

    return templates.TemplateResponse(
        "upload_report.html",
        {
            "request": request,
            "report": report,
            "failed_items": failed_items,
        },
    )


if __name__ == "__main__":
    import uvicorn

    host = "127.0.0.1"
    port = 8000

    threading.Timer(1.5, lambda: webbrowser.open(f"http://{host}:{port}")).start()
    uvicorn.run(app, host=host, port=port)