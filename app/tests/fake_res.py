import json
import os
INPUT_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "tutto.json")

def load_data(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)
    

if __name__ == "__main__":
    data = load_data(INPUT_FILE)
    fake_res=[]
    for entry in data:
        fake_entry = {
            "issue_key": entry["issue_key"],
            "year": entry["year"],
            "month": entry["month"],
            "week_of_month": entry["week_of_month"],
            "true_points": entry.get("true_points", 0),
            "stimated_points": 3.0
        }
        fake_res.append(fake_entry)
    with open(os.path.join(os.path.dirname(__file__), "fake_res.json"), "w", encoding="utf-8") as f:
        json.dump(fake_res, f, indent=4, ensure_ascii=False)
