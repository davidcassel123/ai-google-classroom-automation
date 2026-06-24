import os
import pickle
import sys

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


def get_runtime_base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def get_credentials_path():
    return os.path.join(get_runtime_base_dir(), "credentials.json")


def get_token_path():
    return os.path.join(get_runtime_base_dir(), TOKEN_FILE)

def get_classroom_service():

    creds = None
    token_path = get_token_path()

    # Load existing token if it exists
    if os.path.exists(token_path):
        with open(token_path, "rb") as token:
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
            if os.path.exists(token_path):
                os.remove(token_path)

            flow = InstalledAppFlow.from_client_secrets_file(
                get_credentials_path(),
                SCOPES
            )

            creds = flow.run_local_server(port=0)

        # Save fresh token
        with open(token_path, "wb") as token:
            pickle.dump(creds, token)

    print("Authentication successful.")

    return build("classroom", "v1", credentials=creds)