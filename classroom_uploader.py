import os
import pickle
import json

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from dateutil import parser

SCOPES = [
    "https://www.googleapis.com/auth/classroom.courses",
    "https://www.googleapis.com/auth/classroom.coursework.students"
]

def get_service():
    creds = None

    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json",
                SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)

    return build("classroom", "v1", credentials=creds)

service = get_service()

courses = service.courses().list().execute().get("courses", [])

for c in courses:
    print(c["id"], c["name"])
    
  
    # took out description from this list for now
def create_assignment(service, course_id, title, description, due_date):
    # Convert flexible date string into parsed Python date
    parsed_date = parser.parse(due_date)
    
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

        # "dueDate": {
        #     "year": int(due_date[:4]),
        #     "month": int(due_date[5:7]),
        #     "day": int(due_date[8:10])
        # },
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
    
    
    
    
    

with open("parsed_syllabus.json", "r") as f:
    data = json.load(f)

service = get_service()

print("Starting uploader...")

print(data)

for item in data:
    create_assignment(
        service,
        course_id="793951654742",
        title=item["assignment_title"],
        description=item["description"],
        due_date=item["due_date"]
    )