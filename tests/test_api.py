"""API liveness, task validation, and local persistence tests."""

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app


class ApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        root = Path(self.temporary_directory.name)
        settings = Settings(
            project_root=root,
            database_path=root / "db" / "test.sqlite3",
            upload_dir=root / "uploads",
            processed_dir=root / "processed",
            evidence_dir=root / "evidence",
            model_path=root / "weights.pt",
            lane_config_path=None,
        )
        self.client = TestClient(create_app(settings))

    def tearDown(self) -> None:
        self.client.close()
        self.temporary_directory.cleanup()

    def test_health_endpoint(self) -> None:
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_start_requires_an_uploaded_video(self) -> None:
        response = self.client.post("/api/detection/start", json={"video_id": "missing"})
        self.assertEqual(response.status_code, 404)

    def test_empty_statistics_are_database_derived(self) -> None:
        response = self.client.get("/api/statistics")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total_videos"], 0)
        self.assertEqual(response.json()["total_violations"], 0)
        self.assertEqual(response.json()["vehicle_types"], {})

    def test_upload_and_detection_failure_are_explicit_without_weights(self) -> None:
        upload = self.client.post(
            "/api/videos/upload",
            files={"file": ("sample.mp4", b"test video payload", "video/mp4")},
        )
        self.assertEqual(upload.status_code, 201)
        video_id = upload.json()["id"]
        videos = self.client.get("/api/videos").json()
        self.assertEqual(videos[0]["id"], video_id)

        started = self.client.post("/api/detection/start", json={"video_id": video_id})
        self.assertEqual(started.status_code, 202)
        task_id = started.json()["id"]

        status_response = self.client.get(f"/api/detection/{task_id}/status")
        self.assertEqual(status_response.json()["status"], "failed")
        self.assertIn("YOLO weights were not found", status_response.json()["error"])
        self.assertIsNone(status_response.json()["result"])

    def test_frontend_and_swagger_are_served(self) -> None:
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(self.client.get("/detection").status_code, 200)
        self.assertEqual(self.client.get("/docs").status_code, 200)
        self.assertEqual(self.client.get("/assets/js/api.js").status_code, 200)
        paths = self.client.get("/openapi.json").json()["paths"]
        required_paths = {
            "/api/health",
            "/api/videos/upload",
            "/api/videos",
            "/api/videos/{video_id}",
            "/api/detection/start",
            "/api/detection/{task_id}/status",
            "/api/detection/{task_id}/result",
            "/api/detection/{task_id}/video",
            "/api/violations",
            "/api/statistics",
        }
        self.assertTrue(required_paths.issubset(paths))


if __name__ == "__main__":
    unittest.main()
