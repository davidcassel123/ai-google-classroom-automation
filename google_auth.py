import os
import pickle

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# CENTRALIZED SCOPES
SCOPES = [
    "https://www.googleapis.com/auth/classroom.courses",
    "https://www.googleapis.com/auth/classroom.coursework.students"
]

SCOPES_VERSION = "v2"
TOKEN_FILE = f"token_{SCOPES_VERSION}.pickle"

def get_classroom_service():

    creds = None

    # Load existing token if it exists
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as token:
            creds = pickle.load(token)

    # If credentials missing or invalid
    if not creds or not creds.valid:

        # Try automatic refresh first
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired token...")
            creds.refresh(Request())

        else:
            # Token invalid OR scopes changed
            print("Performing fresh OAuth login...")

            # Delete stale token automatically
            if os.path.exists(TOKEN_FILE):
                os.remove(TOKEN_FILE)

            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json",
                SCOPES
            )

            creds = flow.run_local_server(port=0)

        # Save fresh token
        with open(TOKEN_FILE, "wb") as token:
            pickle.dump(creds, token)

    print("Authentication successful.")

    return build("classroom", "v1", credentials=creds)