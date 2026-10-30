"""
Web Application Runner.
Launches the FastAPI web application and REST API on http://localhost:8000.
"""

import sys
from pathlib import Path

WORKSPACE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(WORKSPACE_DIR))

import uvicorn

if __name__ == "__main__":
    # Ensure UTF-8 on Windows
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("=====================================================================")
    print("  🎓 YottaFlex AI Learning Workflow — End-to-End Web Application    ")
    print("  Web UI:       http://localhost:8000                                ")
    print("  API Docs:     http://localhost:8000/docs                           ")
    print("  OpenAPI Spec: http://localhost:8000/openapi.json                   ")
    print("=====================================================================")
    uvicorn.run("src.api:app", host="0.0.0.0", port=8000, reload=False)
