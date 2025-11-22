# myserver/cli.py

import os
import sys
import time
import subprocess
from pathlib import Path
import argparse

# Environment variable to distinguish parent vs child
_CHILD_ENV_VAR = "MYSERVER_RELOADER_CHILD"


def _run_app():
    """Import and run your app."""
    from .app import run
    run()


def _iter_python_files(root: Path):
    """Yield all .py files under the given root directory."""
    for path in root.rglob("*.py"):
        yield path


def _snapshot_mtimes(root: Path):
    """Return a dict mapping file -> mtime for all .py files."""
    return {path: path.stat().st_mtime for path in _iter_python_files(root)}


def _run_with_reloader(args):
    """
    Parent process: spawn child that runs the app,
    watch for file changes, restart child on change.
    """
    package_root = Path(__file__).resolve().parent
    print(f"Watching for changes under: {package_root}")

    # Initial snapshot of file mtimes
    mtimes = _snapshot_mtimes(package_root)

    while True:
        # Spawn child process
        env = os.environ.copy()
        env[_CHILD_ENV_VAR] = "1"  # mark as child
        cmd = [sys.executable, "-m", "myserver"]
        if args.no_reload:
            # Shouldn't happen because we're only here if reload=True,
            # but we keep args around for completeness.
            pass

        print("Starting child process...")
        proc = subprocess.Popen(cmd, env=env)

        try:
            while True:
                # Has the child exited?
                return_code = proc.poll()
                if return_code is not None:
                    print(f"Child exited with code {return_code}.")
                    return return_code

                time.sleep(1.0)

                # Check for file changes
                new_mtimes = _snapshot_mtimes(package_root)
                if new_mtimes != mtimes:
                    print("Detected file change. Reloading...")
                    mtimes = new_mtimes
                    # Kill child and break to restart
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                    break  # restart loop (new child)
        except KeyboardInterrupt:
            print("Reloader got KeyboardInterrupt, shutting down.")
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
            return 0


def main():
    """
    Entrypoint for the `myserver` command and `python -m myserver`.
    Handles:
      - parent (reloader)
      - child (actual app run)
    """
    parser = argparse.ArgumentParser(description="Example server with auto-reload.")
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload on code changes.",
    )
    parser.add_argument(
        "--no-reload",
        action="store_true",
        help="Disable auto-reload (run app once).",
    )
    args = parser.parse_args()

    # If we are in the child process, just run the app once.
    if os.environ.get(_CHILD_ENV_VAR) == "1":
        _run_app()
        return

    # Parent process behavior
    if args.reload and not args.no_reload:
        # Parent acts as reloader
        exit_code = _run_with_reloader(args)
        sys.exit(exit_code)
    else:
        # No reload: just run the app in this process
        _run_app()


if __name__ == "__main__":
    main()
