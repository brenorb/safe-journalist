from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi.testclient import TestClient

from safe_journalist import storage
from safe_journalist.api import app


def test_same_second_posts_preserve_both_entries(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("MAPLE_API_KEY", "")
    monkeypatch.setenv("SUMMARY_TRIGGER_COUNT", "99")
    monkeypatch.setattr(storage, "generate_timestamp", lambda: "20260117T123456Z")

    with TestClient(app) as client:
        first = client.post("/entries", json={"text": "Synthetic check-in A"})
        second = client.post("/entries", json={"text": "Synthetic check-in B"})
        assert first.status_code == second.status_code == 200
        assert first.json()["path"] != second.json()["path"]
        assert client.get("/status").json()["entries"] == 2
        recent = client.get("/entries").json()

    assert [entry["preview"] for entry in recent] == ["Synthetic check-in B", "Synthetic check-in A"]
    assert [entry["timestamp"] for entry in recent] == [second.json()["timestamp"], first.json()["timestamp"]]


def test_concurrent_entry_writes_do_not_overwrite(tmp_path: Path) -> None:
    entries = [f"Synthetic check-in {index}" for index in range(12)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        paths = list(pool.map(
            lambda text: storage.write_entry(text, str(tmp_path), "20260117T123456Z"),
            entries,
        ))

    assert len(set(paths)) == len(entries)
    assert [path.read_text(encoding="utf-8") for path in paths] == entries


def test_new_stamp_orders_with_legacy_entry_and_summary(tmp_path: Path) -> None:
    base_dir = str(tmp_path)
    timestamp = storage.generate_timestamp()
    second = timestamp.split(".", 1)[0]
    assert len(timestamp) > len(second)
    older = storage.write_entry("Legacy fixture", base_dir, second)
    storage.write_summary("Legacy summary", base_dir, second)
    newer = storage.write_entry("Precise fixture", base_dir, timestamp)

    assert storage.list_entries(base_dir) == [older, newer]
    assert storage.count_entries_since_last_summary(base_dir) == 1
