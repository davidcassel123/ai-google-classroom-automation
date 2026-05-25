from schema import SYLLABUS_ITEM_SCHEMA

def validate_item(item):

    for field in SYLLABUS_ITEM_SCHEMA["required"]:
        if field not in item or not item[field]:
            raise ValueError(f"Missing required field: {field}")

    return True