import json

from normalizer import normalize_item
from validator import validate_item
from dateutil import parser
from datetime import datetime

from google_auth import get_classroom_service

service = get_classroom_service()


courses = service.courses().list().execute().get("courses", [])

for c in courses:
    print(c["id"], c["name"])
    
  
def create_assignment(service, course_id, title, description, due_date):
    
    today = datetime.now()

    parsed_date = parser.parse(
        f"{due_date} {today.year}"
    )

    # If parsed date already passed, assume next year
    if parsed_date.date() < today.date():
        parsed_date = parsed_date.replace(year=today.year + 1)
    
    print("Creating assignment:", title)
    
    
    coursework = {
        "title": title,
        "description": description,
        "workType": "ASSIGNMENT",
        "state": "PUBLISHED",
        "dueDate": {
            "year": parsed_date.year,
            "month": parsed_date.month,
            "day": parsed_date.day
        },
        "dueTime": {
            "hours": 23,
            "minutes": 59
        }
    }

    return service.courses().courseWork().create(
        courseId=course_id,
        body=coursework
    ).execute()
    
print("Assignment created successfully")
    
    
with open("firstrealsyllabus.json", "r", encoding="utf-8") as f:
    data = json.load(f)

service = get_classroom_service()

print("Starting uploader...")


failed_items = []

for i, raw_item in enumerate(data):

    try:
        print(f"\n--- Processing item {i+1} ---")

        # 1. Normalize AI output into clean structure
        item = normalize_item(raw_item)

        # 2. Validate required fields exist
        validate_item(item)

        # 3. Upload to Google Classroom
        print("Creating assignment:", item["title"])

        result = create_assignment(
            service,
            course_id=865977290508,
            title=item["title"],
            description=item["description"],
            due_date=item["due_date"]
        )

        print("SUCCESS:", result.get("id"))

    except Exception as e:
        print("FAILED ITEM:", raw_item)
        print("ERROR:", str(e))

        failed_items.append({
            "item": raw_item,
            "error": str(e)
        })


# BELOW is the way to get course ID do not delete

# service = get_classroom_service()

# courses = service.courses().list().execute().get("courses", [])

# print("\nAVAILABLE COURSES:\n")

# for c in courses:
#     print("Course Name:", c["name"])
#     print("Course ID:", c["id"])
#     print("-------------------")