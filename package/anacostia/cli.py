# anacostia/cli.py

import os
import sys
import time
import subprocess
from pathlib import Path
import argparse
import importlib
import inspect

# Environment variable to distinguish parent vs child
_CHILD_ENV_VAR = "ANACOSTIA_RELOADER_CHILD"
print(sys.path)


def _run_app(app_path: str):
    """
    Import and run the app specified by `app_path`.

    `app_path` should be of the form 'module.submodule:attr',
    where `attr` is a callable (e.g., a function like `run`).
    """
    try:
        module_name, attr_name = app_path.split(":", 1)
    except ValueError:
        raise SystemExit(
            f"Invalid --app value '{app_path}'. Expected format 'module:attr', e.g. 'myproj.main:run'."
        )

    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:
        raise SystemExit(f"Could not import module '{module_name}' for --app: {exc}") from exc

    try:
        target = getattr(module, attr_name)
    except AttributeError as exc:
        raise SystemExit(
            f"Module '{module_name}' has no attribute '{attr_name}' (from --app '{app_path}')."
        ) from exc

    if not callable(target):
        raise SystemExit(
            f"Attribute '{attr_name}' in module '{module_name}' is not callable (from --app '{app_path}')."
        )

    # Call the target (e.g., `run()`)
    target()


def _iter_python_files(root: Path):
    """Yield all .py files under the given root directory."""
    for path in root.rglob("*.py"):
        yield path


def _snapshot_mtimes(root: Path):
    """Return a dict mapping file -> mtime for all .py files."""
    return {path: path.stat().st_mtime for path in _iter_python_files(root)}


def _resolve_app_directory(app_path: str) -> Path:
    # add current dir to sys.path to allow local imports
    repo_dir = Path.cwd()
    if repo_dir.is_dir():
        sys.path.insert(0, str(repo_dir))

    # Import the module part of the app path
    module_name, _ = app_path.split(":", 1)
    module = importlib.import_module(module_name)

    # Inspect the file the module came from and return its parent directory
    module_file = inspect.getfile(module)
    return Path(module_file).resolve().parent


def _run_with_reloader(args):
    """
    Parent process: spawn child that runs the app,
    watch for file changes, restart child on change.
    """
    package_root = _resolve_app_directory(args.app)
    print(f"Watching for changes under: {package_root}")

    # Initial snapshot of file mtimes
    mtimes = _snapshot_mtimes(package_root)

    while True:
        # Spawn child process
        env = os.environ.copy()
        env[_CHILD_ENV_VAR] = "1"  # mark as child

        # Build the command for the child.
        # We pass --app through so the child knows which app to run.
        cmd = [sys.executable, "-m", "anacostia", "--app", args.app]
        if args.no_reload:
            # Shouldn't happen because we're only here if reload=True,
            # but we keep args around for completeness.
            pass

        print("Starting child process...", " ".join(cmd))
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
    Entrypoint for the `anacostia` command and `python -m anacostia`.
    Handles:
      - parent (reloader)
      - child (actual app run)
    """
    parser = argparse.ArgumentParser(description="Anacostia server with optional auto-reload.")
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
    parser.add_argument(
        "--app",
        help=(
            "Application entrypoint as module:attr, "
            "e.g. 'some_repo.main:run'. Default is 'anacostia.app:run'."
        ),
    )
    args = parser.parse_args()

    # If we are in the child process, just run the app once.
    if os.environ.get(_CHILD_ENV_VAR) == "1":
        _run_app(args.app)
        return

    # Parent process behavior
    if args.reload and not args.no_reload:
        # Parent acts as reloader
        print("Starting reloader...")
        exit_code = _run_with_reloader(args)
        sys.exit(exit_code)
    else:
        # No reload: just run the app in this process
        _run_app(args.app)


if __name__ == "__main__":
    main()
