import json
from datetime import datetime

def save_failed_items(failed_items):

    with open("failed_log.json", "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": str(datetime.now()),
            "failed_items": failed_items
        }, f, indent=2, ensure_ascii=False)
        
        if failed_items:
            save_failed_items(failed_items)
            print("Some items failed. Saved to failed_log.json")
        
