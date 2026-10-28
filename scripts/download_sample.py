"""Download the pinned public sample, verify its Git blob, and extract only SQLite."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "fff3df93beeee51a5444450891751f143e38da3e"
ARCHIVE_BYTES = 86721947
ARCHIVE_GIT_SHA = "b2c5b19033285d2361a20df94d36e3eb922b6a1a"
URL = ("https://raw.githubusercontent.com/giuseppedestefanis/gitskills-sample/"
       f"{COMMIT}/agent_skills_sample.zip")


def digest(path: Path, algorithm: str = "sha256", prefix: bytes = b"") -> str:
    result = hashlib.new(algorithm)
    result.update(prefix)
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def main() -> None:
    raw = ROOT / "data" / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    archive = raw / "agent_skills_sample.zip"
    if not archive.exists():
        partial = archive.with_suffix(".zip.part")
        print("Downloading pinned GitSkills sample (87 MB)...", flush=True)
        request = urllib.request.Request(URL, headers={"User-Agent": "dtu-02807-research"})
        with urllib.request.urlopen(request, timeout=60) as source, partial.open("wb") as target:
            shutil.copyfileobj(source, target, length=1024 * 1024)
        partial.rename(archive)
    blob_hash = digest(archive, "sha1", f"blob {ARCHIVE_BYTES}\0".encode())
    if archive.stat().st_size != ARCHIVE_BYTES or blob_hash != ARCHIVE_GIT_SHA:
        raise ValueError("Archive does not match the pinned Git blob; remove it and retry.")
    database = raw / "agent_skills_sample.db"
    with zipfile.ZipFile(archive) as source:
        databases = [item for item in source.infolist() if item.filename.endswith(".db")]
        if len(databases) != 1:
            raise ValueError("Expected exactly one SQLite database in the archive.")
        # Never extract archive paths or run any bundled skill scripts.
        with source.open(databases[0]) as stream, database.with_suffix(".db.part").open("wb") as target:
            shutil.copyfileobj(stream, target, length=1024 * 1024)
        database.with_suffix(".db.part").replace(database)
    with sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True) as connection:
        if connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise ValueError("SQLite integrity check failed.")
        count = connection.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0]
    manifest = {
        "dataset": "GitSkills July 2026 sample", "source_url": URL,
        "source_commit": COMMIT, "archive_git_blob_sha1": blob_hash,
        "archive_sha256": digest(archive), "archive_bytes": archive.stat().st_size,
        "database_sha256": digest(database), "database_bytes": database.stat().st_size,
        "artifact_rows": count,
    }
    (ROOT / "data" / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
