import requests
import time
import json
from pathlib import Path

BASE_URL = "http://localhost:8000"
LOG_FILE = Path(__file__).resolve().parent.parent / "logs" / "requests.jsonl"

def verify_logging():
    print(f"Checking log file: {LOG_FILE}")
    
    # record file size or line count before request
    initial_lines = 0
    if LOG_FILE.exists():
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            initial_lines = sum(1 for _ in f)
    
    print(f"Initial log lines: {initial_lines}")
    
    # Make a request
    print(f"Making request to {BASE_URL}/status")
    try:
        resp = requests.get(f"{BASE_URL}/status")
        print(f"Response: {resp.status_code}")
    except Exception as e:
        print(f"Request failed: {e}")
        return

    # Wait a bit for log flush (requests.jsonl is written in threadpool/background)
    time.sleep(2)
    
    # Check log file again
    if not LOG_FILE.exists():
        print("❌ Log file does not exist!")
        return

    with open(LOG_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    final_lines = len(lines)
    print(f"Final log lines: {final_lines}")
    
    if final_lines > initial_lines:
        new_entry = json.loads(lines[-1])
        print("\n✅ New log entry found!")
        print(f"Method: {new_entry.get('method')}")
        print(f"URL: {new_entry.get('url')}")
        print(f"Duration: {new_entry.get('duration_ms')}ms")
        print(f"Direction: {new_entry.get('direction')}")
        
        # Verify content
        if new_entry.get('method') == 'GET' and '/status' in new_entry.get('url'):
            print("✅ Log entry matches request!")
        else:
            print("❌ Log entry content mismatch.")
    else:
        print("❌ No new log entry found.")

if __name__ == "__main__":
    verify_logging()
