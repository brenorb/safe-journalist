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

    def test_get_entries_returns_empty_list_when_no_entries(self) -> None:
        """Test that GET /entries returns empty list when no entries exist"""
        with TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {"DATA_DIR": tmpdir}, clear=False):
                with TestClient(app) as client:
                    response = client.get("/entries")

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), [])

    def test_get_entries_returns_entries_newest_first(self) -> None:
        """Test that GET /entries returns entries sorted newest first"""
        with TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {"DATA_DIR": tmpdir}, clear=False):
                # Create entries directory and add test entries
                entries_dir = Path(tmpdir) / "entries"
                entries_dir.mkdir(parents=True)
                
                # Create three entries with different timestamps
                ts1 = "20260117T120000Z"
                ts2 = "20260117T130000Z"
                ts3 = "20260117T140000Z"
                content1 = "First entry content"
                content2 = "Second entry content"
                content3 = "Third entry content"
                
                (entries_dir / f"{ts1}-entry.md").write_text(content1)
                (entries_dir / f"{ts2}-entry.md").write_text(content2)
                (entries_dir / f"{ts3}-entry.md").write_text(content3)
                
                with TestClient(app) as client:
                    response = client.get("/entries")

                self.assertEqual(response.status_code, 200)
                entries = response.json()
                
                # Should return newest first
                self.assertEqual(len(entries), 3)
                self.assertEqual(entries[0]["timestamp"], ts3)
                self.assertEqual(entries[1]["timestamp"], ts2)
                self.assertEqual(entries[2]["timestamp"], ts1)
                
                # Check content previews
                self.assertEqual(entries[0]["preview"], content3)
                self.assertEqual(entries[1]["preview"], content2)
                self.assertEqual(entries[2]["preview"], content1)

    def test_get_entries_respects_limit_parameter(self) -> None:
        """Test that GET /entries respects the limit query parameter"""
        with TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {"DATA_DIR": tmpdir}, clear=False):
                # Create entries directory and add test entries
                entries_dir = Path(tmpdir) / "entries"
                entries_dir.mkdir(parents=True)
                
                # Create 5 entries
                for i in range(5):
                    ts = f"2026011712{i:02d}00Z"
                    (entries_dir / f"{ts}-entry.md").write_text(f"Entry {i}")
                
                with TestClient(app) as client:
                    response = client.get("/entries?limit=2")

                self.assertEqual(response.status_code, 200)
                entries = response.json()
                self.assertEqual(len(entries), 2)

    def test_get_entries_truncates_preview_at_200_chars(self) -> None:
        """Test that GET /entries truncates preview at 200 characters"""
        with TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {"DATA_DIR": tmpdir}, clear=False):
                # Create entries directory with long content
                entries_dir = Path(tmpdir) / "entries"
                entries_dir.mkdir(parents=True)
                
                ts = "20260117T120000Z"
                long_content = "x" * 300  # 300 characters
                (entries_dir / f"{ts}-entry.md").write_text(long_content)
                
                with TestClient(app) as client:
                    response = client.get("/entries")

                self.assertEqual(response.status_code, 200)
                entries = response.json()
                self.assertEqual(len(entries), 1)
                self.assertEqual(entries[0]["preview"], "x" * 200)
                self.assertEqual(len(entries[0]["preview"]), 200)

    def test_get_entries_validates_limit_parameter(self) -> None:
        """Test that GET /entries validates limit parameter"""
        with TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {"DATA_DIR": tmpdir}, clear=False):
                with TestClient(app) as client:
                    # Test negative limit
                    response = client.get("/entries?limit=-1")
                    self.assertEqual(response.status_code, 400)
                    
                    # Test zero limit
                    response = client.get("/entries?limit=0")
                    self.assertEqual(response.status_code, 400)
                    
                    # Test excessive limit
                    response = client.get("/entries?limit=1000")
                    self.assertEqual(response.status_code, 400)
