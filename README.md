# ITS Wrong-Lane Detection

## Project Overview

ITS Wrong-Lane Detection is a student-friendly starter project for analyzing traffic videos with Python, FastAPI, OpenCV, and Ultralytics YOLO. It provides a REST API and a plain HTML/CSS/JavaScript dashboard for uploading videos, tracking processing tasks, and reviewing results.

This repository is a foundation, not a finished traffic-enforcement system. Vehicle detection requires a locally supplied YOLO weights file. Lane polygons and forbidden lane transitions must be configured for the camera view. No model weights, traffic videos, datasets, or measured results are included.

## Project Objectives

- Organize an extensible video-analysis backend into detector, tracker, lane, violation, service, and persistence modules.
- Provide validated API endpoints and persist uploaded videos, task state, and recorded violations in SQLite.
- Provide a browser dashboard for uploads, task progress, history, and statistics.
- Make unconfigured capabilities and failed processing tasks visible rather than presenting fabricated results.

## Technologies Used

- Python 3.10+
- FastAPI, Pydantic, and Uvicorn
- OpenCV and NumPy
- Ultralytics YOLO with its ByteTrack integration
- SQLite
- HTML5, CSS3, and vanilla JavaScript

## System Architecture

The browser calls the FastAPI REST API. API routes validate requests and delegate file handling and task orchestration to services. SQLite stores video, task, and violation metadata. A background task composes the YOLO detector, ByteTrack adapter, lane configuration, wrong-lane rule checker, and video processor. The dashboard reads persisted API data and polls task status.

The processing path is usable only when the dependencies, a local model weights file, and (for violation analysis) camera-specific lane/rule configuration are supplied. Without configured lanes, output is explicitly marked detection-only.

## Main Features

- Upload and list supported video files.
- Persist video metadata, detection task progress, and violation records.
- Start an asynchronous detection task and query its status and result.
- Lazy-load a local YOLO model and use Ultralytics' ByteTrack tracker.
- Configure lane polygons and forbidden lane transitions with a JSON file.
- Serve dashboard, detection, history, and statistics pages without a frontend framework.
- Return explicit task errors if processing prerequisites are unavailable.

## Project Structure

```text
backend/       FastAPI routes, processing modules, schemas, services, and SQLite
frontend/      Dashboard pages, stylesheets, and vanilla JavaScript
data/          Empty input, dataset, and sample-data directories
models/        Local model-weight directory and setup notes
storage/       Uploaded videos, processed videos, and evidence images
tests/         API, detection, tracking, and lane-rule tests
docs/          Architecture, API, algorithm, and development documentation
scripts/       Backend launcher and database initialization
```

See [docs/architecture.md](docs/architecture.md) and [docs/development_guide.md](docs/development_guide.md) for design and configuration details.

## Installation

1. Install Python 3.10 or later.
2. Create and activate a virtual environment:

   ```powershell
   py -3 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. Install dependencies:

   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. Copy `.env.example` to `.env` and set `ITS_MODEL_PATH` to an existing local Ultralytics-compatible weights file. The application does not download weights. For violation analysis, set `ITS_LANE_CONFIG` to a camera-specific JSON configuration; see `docs/algorithms.md`.

## Running the Application

From the project root:

```powershell
python scripts\setup_database.py
python scripts\run_backend.py
```

Open `http://127.0.0.1:8000/` for the dashboard and `http://127.0.0.1:8000/docs` for Swagger UI. The API health check is `GET /api/health`.

To run the unit tests:

```powershell
python -m unittest discover -s tests -v
```

## API Documentation

Interactive OpenAPI documentation is available at `/docs`; the OpenAPI schema is at `/openapi.json`. The API includes health, video upload/list/detail, detection start/status/result/video, violations, and statistics endpoints. Request and response models are documented in the schema.

## Team Development

- Keep camera-specific lane coordinates and traffic rules in configuration, not hard-coded assumptions.
- Do not commit `.env`, databases, uploaded/processed videos, datasets, or model weights.
- Add focused tests for new behavior and document algorithm limitations.
- Treat detection metrics as actual persisted results only; an unconfigured lane detector must not be reported as verified violation detection.
