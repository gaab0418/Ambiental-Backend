"""
Helper to execute the project's pytest suite programmatically.

Captures stdout/stderr so failures can be logged for later analysis.
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List

from scripts.logger import StartupLogger


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def run_test_suite(pytest_args: List[str] | None = None) -> Dict[str, Any]:
    args = ["pytest"]
    if pytest_args:
        args.extend(pytest_args)
    else:
        args.append("-q")

    start = time.perf_counter()
    process = subprocess.run(
        args,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    duration = time.perf_counter() - start

    result = {
        "success": process.returncode == 0,
        "returncode": process.returncode,
        "stdout": process.stdout,
        "stderr": process.stderr,
        "duration_seconds": round(duration, 3),
    }

    log_details = {
        "returncode": process.returncode,
        "duration_seconds": result["duration_seconds"],
    }

    if result["success"]:
        StartupLogger.info("Testes executados com sucesso", log_name="tests", details=log_details)
    else:
        log_details["stdout"] = process.stdout
        log_details["stderr"] = process.stderr
        StartupLogger.error("Falha na suíte de testes", log_name="tests", details=log_details)

    return result


if __name__ == "__main__":
    outcome = run_test_suite()
    print(outcome)


