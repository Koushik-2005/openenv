"""OpenEnv server entrypoint for multi-mode deployment."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import uvicorn


def _load_root_server_app():
    """Load the existing root-level server.py app object without renaming files."""
    root_dir = Path(__file__).resolve().parents[1]
    root_server_file = root_dir / "server.py"

    spec = importlib.util.spec_from_file_location("root_server_module", root_server_file)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load root server.py module")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if not hasattr(module, "app"):
        raise RuntimeError("root server.py does not define FastAPI app")

    return module.app


app = _load_root_server_app()


def main() -> None:
    """Run the API server for OpenEnv direct serve modes."""
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "7860"))
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
