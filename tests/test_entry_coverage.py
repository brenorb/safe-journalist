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

    def test_a_check_in_written_while_summarizing_reaches_the_next_summary(self) -> None:
        # CheckIns.tla EveryCheckInReachesAnAlert: the AI call takes time, and
        # the journalist can check in while it runs.
        with TemporaryDirectory() as tmpdir:
            storage.write_entry("arrived", tmpdir, storage.generate_timestamp())
            session = Mock(spec=MapleSession)

            def slow_call(**_):
                storage.write_entry("followed by a car", tmpdir, storage.generate_timestamp())
                return reply("first alert")

            with patch("safe_journalist.summarizer.encrypted_openai_call", side_effect=slow_call):
                summarizer.generate_summary(session=session, api_key="k", model="m", base_dir=tmpdir, client=MagicMock())

            self.assertEqual(storage.count_entries_since_last_summary(tmpdir), 1)
            with patch("safe_journalist.summarizer.encrypted_openai_call", return_value=reply("second alert")) as call:
                summarizer.generate_summary(session=session, api_key="k", model="m", base_dir=tmpdir, client=MagicMock())
            prompt = call.call_args.kwargs["payload"]["messages"][0]["content"]
            self.assertIn("followed by a car", prompt)
