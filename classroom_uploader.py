import json
import re

from normalizer import normalize_item
from validator import validate_item
from dateutil import parser
from datetime import datetime

from google_auth import get_classroom_service


DATE_LIKE_PATTERNS = [
    r"\b\d{4}-\d{1,2}-\d{1,2}\b",
    r"\b\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b",
    r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+\d{1,2}(?:,\s*\d{4})?\b",
    r"\b\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\b",
]


def _clean_due_date_text(due_date):
    if due_date is None:
        return ""

    return str(due_date).strip()


def _looks_like_date(due_date_text):
    lowered = due_date_text.lower()
    return any(re.search(pattern, lowered) for pattern in DATE_LIKE_PATTERNS)


def _parse_due_date(due_date):
    due_date_text = _clean_due_date_text(due_date)

    if not due_date_text or not _looks_like_date(due_date_text):
        return None

    today = datetime.now()

    parse_candidates = [due_date_text]

    if not re.search(r"\b\d{4}\b", due_date_text):
        parse_candidates.append(f"{due_date_text} {today.year}")

    for candidate in parse_candidates:
        try:
            parsed_date = parser.parse(candidate, fuzzy=True)

            if not re.search(r"\b\d{4}\b", due_date_text) and parsed_date.date() < today.date():
                parsed_date = parsed_date.replace(year=today.year + 1)

            return parsed_date
        except (ValueError, TypeError):
            continue

    return None
    
  
def create_assignment(service, course_id, title, description, due_date):
    parsed_date = _parse_due_date(due_date)
    
    print("Creating assignment:", title)
    
    
    coursework = {
        "title": title,
        "description": description,
        "workType": "ASSIGNMENT",
        "state": "PUBLISHED",
    }

    if parsed_date:
        coursework["dueDate"] = {
            "year": parsed_date.year,
            "month": parsed_date.month,
            "day": parsed_date.day
        }
        coursework["dueTime"] = {
            "hours": 23,
            "minutes": 59
        }

    return service.courses().courseWork().create(
        courseId=course_id,
        body=coursework
    ).execute()
    
    
    
def assignment_exists(service, course_id, title, due_date):

    coursework = service.courses().courseWork().list(
        courseId=course_id
    ).execute()

    assignments = coursework.get("courseWork", [])

    for assignment in assignments:

        existing_title = assignment.get("title", "").strip()

        existing_due = assignment.get("dueDate")

        # Convert Google due date to comparable string
        if existing_due:
            existing_due_str = (
                f"{existing_due['year']}-"
                f"{existing_due['month']:02d}-"
                f"{existing_due['day']:02d}"
            )
        else:
            existing_due_str = ""

        if (
            existing_title.lower() == title.strip().lower()
            and existing_due_str == due_date
        ):
            return True

    return False
   
def normalize_text(text):
    return text.strip().lower()
   
def make_fingerprint(title, due_date):

    return (
        normalize_text(title),
        normalize_text(str(due_date))
    )
    
def normalize_due_date(due_date):
    parsed_date = _parse_due_date(due_date)

    if not parsed_date:
        return ""

    return parsed_date.strftime("%Y-%m-%d")


if __name__ == "__main__":
    with open("firstrealsyllabus.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    service = get_classroom_service()

    coursework = service.courses().courseWork().list(
        courseId=866843749172
    ).execute()

    existing_assignments = coursework.get("courseWork", [])

    existing_fingerprints = set()

    for assignment in existing_assignments:

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

        fp = make_fingerprint(existing_title, existing_due)

        existing_fingerprints.add(fp)

    print("Starting uploader...")

    failed_items = []

    for i, raw_item in enumerate(data):

        try:
            print(f"\n--- Processing item {i+1} ---")

            # 1. Normalize AI output into clean structure
            item = normalize_item(raw_item)

            # 2. Validate required fields exist
            validate_item(item)

            # 3. Check if assignment already exists to avoid duplicates
            normalized_due = normalize_due_date(item["due_date"])

            fingerprint = make_fingerprint(
                item["title"],
                normalized_due
            )

            if fingerprint in existing_fingerprints:
                print("SKIPPING DUPLICATE:", item["title"])
                continue

            # 4. Upload to Google Classroom
            print("Creating assignment:", item["title"])

            result = create_assignment(
                service,
                course_id=866843749172,
                title=item["title"],
                description=item["description"],
                due_date=item["due_date"]
            )

            print("SUCCESS:", result.get("id"))
            existing_fingerprints.add(fingerprint)

        except Exception as e:
            print("FAILED ITEM:", raw_item)
            print("ERROR:", str(e))

            failed_items.append({
                "item": raw_item,
                "error": str(e)
            })

    print("\nUPLOAD COMPLETE")
    print("Failed items:", len(failed_items))
    if failed_items:
        print("\nFAILED ITEMS:")
        for item in failed_items:
            print(item)

# BELOW is the way to get course ID do not delete

# service = get_classroom_service()

# courses = service.courses().list().execute().get("courses", [])

# print("\nAVAILABLE COURSES:\n")

# for c in courses:
#     print("Course Name:", c["name"])
#     print("Course ID:", c["id"])
#     print("-------------------")