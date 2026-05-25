def normalize_item(item):
    """
    Converts messy AI output into consistent structure.
    """

    return {
        "title": (
            item.get("assignment_title")
            or item.get("title")
            or "Untitled Assignment"
        ),

        "description": item.get("description", ""),

        "due_date": item.get("due_date", "1970-01-01"),

        "week": item.get("week"),
        "topic": item.get("topic"),
        "reading": item.get("reading"),
    }