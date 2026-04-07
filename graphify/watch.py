# monitor a folder and auto-trigger --update when files change
from __future__ import annotations
import json
import time
from pathlib import Path

from graphify.log import logger


_WATCHED_EXTENSIONS = {
    ".py", ".ts", ".js", ".go", ".rs", ".java", ".cpp", ".c", ".rb", ".swift", ".kt",
    ".cs", ".scala", ".php", ".cc", ".cxx", ".hpp", ".h", ".kts",
    ".md", ".txt", ".rst", ".pdf",
    ".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg",
}

_CODE_EXTENSIONS = {
    ".py", ".ts", ".js", ".go", ".rs", ".java", ".cpp", ".c", ".rb", ".swift", ".kt",
    ".cs", ".scala", ".php", ".cc", ".cxx", ".hpp", ".h", ".kts",
}


def _rebuild_code(watch_path: Path, *, follow_symlinks: bool = False) -> bool:
    """Re-run AST extraction + build + cluster + report for code files. No LLM needed.

    Returns True on success, False on error.
    """
    try:
        from graphify.extract import collect_files, extract
        from graphify.build import build_from_json
        from graphify.cluster import cluster, score_all
        from graphify.analyze import god_nodes, surprising_connections, suggest_questions
        from graphify.report import generate
        from graphify.export import to_json

        code_files = collect_files(watch_path, follow_symlinks=follow_symlinks)
        code_files = [
            f for f in code_files
            if "graphify-out" not in f.parts
            and "__pycache__" not in f.parts
        ]

        if not code_files:
            logger.info("watch: No code files found - nothing to rebuild.")
            return False

        result = extract(code_files)

        detection = {
            "files": {"code": [str(f) for f in code_files], "document": [], "paper": [], "image": []},
            "total_files": len(code_files),
            "total_words": 0,  # not needed during watch rebuild
        }

        G = build_from_json(result)
        communities = cluster(G)
        cohesion = score_all(G, communities)
        gods = god_nodes(G)
        surprises = surprising_connections(G, communities)
        labels = {cid: "Community " + str(cid) for cid in communities}
        questions = suggest_questions(G, communities, labels)

        out = watch_path / "graphify-out"
        out.mkdir(exist_ok=True)

        report = generate(G, communities, cohesion, labels, gods, surprises, detection,
                          {"input": 0, "output": 0}, str(watch_path), suggested_questions=questions)
        (out / "GRAPH_REPORT.md").write_text(report)
        to_json(G, communities, str(out / "graph.json"))

        # clear stale needs_update flag if present
        flag = out / "needs_update"
        if flag.exists():
            flag.unlink()

        logger.info("watch: Rebuilt: %d nodes, %d edges, %d communities",
                    G.number_of_nodes(), G.number_of_edges(), len(communities))
        logger.info("watch: graph.json and GRAPH_REPORT.md updated in %s", out)
        return True

    except Exception as exc:
        logger.error("watch: Rebuild failed: %s", exc)
        return False


def _notify_only(watch_path: Path) -> None:
    """Write a flag file and print a notification (fallback for non-code-only corpora)."""
    flag = watch_path / "graphify-out" / "needs_update"
    flag.parent.mkdir(parents=True, exist_ok=True)
    flag.write_text("1")
    logger.info("watch: New or changed files detected in %s", watch_path)
    logger.info("watch: Non-code files changed - semantic re-extraction requires LLM.")
    logger.info("watch: Run `/graphify --update` in Claude Code to update the graph.")
    logger.info("watch: Flag written to %s", flag)


def _has_non_code(changed_paths: list[Path]) -> bool:
    return any(p.suffix.lower() not in _CODE_EXTENSIONS for p in changed_paths)


def watch(watch_path: Path, debounce: float = 3.0) -> None:
    """
    Watch watch_path for new or modified files and auto-update the graph.

    For code-only changes: re-runs AST extraction + rebuild immediately (no LLM).
    For doc/paper/image changes: writes a needs_update flag and notifies the user
    to run /graphify --update (LLM extraction required).

    debounce: seconds to wait after the last change before triggering (avoids
    running on every keystroke when many files are saved at once).
    """
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
    except ImportError as e:
        raise ImportError("watchdog not installed. Run: pip install watchdog") from e

    last_trigger: float = 0.0
    pending: bool = False
    changed: set[Path] = set()

    class Handler(FileSystemEventHandler):
        def on_any_event(self, event):
            nonlocal last_trigger, pending
            if event.is_directory:
                return
            path = Path(event.src_path)
            if path.suffix.lower() not in _WATCHED_EXTENSIONS:
                return
            if any(part.startswith(".") for part in path.parts):
                return
            if "graphify-out" in path.parts:
                return
            last_trigger = time.monotonic()
            pending = True
            changed.add(path)

    handler = Handler()
    observer = Observer()
    observer.schedule(handler, str(watch_path), recursive=True)
    observer.start()

    logger.info("watch: Watching %s - press Ctrl+C to stop", watch_path.resolve())
    logger.info("watch: Code changes rebuild graph automatically. "
                "Doc/image changes require /graphify --update.")
    logger.info("watch: Debounce: %ss", debounce)

    try:
        while True:
            time.sleep(0.5)
            if pending and (time.monotonic() - last_trigger) >= debounce:
                pending = False
                batch = list(changed)
                changed.clear()
                logger.info("watch: %d file(s) changed", len(batch))
                if _has_non_code(batch):
                    _notify_only(watch_path)
                else:
                    _rebuild_code(watch_path)
    except KeyboardInterrupt:
        logger.info("watch: Stopped.")
    finally:
        observer.stop()
        observer.join()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Watch a folder and auto-update the graphify graph")
    parser.add_argument("path", nargs="?", default=".", help="Folder to watch (default: .)")
    parser.add_argument("--debounce", type=float, default=3.0,
                        help="Seconds to wait after last change before updating (default: 3)")
    args = parser.parse_args()
    watch(Path(args.path), debounce=args.debounce)
