import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from fastapi.testclient import TestClient

from safe_journalist.api import app


class TestApi(TestCase):
    def test_post_text_writes_file(self) -> None:
        timestamp = "20260117T123456Z"

        with TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {"DATA_DIR": tmpdir}, clear=False):
                with patch("safe_journalist.storage.generate_timestamp", return_value=timestamp):
                    with TestClient(app) as client:
                        response = client.post("/entries", json={"text": "hello"})

                    self.assertEqual(response.status_code, 200)
                    payload = response.json()
                    # Updated to use new entry subdirectory structure
                    expected_path = str(Path(tmpdir) / "entries" / f"{timestamp}-entry.md")
                    self.assertEqual(payload["path"], expected_path)
                    self.assertEqual(payload["timestamp"], timestamp)
                    self.assertEqual(Path(expected_path).read_text(encoding="utf-8"), "hello")

    def test_missing_text_returns_4xx(self) -> None:
        with TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {"DATA_DIR": tmpdir}, clear=False):
                with TestClient(app) as client:
                    response = client.post("/entries", json={})

            self.assertGreaterEqual(response.status_code, 400)
            self.assertLess(response.status_code, 500)
            self.assertEqual(list(Path(tmpdir).glob("*")), [])

    def test_empty_text_returns_4xx(self) -> None:
        with TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {"DATA_DIR": tmpdir}, clear=False):
                with TestClient(app) as client:
                    response = client.post("/entries", json={"text": ""})

            self.assertGreaterEqual(response.status_code, 400)
            self.assertLess(response.status_code, 500)
            self.assertEqual(list(Path(tmpdir).glob("*")), [])

    def test_alert_returns_404_when_no_summary(self) -> None:
        """Test that /alert returns 404 when no summaries exist"""
        with TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {"DATA_DIR": tmpdir}, clear=False):
                with TestClient(app) as client:
                    response = client.get("/alert")

                self.assertEqual(response.status_code, 404)
                self.assertIn("No summary available", response.json()["detail"])

    def test_alert_returns_latest_summary(self) -> None:
        """Test that /alert returns the latest summary"""
        with TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {"DATA_DIR": tmpdir}, clear=False):
                # Create summaries directory and add test summaries
                summaries_dir = Path(tmpdir) / "summaries"
                summaries_dir.mkdir(parents=True)
                
                # Create two summaries (older and newer)
                older_timestamp = "20260117T120000Z"
                newer_timestamp = "20260117T130000Z"
                older_content = "Older summary content"
                newer_content = "Newer summary content"
                
                (summaries_dir / f"{older_timestamp}-summary.md").write_text(older_content)
                (summaries_dir / f"{newer_timestamp}-summary.md").write_text(newer_content)
                
                with TestClient(app) as client:
                    response = client.get("/alert")

                self.assertEqual(response.status_code, 200)
                payload = response.json()
                self.assertEqual(payload["summary"], newer_content)
                self.assertEqual(payload["timestamp"], newer_timestamp)
                self.assertEqual(
                    payload["path"],
                    str(summaries_dir / f"{newer_timestamp}-summary.md")
                )
