#!/usr/bin/env python3
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Depends, Query, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn
import uuid
import os
import json
from datetime import datetime
import argparse
from pathlib import Path

# Parse command line arguments
parser = argparse.ArgumentParser(description='FastAPI Server for Web Content Capture')
parser.add_argument('--port', type=int, default=8000, help='Port to run the server on')
args = parser.parse_args()

# Create the FastAPI app
app = FastAPI(
    title="Web Content Capture API",
    description="API for capturing and storing web content",
    version="1.0.0",
)

# Add CORS middleware to allow requests from any origin (for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Models
class CaptureBase(BaseModel):
    """Base model for a web capture"""
    url: str = Field(..., description="URL of the captured page")
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp of the capture")
    hash: Optional[str] = Field(None, description="Content hash for deduplication")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class CaptureCreate(CaptureBase):
    """Model for creating a new capture"""
    pass


class Capture(CaptureBase):
    """Model for a capture with ID"""
    capture_id: str = Field(..., description="Unique identifier for the capture")
    html_path: Optional[str] = Field(None, description="Path to stored HTML content")
    screenshot_path: Optional[str] = Field(None, description="Path to screenshot")
    resources: List[Dict[str, Any]] = Field(default_factory=list, description="Captured resources")


# Set up storage directories
CAPTURES_DIR = Path(os.path.dirname(os.path.abspath(__file__))) / "data" / "captures"
CAPTURES_DIR.mkdir(parents=True, exist_ok=True)

# In-memory database for demo purposes
captures_db = {}

# File to persist captures between runs
CAPTURES_DB_FILE = CAPTURES_DIR / "captures_index.json"

# Load existing captures if available
if CAPTURES_DB_FILE.exists():
    try:
        with open(CAPTURES_DB_FILE, "r") as f:
            captures_db = json.load(f)
    except Exception as e:
        print(f"Error loading captures database: {e}")


# Helper function to save the captures database
def save_captures_db():
    try:
        with open(CAPTURES_DB_FILE, "w") as f:
            json.dump(captures_db, f, default=str)
    except Exception as e:
        print(f"Error saving captures database: {e}")


# API Routes
@app.get("/", include_in_schema=False)
async def root():
    """Redirect to docs"""
    return {"message": "Welcome to Web Content Capture API. Visit /docs for the API documentation."}


# Capture operations
@app.post("/captures/", response_model=Capture, tags=["Captures"])
async def create_capture(capture: CaptureCreate):
    """Create a new capture record"""
    capture_id = str(uuid.uuid4())
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")

    capture_data = Capture(
        capture_id=capture_id,
        url=capture.url,
        timestamp=capture.timestamp,
        hash=capture.hash,
        metadata=capture.metadata,
        html_path=None,
        screenshot_path=None,
        resources=[]
    )

    captures_db[capture_id] = capture_data.dict()
    save_captures_db()

    return capture_data


@app.get("/captures/", response_model=List[Capture], tags=["Captures"])
async def get_captures(
        url: Optional[str] = Query(None, description="Filter by URL")
):
    """Get all captures, optionally filtered by URL"""
    filtered_captures = list(captures_db.values())

    if url:
        filtered_captures = [c for c in filtered_captures if c["url"] == url]

    return filtered_captures


@app.get("/captures/{capture_id}", response_model=Capture, tags=["Captures"])
async def get_capture(capture_id: str):
    """Get a capture by its ID"""
    if capture_id not in captures_db:
        raise HTTPException(status_code=404, detail="Capture not found")

    return captures_db[capture_id]


@app.delete("/captures/{capture_id}", tags=["Captures"])
async def delete_capture(capture_id: str):
    """Delete a capture by its ID"""
    if capture_id not in captures_db:
        raise HTTPException(status_code=404, detail="Capture not found")

    del captures_db[capture_id]
    save_captures_db()

    return {"message": f"Capture {capture_id} deleted successfully"}


@app.post("/captures/{capture_id}/upload", tags=["Captures"])
async def upload_capture_content(
        capture_id: str,
        file_type: str = Query(..., description="Type of file (html, screenshot, resource)"),
        file: UploadFile = File(...),
):
    """Upload content for an existing capture"""
    if capture_id not in captures_db:
        raise HTTPException(status_code=404, detail="Capture not found")

    # Create directory for this capture
    capture_dir = CAPTURES_DIR / capture_id
    capture_dir.mkdir(exist_ok=True)

    # Save the uploaded file
    file_path = capture_dir / f"{file_type}_{file.filename}"

    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Update the capture record
    if file_type == "html":
        captures_db[capture_id]["html_path"] = str(file_path)
    elif file_type == "screenshot":
        captures_db[capture_id]["screenshot_path"] = str(file_path)
    elif file_type == "resource":
        if "resources" not in captures_db[capture_id]:
            captures_db[capture_id]["resources"] = []

        captures_db[capture_id]["resources"].append({
            "filename": file.filename,
            "path": str(file_path)
        })

    save_captures_db()

    return {"message": f"{file_type} uploaded successfully", "path": str(file_path)}


@app.get("/captures/{capture_id}/content", tags=["Captures"])
async def get_capture_content(
        capture_id: str,
        content_type: str = Query(..., description="Type of content to retrieve (html, screenshot)")
):
    """Get content for a capture"""
    if capture_id not in captures_db:
        raise HTTPException(status_code=404, detail="Capture not found")

    capture = captures_db[capture_id]

    if content_type == "html" and capture.get("html_path"):
        try:
            with open(capture["html_path"], "r", encoding="utf-8") as f:
                return {"content": f.read()}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error reading HTML content: {str(e)}")

    elif content_type == "screenshot" and capture.get("screenshot_path"):
        return {"image_path": capture["screenshot_path"]}

    else:
        raise HTTPException(status_code=404, detail=f"{content_type} content not found")


# Management operations
@app.post("/system/clear-all", tags=["System"])
async def clear_all_captures():
    """Clear all captures (for development/testing)"""
    captures_db.clear()
    save_captures_db()
    return {"message": "All captures cleared successfully"}


if __name__ == "__main__":
    print(f"Starting FastAPI server on port {args.port}")
    uvicorn.run(app, host="127.0.0.1", port=args.port)