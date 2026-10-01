"""Deploy MoodReel to a Hugging Face Space (Docker SDK) in one command.

Usage (from the repo root, after `pip install huggingface_hub`):

    export HF_TOKEN=hf_...            # a *write* token
    python scripts/deploy_hf_space.py --space <your-username>/moodreel

Optional environment variables are copied into the Space as secrets:
TMDB_API_KEY, TMDB_READ_TOKEN. Pass --llm to enable the LLM planner (uses HF_TOKEN
inside the Space via HF Inference Providers).

What it does:
1. Creates the Space if needed (SDK: docker, port 7860).
2. Uploads the repo (the root Dockerfile builds the UI and API into one container),
   with a Space-specific README carrying the required front matter.
3. Sets secrets and variables, then prints the Space URL.
"""

from __future__ import annotations

import argparse
import io
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FRONT_MATTER = """---
title: MoodReel
emoji: 🎬
colorFrom: yellow
colorTo: red
sdk: docker
app_port: 7860
pinned: false
short_description: Movies for how you feel — Malayalam, Hindi, Tamil, Telugu, English
---

"""

IGNORE = [
    ".git/*",
    "**/node_modules/*",
    "**/dist/*",
    "**/__pycache__/*",
    "**/.pytest_cache/*",
    "**/.ruff_cache/*",
    "backend/data/*",
    ".env",
    "docs/screenshots/*",
    "*.log",
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--space", required=True, help="Space id, e.g. username/moodreel"
    )
    parser.add_argument(
        "--private", action="store_true", help="create the Space as private"
    )
    parser.add_argument(
        "--llm",
        action="store_true",
        help="enable the LLM planner (LLM_BACKEND=hf_inference)",
    )
    parser.add_argument(
        "--hardware",
        default=None,
        help="e.g. cpu-upgrade (paid); default is free cpu-basic",
    )
    args = parser.parse_args()

    token = os.environ.get("HF_TOKEN")
    if not token:
        sys.exit(
            "HF_TOKEN is not set (needs a write token: huggingface.co/settings/tokens)"
        )
    try:
        from huggingface_hub import HfApi
    except ImportError:
        sys.exit("pip install huggingface_hub")

    api = HfApi(token=token)
    user = api.whoami()["name"]
    print(f"Authenticated as {user}")

    api.create_repo(
        args.space,
        repo_type="space",
        space_sdk="docker",
        private=args.private,
        exist_ok=True,
        space_hardware=args.hardware,
    )
    print(f"Space ready: {args.space}")

    readme = FRONT_MATTER + (ROOT / "README.md").read_text(encoding="utf-8")
    api.upload_folder(
        repo_id=args.space,
        repo_type="space",
        folder_path=str(ROOT),
        ignore_patterns=IGNORE + ["README.md"],
        commit_message="Deploy MoodReel",
    )
    api.upload_file(
        repo_id=args.space,
        repo_type="space",
        path_or_fileobj=io.BytesIO(readme.encode("utf-8")),
        path_in_repo="README.md",
        commit_message="Space README",
    )

    for name in ("TMDB_API_KEY", "TMDB_READ_TOKEN"):
        if os.environ.get(name):
            api.add_space_secret(args.space, name, os.environ[name])
            print(f"secret set: {name}")
    if args.llm:
        api.add_space_secret(args.space, "HF_TOKEN", token)
        api.add_space_variable(args.space, "LLM_BACKEND", "hf_inference")
        print("LLM planner enabled (LLM_BACKEND=hf_inference)")

    host = args.space.replace("/", "-").replace("_", "-").lower()
    print(
        f"\nBuilding now (first build takes a few minutes):\n  https://huggingface.co/spaces/{args.space}"
    )
    print(f"App URL once running:\n  https://{host}.hf.space")


if __name__ == "__main__":
    main()
