from openai import OpenAI
from dotenv import load_dotenv
import os
import json

# Load environment variables
load_dotenv()

# Get API key from environment
api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=api_key)


# Read syllabus file
with open("plumoutput.txt", "r", encoding="utf-8") as file:
    syllabus_text = file.read()

prompt = f"""
Extract structured course information from this syllabus.

Return ONLY valid JSON.

Format:
 [ 
 {{
        "course_name": "",
        "description": "",
        "teacher_name": ""
        }},
  {{
    "week": 1,
    "topic": "",
    "assignment_title": "",
    "description": "",
    "due_date": "YYYY-MM-DD",
    "materials": []
  }}
]

# [ this was for simple testing, but the actual output is more complex
#   {{
#     "week": 0,
#     "topic": "",
#     "reading": "",
#     "assignment_title": "",
#     "due_date": ""
#   }}
# ]

Syllabus:
{syllabus_text}
"""

response = client.chat.completions.create(
    model="gpt-4.1-mini",
    messages=[
        {"role": "user", "content": prompt}
    ]
)

output = response.choices[0].message.content

print(output)