
import os
import json
import re
import sys
from urllib import error, request

from dotenv import load_dotenv
from openai import OpenAI


def get_runtime_base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


load_dotenv(os.path.join(get_runtime_base_dir(), ".env"))

api_key = os.getenv("OPENAI_API_KEY")
model_provider = os.getenv("MODEL_PROVIDER", "openai").strip().lower()
openai_model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip()
ollama_model = os.getenv("OLLAMA_MODEL", "qwen2.5:7b").strip()
ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
default_allow_openai = os.getenv("ALLOW_OPENAI_FALLBACK", "true").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

client = OpenAI(api_key=api_key) if api_key else None


def split_grouped_assignments(assignments):
    split_items = []

    for item in assignments:
        title = str(item.get("title", "")).strip()
        description = str(item.get("description", "")).strip()
        due_date = item.get("due_date", "")
        materials = item.get("materials", []) or []

        material_parts = [str(part).strip() for part in materials if str(part).strip()]

        if len(material_parts) > 1:
            for part in material_parts:
                split_items.append(
                    {
                        "title": part,
                        "description": part,
                        "due_date": due_date,
                        "materials": [part],
                    }
                )
            continue

        should_split_description = "reading" in title.lower() or "readings" in description.lower()

        if should_split_description:
            description_parts = []

            for raw_part in re.split(r"[\n;]+", description):
                cleaned = re.sub(r"^[\-\*\u2022\d\.)\s]+", "", raw_part).strip()
                if len(cleaned) >= 4:
                    description_parts.append(cleaned)

            unique_parts = []
            seen = set()
            for part in description_parts:
                lowered = part.lower()
                if lowered not in seen:
                    seen.add(lowered)
                    unique_parts.append(part)

            if len(unique_parts) > 1:
                for part in unique_parts:
                    split_items.append(
                        {
                            "title": part,
                            "description": part,
                            "due_date": due_date,
                            "materials": [part],
                        }
                    )
                continue

        split_items.append(item)

    return split_items


def build_prompt(syllabus_text):
    return f"""
Extract ALL assignments, quizzes, exams, projects,
papers, readings, discussions, and due dates.

If a schedule table exists, interpret the rows
and convert them into structured assignments.

Important extraction rules:
- Split grouped items into separate assignments whenever possible.
- If a weekly schedule row lists multiple readings, create one assignment per reading.
- Do not combine several readings into a single item called "Weekly Readings" unless the syllabus truly provides no separate titles.
- Prefer more, smaller assignments over fewer grouped assignments.
- If a row has both a reading and a graded task, return them as separate assignments when they are distinct pieces of work.
- Keep titles specific. Use the actual reading title, chapter, article, or task name when available.
- If no clear due date exists for an item, leave due_date as an empty string rather than guessing.

Return a JSON object with this exact structure:

{{
    "course_info": {{
        "course_name": "",
        "description": "",
        "teacher_name": ""
    }},
    "assignments": [
        {{
            "title": "",
            "description": "",
            "due_date": "",
            "materials": []
        }}
    ]
}}

If no assignments are found, return an empty
assignments array.

Return valid JSON only. Do not wrap it in markdown fences.

Syllabus:
{syllabus_text}
"""


def extract_json_text(raw_text):
    cleaned = str(raw_text).strip()

    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    start = cleaned.find("{")
    end = cleaned.rfind("}")

    if start != -1 and end != -1 and end >= start:
        return cleaned[start:end + 1]

    return cleaned


def parse_response_payload(output, provider_name):
    json_text = extract_json_text(output)

    print(f"\n===== {provider_name.upper()} OUTPUT =====")
    print(output)
    print("=========================\n")

    parsed = json.loads(json_text)
    assignments = parsed.get("assignments", [])
    return split_grouped_assignments(assignments)


def parse_with_openai(prompt):
    if not client:
        raise RuntimeError("OPENAI_API_KEY is not set.")

    response = client.chat.completions.create(
        model=openai_model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    output = response.choices[0].message.content
    return parse_response_payload(output, "openai")


def parse_with_ollama(prompt):
    payload = {
        "model": ollama_model,
        "stream": False,
        "format": "json",
        "messages": [
            {"role": "user", "content": prompt}
        ],
    }

    req = request.Request(
        f"{ollama_base_url}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=900) as response:
            body = json.loads(response.read().decode("utf-8"))
    except error.URLError as exc:
        raise RuntimeError(f"Unable to reach Ollama at {ollama_base_url}: {exc}") from exc

    message = body.get("message", {})
    output = message.get("content", "")

    if not output:
        raise RuntimeError("Ollama returned an empty response.")

    return parse_response_payload(output, "ollama")


def parse_syllabus(syllabus_text, allow_openai=None):
    prompt = build_prompt(syllabus_text)
    openai_allowed = default_allow_openai if allow_openai is None else bool(allow_openai)

    if model_provider == "ollama":
        try:
            return parse_with_ollama(prompt)
        except Exception as exc:
            if openai_allowed and client:
                print(f"Ollama parsing failed, falling back to OpenAI: {exc}")
                return parse_with_openai(prompt)
            raise

    if not openai_allowed:
        return parse_with_ollama(prompt)

    return parse_with_openai(prompt)


if __name__ == "__main__":

    data = parse_syllabus("plumoutput.txt")

    print(json.dumps(data, indent=2))