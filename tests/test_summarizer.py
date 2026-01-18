import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import MagicMock, Mock, patch

from safe_journalist import storage, summarizer
from safe_journalist.session import MapleSession


class TestSummarizer(TestCase):
    def test_generate_summary_with_no_previous_summary(self) -> None:
        """Test generating first summary with all entries"""
        with TemporaryDirectory() as tmpdir:
            # Create some entries
            storage.write_entry("Entry 1: Arrived at location", tmpdir, "20260117T110000Z")
            storage.write_entry("Entry 2: Met with source", tmpdir, "20260117T120000Z")
            storage.write_entry("Entry 3: Situation escalating", tmpdir, "20260117T130000Z")
            
            # Mock session and client
            mock_session = Mock(spec=MapleSession)
            mock_session.api_url = "https://test.api"
            mock_session.session_id = "test-session"
            mock_session.session_key = b"test-key-32-bytes-long-xxxxxxxx"
            
            mock_client = MagicMock()
            
            # Mock the encrypted_openai_call to return a summary
            with patch("safe_journalist.summarizer.encrypted_openai_call") as mock_call:
                mock_call.return_value = {
                    "choices": [{
                        "message": {
                            "content": "• Journalist arrived at location\n• Met with confidential source\n• Situation becoming dangerous"
                        }
                    }]
                }
                
                with patch("safe_journalist.storage.generate_timestamp", return_value="20260117T140000Z"):
                    summary_path, summary_content = summarizer.generate_summary(
                        session=mock_session,
                        api_key="test-key",
                        model="test-model",
                        base_dir=tmpdir,
                        client=mock_client
                    )
            
            # Verify summary was created
            self.assertTrue(summary_path.exists())
            self.assertTrue(str(summary_path).endswith("20260117T140000Z-summary.md"))
            self.assertIn("Journalist arrived", summary_content)
            
            # Verify the prompt included all entries and no previous summary
            call_args = mock_call.call_args
            prompt = call_args.kwargs["payload"]["messages"][0]["content"]
            self.assertIn("Entry 1: Arrived at location", prompt)
            self.assertIn("Entry 2: Met with source", prompt)
            self.assertIn("Entry 3: Situation escalating", prompt)
            self.assertNotIn("Previous summary:", prompt)
    
    def test_generate_summary_with_previous_summary(self) -> None:
        """Test generating summary with previous summary and new entries"""
        with TemporaryDirectory() as tmpdir:
            # Create old entries and summary
            storage.write_entry("Old entry 1", tmpdir, "20260117T110000Z")
            storage.write_entry("Old entry 2", tmpdir, "20260117T120000Z")
            storage.write_summary("Previous summary content", tmpdir, "20260117T125000Z")
            
            # Create new entries after summary
            storage.write_entry("New entry 1: Update", tmpdir, "20260117T130000Z")
            storage.write_entry("New entry 2: Critical", tmpdir, "20260117T140000Z")
            
            # Mock session and client
            mock_session = Mock(spec=MapleSession)
            mock_session.api_url = "https://test.api"
            mock_session.session_id = "test-session"
            mock_session.session_key = b"test-key-32-bytes-long-xxxxxxxx"
            
            mock_client = MagicMock()
            
            # Mock the encrypted_openai_call
            with patch("safe_journalist.summarizer.encrypted_openai_call") as mock_call:
                mock_call.return_value = {
                    "choices": [{
                        "message": {
                            "content": "Updated summary with new information"
                        }
                    }]
                }
                
                with patch("safe_journalist.storage.generate_timestamp", return_value="20260117T150000Z"):
                    summary_path, summary_content = summarizer.generate_summary(
                        session=mock_session,
                        api_key="test-key",
                        model="test-model",
                        base_dir=tmpdir,
                        client=mock_client
                    )
            
            # Verify new summary was created
            self.assertTrue(summary_path.exists())
            self.assertTrue(str(summary_path).endswith("20260117T150000Z-summary.md"))
            
            # Verify prompt included previous summary and only new entries
            call_args = mock_call.call_args
            prompt = call_args.kwargs["payload"]["messages"][0]["content"]
            self.assertIn("Previous summary:", prompt)
            self.assertIn("Previous summary content", prompt)
            self.assertIn("New entry 1: Update", prompt)
            self.assertIn("New entry 2: Critical", prompt)
            # Old entries should NOT be in prompt (already summarized)
            self.assertNotIn("Old entry 1", prompt)
            self.assertNotIn("Old entry 2", prompt)
    
    def test_generate_summary_with_no_entries(self) -> None:
        """Test that generating summary with no entries returns early"""
        with TemporaryDirectory() as tmpdir:
            mock_session = Mock(spec=MapleSession)
            mock_client = MagicMock()
            
            # Should return None when no entries exist
            result = summarizer.generate_summary(
                session=mock_session,
                api_key="test-key",
                model="test-model",
                base_dir=tmpdir,
                client=mock_client
            )
            
            self.assertIsNone(result)
    
    def test_generate_summary_constructs_correct_prompt_format(self) -> None:
        """Test that the prompt is formatted correctly for the AI"""
        with TemporaryDirectory() as tmpdir:
            storage.write_entry("Test entry", tmpdir, "20260117T120000Z")
            
            mock_session = Mock(spec=MapleSession)
            mock_session.api_url = "https://test.api"
            mock_session.session_id = "test-session"
            mock_session.session_key = b"test-key-32-bytes-long-xxxxxxxx"
            
            mock_client = MagicMock()
            
            with patch("safe_journalist.summarizer.encrypted_openai_call") as mock_call:
                mock_call.return_value = {
                    "choices": [{"message": {"content": "Summary"}}]
                }
                
                with patch("safe_journalist.storage.generate_timestamp", return_value="20260117T130000Z"):
                    summarizer.generate_summary(
                        session=mock_session,
                        api_key="test-key",
                        model="test-model",
                        base_dir=tmpdir,
                        client=mock_client
                    )
                
                # Verify API call structure
                call_args = mock_call.call_args
                self.assertEqual(call_args.kwargs["session"], mock_session)
                self.assertEqual(call_args.kwargs["api_key"], "test-key")
                self.assertEqual(call_args.kwargs["path"], "/v1/chat/completions")
                
                payload = call_args.kwargs["payload"]
                self.assertEqual(payload["model"], "test-model")
                self.assertFalse(payload["stream"])
                self.assertEqual(len(payload["messages"]), 1)
                self.assertEqual(payload["messages"][0]["role"], "user")
                
                # Verify prompt contains key phrases
                prompt = payload["messages"][0]["content"]
                self.assertIn("actionable information", prompt)
                self.assertIn("emergency contacts", prompt)
    
    def test_generate_summary_handles_errors(self) -> None:
        """Test that errors are handled gracefully"""
        with TemporaryDirectory() as tmpdir:
            storage.write_entry("Test entry", tmpdir, "20260117T120000Z")
            
            mock_session = Mock(spec=MapleSession)
            mock_session.api_url = "https://test.api"
            mock_session.session_id = "test-session"
            mock_session.session_key = b"test-key-32-bytes-long-xxxxxxxx"
            
            mock_client = MagicMock()
            
            # Mock API call to raise an exception
            with patch("safe_journalist.summarizer.encrypted_openai_call") as mock_call:
                mock_call.side_effect = Exception("API Error")
                
                # Should raise exception (will be caught by caller)
                with self.assertRaises(Exception) as context:
                    summarizer.generate_summary(
                        session=mock_session,
                        api_key="test-key",
                        model="test-model",
                        base_dir=tmpdir,
                        client=mock_client
                    )
                
                self.assertIn("API Error", str(context.exception))
