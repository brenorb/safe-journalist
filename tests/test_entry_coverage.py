"""Replays of the CheckIns.tla rules on the real storage and summarizer."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import MagicMock, Mock, patch

from safe_journalist import storage, summarizer
from safe_journalist.session import MapleSession


def reply(text):
    return {"choices": [{"message": {"content": text}}]}


class TestEntryCoverage(TestCase):
    def test_two_check_ins_in_the_same_second_are_both_kept(self) -> None:
        with TemporaryDirectory() as tmpdir:
            first = storage.generate_timestamp()
            storage.write_entry("first check-in", tmpdir, first)
            second = storage.generate_timestamp()
            storage.write_entry("second check-in", tmpdir, second)
            texts = sorted(p.read_text(encoding="utf-8") for p in storage.list_entries(tmpdir))
            self.assertEqual(texts, ["first check-in", "second check-in"])

    def test_an_existing_check_in_is_never_overwritten(self) -> None:
        with TemporaryDirectory() as tmpdir:
            storage.write_entry("first check-in", tmpdir, "20260117T120000Z")
            with self.assertRaises(FileExistsError):
                storage.write_entry("second check-in", tmpdir, "20260117T120000Z")

