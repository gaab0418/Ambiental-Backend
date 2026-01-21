import logging
import time
import os
from pathlib import Path
from logging.handlers import RotatingFileHandler

# Setup paths
LOG_ROOT = Path(__file__).resolve().parent.parent / "logs"
LOG_ROOT.mkdir(parents=True, exist_ok=True)
TEST_LOG_FILE = LOG_ROOT / "test_rotation.log"

def verify_rotation():
    print(f"Testing rotation on: {TEST_LOG_FILE}")
    
    # Clean up previous tests
    for f in LOG_ROOT.glob("test_rotation.log*"):
        try:
           os.remove(f)
        except:
           pass

    # Configure small rotation limit (e.g., 1KB)
    MAX_BYTES = 1024  # 1 KB
    BACKUP_COUNT = 3
    
    logger = logging.getLogger("test_rotation_logger")
    logger.setLevel(logging.INFO)
    
    handler = RotatingFileHandler(
        TEST_LOG_FILE, 
        maxBytes=MAX_BYTES, 
        backupCount=BACKUP_COUNT, 
        encoding="utf-8"
    )
    logger.addHandler(handler)
    
    # Write enough data to trigger rotation
    print("Writing data to trigger rotation...")
    large_message = "x" * 100 # 100 bytes
    
    # Write 15 times -> 1500 bytes (should trigger rotation at 1024)
    for i in range(15):
        logger.info(f"Message {i}: {large_message}")
    
    # Close handlers to release file
    handler.close()
    logger.removeHandler(handler)
    
    # Check for rotated files
    rotated_file = LOG_ROOT / "test_rotation.log.1"
    if rotated_file.exists():
        print(f"✅ Rotation successful! Found {rotated_file}")
        print(f"Original file size: {TEST_LOG_FILE.stat().st_size} bytes")
        print(f"Rotated file size: {rotated_file.stat().st_size} bytes")
    else:
        print("❌ Rotation failed. Backup file not found.")
        print(f"Files found: {list(LOG_ROOT.glob('test_rotation.log*'))}")

if __name__ == "__main__":
    verify_rotation()
