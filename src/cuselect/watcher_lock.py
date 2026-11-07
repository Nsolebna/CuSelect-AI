# CuSelect-AI — Exclusive Research Watcher Lock
#
# PSEUDOCODE
# 1. Identify the lock file for watcher history.
# 2. Request exclusive access.
# 3. Reject a second process if a lock is held.
# 4. Allow the protected operation to execute.
# 5. Release the lock even if an error occurs.
# 6. Keep the lock file separate from research data.

import errno
import fcntl

from contextlib import contextmanager
from pathlib import Path


class WatcherLockError(RuntimeError):
    """Another process currently owns the watcher lock."""


@contextmanager
def exclusive_history_lock(history_path):
    """Prevent overlapping cooperative history updates."""

    lock_path = Path(str(history_path) + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    with lock_path.open("a+b") as handle:
        try:
            fcntl.flock(
                handle.fileno(),
                fcntl.LOCK_EX | fcntl.LOCK_NB,
            )
        except OSError as error:
            if error.errno in (errno.EAGAIN, errno.EACCES):
                raise WatcherLockError(
                    "Another Research Watcher scan "
                    "is already holding the history lock"
                ) from error
            raise

        try:
            yield
        finally:
            fcntl.flock(
                handle.fileno(),
                fcntl.LOCK_UN,
            )
