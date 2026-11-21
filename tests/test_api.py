"""API validation, persistence, and result endpoint tests."""

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app
from backend.models.violation import Violation


class ApiTests(unittest.TestCase):
    def setUp(self):
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

    def tearDown(self):
        self.client.close()
        self.temporary_directory.cleanup()

    def upload_video(self, filename="sample.mp4", payload=b"video payload"):
        response = self.client.post(
            "/api/videos/upload",
            files={"file": (filename, payload, "video/mp4")},
        )
        self.assertEqual(response.status_code, 201)
        return response.json()

    def test_health_endpoint(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_start_requires_an_uploaded_video(self):
        response = self.client.post(
            "/api/detection/start",
            json={"video_id": "missing"},
        )
        self.assertEqual(response.status_code, 404)

    def test_empty_statistics_are_database_derived(self):
        response = self.client.get("/api/statistics")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total_videos"], 0)
        self.assertEqual(response.json()["total_violations"], 0)
        self.assertEqual(response.json()["vehicle_types"], {})

    def test_upload_and_detection_failure_are_explicit_without_weights(self):
        video = self.upload_video()
        video_id = video["id"]

        videos = self.client.get("/api/videos").json()
        self.assertEqual(videos[0]["id"], video_id)

        started = self.client.post(
            "/api/detection/start",
            json={"video_id": video_id},
        )
        self.assertEqual(started.status_code, 202)
        task_id = started.json()["id"]

        response = self.client.get(f"/api/detection/{task_id}/status")
        self.assertEqual(response.status_code, 200)

        task = response.json()
        self.assertEqual(task["status"], "failed")
        self.assertIn("YOLO weights were not found", task["error"])
        self.assertIsNone(task["result"])

    def test_frontend_and_swagger_are_served(self):
        for path in (
            "/",
            "/detection",
            "/docs",
            "/assets/js/api.js",
        ):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

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

    def test_upload_roundtrip_persists_bytes_and_metadata(self):
        video = self.upload_video("SAMPLE.MP4", b"123456")

        response = self.client.get(f"/api/videos/{video['id']}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), video)
        self.assertEqual(video["size_bytes"], 6)

        repository = self.client.app.state.repository
        stored_path = repository.get_video_path(video["id"])
        self.assertEqual(stored_path.read_bytes(), b"123456")

        with TestClient(
            create_app(self.client.app.state.settings)
        ) as reopened:
            self.assertEqual(reopened.get("/api/videos").json(), [video])

    def test_invalid_uploads_leave_no_files_or_records(self):
        app = self.client.app
        app.state.settings = replace(
            app.state.settings,
            max_upload_bytes=4,
        )

        cases = [
            ("sample.txt", b"abc"),
            ("sample.mp4", b""),
            ("sample.mp4", b"12345"),
        ]

        for filename, payload in cases:
            with self.subTest(filename=filename, payload=payload):
                response = self.client.post(
                    "/api/videos/upload",
                    files={"file": (filename, payload, "video/mp4")},
                )
                self.assertEqual(response.status_code, 400)
                self.assertEqual(
                    self.client.get("/api/videos").json(),
                    [],
                )
                self.assertEqual(
                    list(app.state.settings.upload_dir.iterdir()),
                    [],
                )

    def test_unknown_resources_return_404(self):
        paths = [
            "/api/videos/missing",
            "/api/detection/missing/status",
            "/api/detection/missing/result",
            "/api/detection/missing/video",
        ]

        for path in paths:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 404)

    def test_request_validation(self):
        response = self.client.post("/api/detection/start", json={})
        self.assertEqual(response.status_code, 422)

        response = self.client.post("/api/videos/upload")
        self.assertEqual(response.status_code, 422)

        for limit in (0, 501, "invalid"):
            with self.subTest(limit=limit):
                response = self.client.get(
                    "/api/violations",
                    params={"limit": limit},
                )
                self.assertEqual(response.status_code, 422)

    def test_pending_and_failed_task_results(self):
        video = self.upload_video()
        repository = self.client.app.state.repository
        task = repository.create_task("pending", video["id"])

        response = self.client.get(f"/api/detection/{task.id}/result")
        self.assertEqual(response.status_code, 409)

        response = self.client.get(f"/api/detection/{task.id}/video")
        self.assertEqual(response.status_code, 404)

        repository.update_task(
            task.id,
            status="failed",
            error="Cannot decode video",
        )

        response = self.client.get(f"/api/detection/{task.id}/result")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["error"], "Cannot decode video")
        self.assertIsNone(response.json()["result"])

    def test_completed_result_video_violations_and_statistics(self):
        # Seed completed data to test API responses without running YOLO.
        video = self.upload_video()
        repository = self.client.app.state.repository
        task = repository.create_task("completed", video["id"])

        output = (
            self.client.app.state.settings.processed_dir / "completed.mp4"
        )
        output.write_bytes(b"processed video fixture")

        repository.save_violations(
            task.id,
            video["id"],
            [
                Violation(
                    track_id=7,
                    vehicle_type="truck",
                    source_lane="a",
                    destination_lane="b",
                    frame_index=20,
                    timestamp_seconds=1.0,
                )
            ],
        )

        repository.update_video_metrics(
            video["id"],
            processing_seconds=0.5,
            vehicle_type_counts={"car": 2},
            processed_frames=30,
            vehicle_count=2,
            violation_count=1,
        )

        repository.update_task(
            task.id,
            status="completed",
            progress=100,
            result={"violation_count": 1},
            output_path=output,
        )

        response = self.client.get(f"/api/detection/{task.id}/result")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["result"],
            {"violation_count": 1},
        )

        video_url = response.json()["video_url"]
        downloaded = self.client.get(video_url)
        self.assertEqual(downloaded.status_code, 200)
        self.assertEqual(downloaded.content, output.read_bytes())
        self.assertEqual(
            downloaded.headers["content-type"],
            "video/mp4",
        )

        violations = self.client.get("/api/violations?limit=1").json()
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["track_id"], 7)
        self.assertEqual(violations[0]["vehicle_type"], "truck")
        self.assertEqual(violations[0]["video_id"], video["id"])

        statistics = self.client.get("/api/statistics").json()
        self.assertEqual(
            statistics,
            {
                "total_videos": 1,
                "processed_videos": 1,
                "total_vehicles": 2,
                "total_violations": 1,
                "videos_with_violations": 1,
                "vehicle_types": {"car": 2},
                "detection_rate": 1.0,
            },
        )

        output.unlink()
        self.assertEqual(self.client.get(video_url).status_code, 404)


if __name__ == "__main__":
    unittest.main()