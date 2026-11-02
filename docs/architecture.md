# System architecture

```text
Vanilla JS pages
      │ REST /api/*
      ▼
FastAPI routes ──► services ──► SQLite repository
                         │
                         └──► VideoProcessor
                                ├── YOLODetector
                                ├── VehicleTracker (Ultralytics ByteTrack)
                                ├── LaneDetector (configured polygons)
                                ├── WrongLaneDetector (configured transitions)
                                └── AlertManager (evidence images)
```

Video uploads and task metadata are stored locally. SQLite connections are short-lived and configured with foreign keys. Processing runs as an in-process FastAPI background task; it is suitable for a local/student application, not a distributed production queue. The API remains startable without YOLO weights because the model is loaded only when a task is run. Missing processing prerequisites are recorded as task failures.

Lane geometry is camera-specific. The lane detector only assigns image coordinates to configured polygons; YOLO does not infer lane boundaries. Wrong-lane decisions are based on explicitly configured forbidden lane transitions and a multi-frame confirmation threshold. They do not establish legal compliance without validated camera geometry and traffic rules.
