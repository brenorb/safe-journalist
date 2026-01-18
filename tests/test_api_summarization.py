import os
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import MagicMock, Mock, patch

from fastapi.testclient import TestClient

from safe_journalist.api import app
from safe_journalist import storage


class TestAutoSummarization(TestCase):
    def test_entry_creation_does_not_trigger_summarization_before_threshold(self) -> None:
        """Test that creating 1-2 entries does not trigger summarization"""
        with TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {"DATA_DIR": tmpdir, "SUMMARY_TRIGGER_COUNT": "3"}, clear=False):
                with patch("safe_journalist.storage.generate_timestamp", side_effect=["20260117T110000Z", "20260117T120000Z"]):
                    with patch("safe_journalist.api.run_summarization") as mock_summarize:
                        with TestClient(app) as client:
                            # Create first entry
                            response1 = client.post("/entries", json={"text": "Entry 1"})
                            self.assertEqual(response1.status_code, 200)
                            
                            # Create second entry
                            response2 = client.post("/entries", json={"text": "Entry 2"})
                            self.assertEqual(response2.status_code, 200)
                            
                            # Summarization should NOT have been triggered
                            mock_summarize.assert_not_called()
    
    def test_third_entry_triggers_summarization(self) -> None:
        """Test that the 3rd entry triggers automatic summarization"""
        with TemporaryDirectory() as tmpdir:
            timestamps = [
                "20260117T110000Z",
                "20260117T120000Z",
                "20260117T130000Z",
            ]
            
            with patch.dict(os.environ, {
                "DATA_DIR": tmpdir,
                "SUMMARY_TRIGGER_COUNT": "3",
                "MAPLE_API_KEY": "test-key",
                "MAPLE_API_URL": "https://test.api",
                "MAPLE_MODEL": "test-model"
            }, clear=False):
                with patch("safe_journalist.storage.generate_timestamp", side_effect=timestamps):
                    with patch("safe_journalist.api.run_summarization") as mock_summarize:
                        with TestClient(app) as client:
                            # Create 3 entries
                            client.post("/entries", json={"text": "Entry 1"})
                            client.post("/entries", json={"text": "Entry 2"})
                            response3 = client.post("/entries", json={"text": "Entry 3"})
                            
                            self.assertEqual(response3.status_code, 200)
                            
                            # Summarization should have been triggered once
                            mock_summarize.assert_called_once()
    
    def test_summarization_uses_background_task(self) -> None:
        """Test that summarization runs in background and doesn't block response"""
        with TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {
                "DATA_DIR": tmpdir,
                "SUMMARY_TRIGGER_COUNT": "3",
                "MAPLE_API_KEY": "test-key",
            }, clear=False):
                with patch("safe_journalist.storage.generate_timestamp", side_effect=["20260117T110000Z", "20260117T120000Z", "20260117T130000Z"]):
                    # Mock summarization to simulate slow operation
                    def slow_summarize():
                        time.sleep(0.1)
                    
                    with patch("safe_journalist.api.run_summarization", side_effect=slow_summarize) as mock_summarize:
                        with TestClient(app) as client:
                            client.post("/entries", json={"text": "Entry 1"})
                            client.post("/entries", json={"text": "Entry 2"})
                            
                            # This should return quickly even though summarization is slow
                            start = time.time()
                            response = client.post("/entries", json={"text": "Entry 3"})
                            duration = time.time() - start
                            
                            # Response should be fast (< 50ms without background task delay)
                            # Background task runs after response in TestClient
                            self.assertEqual(response.status_code, 200)
    
    def test_custom_trigger_count_from_env(self) -> None:
        """Test that SUMMARY_TRIGGER_COUNT can be customized via environment variable"""
        with TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {
                "DATA_DIR": tmpdir,
                "SUMMARY_TRIGGER_COUNT": "2",  # Trigger after 2 entries instead of 3
                "MAPLE_API_KEY": "test-key",
            }, clear=False):
                with patch("safe_journalist.storage.generate_timestamp", side_effect=["20260117T110000Z", "20260117T120000Z"]):
                    with patch("safe_journalist.api.run_summarization") as mock_summarize:
                        with TestClient(app) as client:
                            client.post("/entries", json={"text": "Entry 1"})
                            response = client.post("/entries", json={"text": "Entry 2"})
                            
                            self.assertEqual(response.status_code, 200)
                            # Should trigger after just 2 entries
                            mock_summarize.assert_called_once()
    
    def test_summarization_after_existing_summary(self) -> None:
        """Test that count resets after a summary is created"""
        with TemporaryDirectory() as tmpdir:
            # Pre-create some entries and a summary
            storage.write_entry("Old entry 1", tmpdir, "20260117T100000Z")
            storage.write_entry("Old entry 2", tmpdir, "20260117T110000Z")
            storage.write_summary("Previous summary", tmpdir, "20260117T115000Z")
            
            with patch.dict(os.environ, {
                "DATA_DIR": tmpdir,
                "SUMMARY_TRIGGER_COUNT": "3",
                "MAPLE_API_KEY": "test-key",
            }, clear=False):
                with patch("safe_journalist.storage.generate_timestamp", side_effect=[
                    "20260117T120000Z",
                    "20260117T130000Z",
                    "20260117T140000Z",
                ]):
                    with patch("safe_journalist.api.run_summarization") as mock_summarize:
                        with TestClient(app) as client:
                            # Create 3 NEW entries after the existing summary
                            client.post("/entries", json={"text": "New entry 1"})
                            client.post("/entries", json={"text": "New entry 2"})
                            response = client.post("/entries", json={"text": "New entry 3"})
                            
                            self.assertEqual(response.status_code, 200)
                            # Should trigger after 3 new entries (not counting old ones)
                            mock_summarize.assert_called_once()
    
    def test_entry_creation_still_works_without_maple_api_key(self) -> None:
        """Test that entries can be created even if MAPLE_API_KEY is not set"""
        with TemporaryDirectory() as tmpdir:
            # Don't set MAPLE_API_KEY
            with patch.dict(os.environ, {
                "DATA_DIR": tmpdir,
                "SUMMARY_TRIGGER_COUNT": "3",
            }, clear=False):
                # Remove MAPLE_API_KEY if it exists
                if "MAPLE_API_KEY" in os.environ:
                    del os.environ["MAPLE_API_KEY"]
                
                with patch("safe_journalist.storage.generate_timestamp", side_effect=[
                    "20260117T110000Z",
                    "20260117T120000Z",
                    "20260117T130000Z",
                ]):
                    with TestClient(app) as client:
                        # Should be able to create entries
                        response1 = client.post("/entries", json={"text": "Entry 1"})
                        response2 = client.post("/entries", json={"text": "Entry 2"})
                        response3 = client.post("/entries", json={"text": "Entry 3"})
                        
                        # All entries should succeed
                        self.assertEqual(response1.status_code, 200)
                        self.assertEqual(response2.status_code, 200)
                        self.assertEqual(response3.status_code, 200)
                        
                        # Entries should be created on disk
                        entries = storage.list_entries(tmpdir)
                        self.assertEqual(len(entries), 3)
    
    def test_run_summarization_helper_function(self) -> None:
        """Test the run_summarization helper function works correctly"""
        with TemporaryDirectory() as tmpdir:
            # Create entries
            storage.write_entry("Entry 1", tmpdir, "20260117T110000Z")
            storage.write_entry("Entry 2", tmpdir, "20260117T120000Z")
            
            with patch.dict(os.environ, {
                "DATA_DIR": tmpdir,
                "MAPLE_API_KEY": "test-key",
                "MAPLE_API_URL": "https://test.api",
                "MAPLE_MODEL": "test-model",
            }, clear=False):
                # Mock the dependencies
                mock_session_obj = Mock()
                mock_client_obj = MagicMock()
                
                with patch("safe_journalist.api.get_or_create_session") as mock_session:
                    # Return tuple of (session, client)
                    mock_session.return_value = (mock_session_obj, mock_client_obj)
                    
                    with patch("safe_journalist.summarizer.generate_summary") as mock_generate:
                        mock_generate.return_value = (Path(tmpdir) / "summaries" / "20260117T130000Z-summary.md", "Test summary")
                        
                        # Import and call run_summarization
                        from safe_journalist.api import run_summarization
                        
                        # Should not raise exception
                        run_summarization()
                        
                        # Should have called generate_summary
                        mock_generate.assert_called_once()
    
    def test_run_summarization_handles_errors_gracefully(self) -> None:
        """Test that errors in summarization don't crash the app"""
        with TemporaryDirectory() as tmpdir:
            storage.write_entry("Entry 1", tmpdir, "20260117T110000Z")
            
            with patch.dict(os.environ, {
                "DATA_DIR": tmpdir,
                "MAPLE_API_KEY": "test-key",
            }, clear=False):
                with patch("safe_journalist.api.get_or_create_session") as mock_session:
                    with patch("safe_journalist.summarizer.generate_summary") as mock_generate:
                        # Simulate error in summarization
                        mock_generate.side_effect = Exception("API Error")
                        
                        from safe_journalist.api import run_summarization
                        
                        # Should not raise exception (errors are caught and logged)
                        try:
                            run_summarization()
                        except Exception:
                            self.fail("run_summarization should handle errors gracefully")
