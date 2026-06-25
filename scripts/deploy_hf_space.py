"""One-shot deploy to Hugging Face Spaces (Streamlit). Token via HF_TOKEN env."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SPACE_ID = os.environ.get("HF_SPACE_ID", "Tunti35/qec-playground")
SPACE_URL = f"https://huggingface.co/spaces/{SPACE_ID}"

HF_README = """---
title: QEC-Playground
emoji: ⚛️
colorFrom: indigo
colorTo: blue
sdk: docker
pinned: false
license: mit
app_port: 7860
---

# QEC-Playground

First open-source **full SWIPER-SIM behavioral model** for Li & Martonosi speculative window decoders ([arXiv:2606.24048](https://arxiv.org/abs/2606.24048)).

DeviceManager + WindowManager + DecoderManager — parallel/aligned/sliding strategies, blocking Conditional-S, matching-decoder speculation verify.

Tune processors, gate speed, speculation accuracy, window strategy, and ordering — compare speculative vs non-speculative metrics live.
"""

SLIM_REQUIREMENTS = """numpy>=1.24.0
scipy>=1.10.0
streamlit>=1.28.0
plotly>=5.18.0
pandas>=2.0.0
kaleido>=0.2.1
"""

IGNORE = [
    ".git",
    ".git/**",
    "**/.git/**",
    ".venv",
    ".venv/**",
    "**/.venv/**",
    ".pytest_cache",
    ".pytest_cache/**",
    "**/__pycache__/**",
    ".gating-evidence",
    ".gating-evidence/**",
    "mcps",
    "mcps/**",
    "tests",
    "tests/**",
    "scripts/deploy_hf_space.py",
    "requirements-dev.txt",
    ".cursor",
    ".cursor/**",
]


def main() -> int:
    token = os.environ.get("HF_TOKEN")
    if not token:
        print("Set HF_TOKEN", file=sys.stderr)
        return 1

    from huggingface_hub import HfApi, create_repo

    api = HfApi(token=token)
    who = api.whoami()
    print(f"HF user: {who['name']}")

    create_repo(
        SPACE_ID,
        repo_type="space",
        space_sdk="docker",
        private=False,
        exist_ok=True,
    )
    print(f"Space repo ready: {SPACE_ID}")

    api.upload_folder(
        folder_path=str(ROOT),
        repo_id=SPACE_ID,
        repo_type="space",
        ignore_patterns=IGNORE,
        commit_message="Deploy QEC-Playground Streamlit app",
    )
    api.upload_file(
        path_or_fileobj=HF_README.encode("utf-8"),
        path_in_repo="README.md",
        repo_id=SPACE_ID,
        repo_type="space",
        commit_message="Space card README with Streamlit SDK config",
    )
    api.upload_file(
        path_or_fileobj=SLIM_REQUIREMENTS.encode("utf-8"),
        path_in_repo="requirements.txt",
        repo_id=SPACE_ID,
        repo_type="space",
        commit_message="Slim runtime requirements (no QuTiP/pytest)",
    )

    print(f"DEPLOY_OK url={SPACE_URL}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())