import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from safe_journalist import storage


class TestStorageRefactor(TestCase):
    def test_write_entry_creates_entry_file(self) -> None:
        """Test that write_entry creates files in /entries subdirectory"""
        with TemporaryDirectory() as tmpdir:
            timestamp = "20260117T123456Z"
            text = "Test entry content"
            
            path = storage.write_entry(text, tmpdir, timestamp)
            
            expected_path = Path(tmpdir) / "entries" / f"{timestamp}-entry.md"
            self.assertEqual(path, expected_path)
            self.assertTrue(path.exists())
            self.assertEqual(path.read_text(encoding="utf-8"), text)
    
    def test_write_summary_creates_summary_file(self) -> None:
        """Test that write_summary creates files in /summaries subdirectory"""
        with TemporaryDirectory() as tmpdir:
            timestamp = "20260117T130000Z"
            summary = "Test summary content"
            
            path = storage.write_summary(summary, tmpdir, timestamp)
            
            expected_path = Path(tmpdir) / "summaries" / f"{timestamp}-summary.md"
            self.assertEqual(path, expected_path)
            self.assertTrue(path.exists())
            self.assertEqual(path.read_text(encoding="utf-8"), summary)
    
    def test_list_entries_returns_sorted_entries(self) -> None:
        """Test that list_entries returns entries sorted by timestamp"""
        with TemporaryDirectory() as tmpdir:
            # Create entries in non-chronological order
            storage.write_entry("Third", tmpdir, "20260117T130000Z")
            storage.write_entry("First", tmpdir, "20260117T110000Z")
            storage.write_entry("Second", tmpdir, "20260117T120000Z")
            
            entries = storage.list_entries(tmpdir)
            
            self.assertEqual(len(entries), 3)
            # Should be sorted by timestamp (oldest to newest)
            self.assertTrue(str(entries[0]).endswith("20260117T110000Z-entry.md"))
            self.assertTrue(str(entries[1]).endswith("20260117T120000Z-entry.md"))
            self.assertTrue(str(entries[2]).endswith("20260117T130000Z-entry.md"))
    
    def test_list_entries_returns_empty_when_no_entries(self) -> None:
        """Test that list_entries returns empty list when no entries exist"""
        with TemporaryDirectory() as tmpdir:
            entries = storage.list_entries(tmpdir)
            self.assertEqual(entries, [])
    
    def test_list_summaries_returns_sorted_summaries(self) -> None:
        """Test that list_summaries returns summaries sorted by timestamp"""
        with TemporaryDirectory() as tmpdir:
            # Create summaries in non-chronological order
            storage.write_summary("Third", tmpdir, "20260117T130000Z")
            storage.write_summary("First", tmpdir, "20260117T110000Z")
            storage.write_summary("Second", tmpdir, "20260117T120000Z")
            
            summaries = storage.list_summaries(tmpdir)
            
            self.assertEqual(len(summaries), 3)
            # Should be sorted by timestamp (oldest to newest)
            self.assertTrue(str(summaries[0]).endswith("20260117T110000Z-summary.md"))
            self.assertTrue(str(summaries[1]).endswith("20260117T120000Z-summary.md"))
            self.assertTrue(str(summaries[2]).endswith("20260117T130000Z-summary.md"))
    
    def test_get_latest_summary_returns_most_recent(self) -> None:
        """Test that get_latest_summary returns the most recent summary"""
        with TemporaryDirectory() as tmpdir:
            storage.write_summary("First summary", tmpdir, "20260117T110000Z")
            storage.write_summary("Latest summary", tmpdir, "20260117T130000Z")
            storage.write_summary("Middle summary", tmpdir, "20260117T120000Z")
            
            path, content = storage.get_latest_summary(tmpdir)
            
            self.assertTrue(str(path).endswith("20260117T130000Z-summary.md"))
            self.assertEqual(content, "Latest summary")
    
    def test_get_latest_summary_returns_none_when_no_summaries(self) -> None:
        """Test that get_latest_summary returns None when no summaries exist"""
        with TemporaryDirectory() as tmpdir:
            result = storage.get_latest_summary(tmpdir)
            self.assertIsNone(result)
    
    def test_count_entries_since_last_summary_with_no_summaries(self) -> None:
        """Test counting entries when no summaries exist (should count all)"""
        with TemporaryDirectory() as tmpdir:
            storage.write_entry("Entry 1", tmpdir, "20260117T110000Z")
            storage.write_entry("Entry 2", tmpdir, "20260117T120000Z")
            storage.write_entry("Entry 3", tmpdir, "20260117T130000Z")
            
            count = storage.count_entries_since_last_summary(tmpdir)
            
            self.assertEqual(count, 3)
    
    def test_count_entries_since_last_summary_with_existing_summary(self) -> None:
        """Test counting only entries newer than the latest summary"""
        with TemporaryDirectory() as tmpdir:
            # Old entries (before summary)
            storage.write_entry("Old entry 1", tmpdir, "20260117T110000Z")
            storage.write_entry("Old entry 2", tmpdir, "20260117T120000Z")
            
            # Summary
            storage.write_summary("Summary", tmpdir, "20260117T125000Z")
            
            # New entries (after summary)
            storage.write_entry("New entry 1", tmpdir, "20260117T130000Z")
            storage.write_entry("New entry 2", tmpdir, "20260117T140000Z")
            
            count = storage.count_entries_since_last_summary(tmpdir)
            
            self.assertEqual(count, 2)
    
    def test_count_entries_since_last_summary_returns_zero(self) -> None:
        """Test that count returns 0 when no new entries after summary"""
        with TemporaryDirectory() as tmpdir:
            storage.write_entry("Entry", tmpdir, "20260117T110000Z")
            storage.write_summary("Summary", tmpdir, "20260117T120000Z")
            
            count = storage.count_entries_since_last_summary(tmpdir)
            
            self.assertEqual(count, 0)
