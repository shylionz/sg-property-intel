"""Create a consistent, persistent SQLite backup before the first rental repair."""
import fcntl
import logging
import os
import sqlite3
import tempfile
from pathlib import Path


def ensure_rental_backup(db):
    url = db.get_bind().url
    if url.get_backend_name() != "sqlite" or not url.database or url.database == ":memory:":
        return None
    source = Path(url.database).resolve()
    if not source.exists():
        return None  # A new installation has no existing database to preserve.
    directory = source.parent / ".backups"
    directory.mkdir(mode=0o700, exist_ok=True)
    target = directory / (source.stem + "-before-rental-refresh-v1.db")
    # Also serialize across workers. A process crash cannot expose a partial file
    # as a completed backup; replacement follows SQLite's integrity check.
    with (directory / ".rental-backup.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if target.exists():
            with sqlite3.connect(str(target)) as backup:
                if backup.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise RuntimeError("Existing rental backup failed its integrity check")
            logging.getLogger(__name__).info("Verified existing pre-repair SQLite backup: %s", target)
            return str(target)
        descriptor, temporary = tempfile.mkstemp(prefix="rental-backup-", suffix=".db", dir=directory)
        os.close(descriptor)
        try:
            with sqlite3.connect(source.as_uri() + "?mode=ro", uri=True) as original:
                with sqlite3.connect(temporary) as backup:
                    original.backup(backup)
                    if backup.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                        raise RuntimeError("Rental backup failed its integrity check")
            os.replace(temporary, target)
            logging.getLogger(__name__).info("Created and verified pre-repair SQLite backup: %s (integrity_check=ok)", target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    return str(target)
