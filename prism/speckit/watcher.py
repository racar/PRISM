from __future__ import annotations

import logging
import platform
from pathlib import Path
from threading import Timer
from typing import Optional

log = logging.getLogger("prism.watcher")

_DEBOUNCE = 2.0


class _DebounceHandler:
    def __init__(self) -> None:
        self._timer: Optional[Timer] = None

    def dispatch(self, event) -> None:
        if not event.src_path.endswith("tasks.md"):
            return
        log.info("[FILE WATCHER] tasks.md detected → %s", event.src_path)
        if self._timer:
            self._timer.cancel()
        self._timer = Timer(_DEBOUNCE, self._augment, args=(Path(event.src_path),))
        self._timer.start()

    def _augment(self, path: Path) -> None:
        try:
            from prism.speckit.augmenter import augment_tasks_md, is_augmented
            output = path.with_name("tasks.prism.md")
            if is_augmented(output):
                log.info("[FILE WATCHER] already augmented — skipping")
                return
            result = augment_tasks_md(path)
            log.info("[FILE WATCHER] augmented → %s", result)
        except Exception as exc:
            log.error("[FILE WATCHER] augment failed: %s", exc)


def start_watcher(specs_dir: Path):
    if platform.system() == "Windows":
        log.warning("[FILE WATCHER] watchdog may be unstable on Windows — use 'prism augment' manually")
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler

        class _Handler(FileSystemEventHandler, _DebounceHandler):
            def __init__(self) -> None:
                FileSystemEventHandler.__init__(self)
                _DebounceHandler.__init__(self)

        observer = Observer()
        observer.schedule(_Handler(), path=str(specs_dir), recursive=True)
        observer.start()
        log.info("[FILE WATCHER] watching %s", specs_dir)
        return observer
    except ImportError:
        log.warning("[FILE WATCHER] watchdog not installed — file watching disabled")
        return None
