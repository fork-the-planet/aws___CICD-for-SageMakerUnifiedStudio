#!/usr/bin/env python3
"""
Load environment variables from per-pipeline YAML config.

Usage:
    python3 scripts/load_env.py <pipeline>

Examples:
    python3 scripts/load_env.py mlops       # all stages
    python3 scripts/load_env.py dataops     # all stages

Output (prefixed by stage):
    DEV_DOMAIN_NAME=Default_03112026_Domain
    TEST_DOMAIN_NAME=Default_03112026_Domain
    PROD_DOMAIN_NAME=Default_03112026_Domain

In GitHub Actions: writes to $GITHUB_ENV (no eval needed).
Locally: prints export statements to stdout for eval.

Config: examples/<pipeline>-pipeline/configs/<pipeline>.yaml
"""

import os
import sys
from pathlib import Path

import yaml


def find_config(pipeline: str) -> Path:
    """Locate the config YAML for the given pipeline."""
    root = Path(os.environ.get("REPO_ROOT", ""))
    if not root.is_dir():
        root = Path(__file__).resolve().parent.parent

    config = root / "examples" / f"{pipeline}-pipeline" / "configs" / f"{pipeline}.yaml"
    if not config.is_file():
        print(f"❌ Config not found: {config}", file=sys.stderr)
        sys.exit(1)
    return config


def parse_config(config: Path) -> list[tuple[str, str]]:
    """Parse YAML config and return (key, value) pairs for all stages."""
    with open(config) as f:
        cfg = yaml.safe_load(f)

    exports: list[tuple[str, str]] = []
    for stage, values in cfg.items():
        if not isinstance(values, dict):
            continue
        prefix = stage.upper()
        for key, val in values.items():
            exports.append((f"{prefix}_{key.upper()}", str(val)))

    # Also export common aliases expected by manifests
    # Maps: DEV_ACCOUNT_ID → AWS_ACCOUNT_ID, DEV_PROJECT_ROLE → PROJECT_ROLE
    alias_map = {"ACCOUNT_ID": "AWS_ACCOUNT_ID", "DEPLOYMENT_ROLE": "PROJECT_ROLE"}
    for stage, values in cfg.items():
        if not isinstance(values, dict):
            continue
        for key, val in values.items():
            upper_key = key.upper()
            if upper_key in alias_map:
                exports.append((alias_map[upper_key], str(val)))
        break  # Only use first stage for aliases

    return exports


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/load_env.py <pipeline>", file=sys.stderr)
        sys.exit(1)

    pipeline = sys.argv[1]
    config = find_config(pipeline)
    print(f"📋 Loading config: {config}", file=sys.stderr)

    exports = parse_config(config)
    if not exports:
        print(f"⚠️  No config found for {pipeline}", file=sys.stderr)
        sys.exit(1)

    github_env = os.environ.get("GITHUB_ENV")

    if github_env:
        # GitHub Actions: write directly to $GITHUB_ENV
        with open(github_env, "a") as f:
            for key, val in exports:
                f.write(f"{key}={val}\n")
    else:
        # Local: print export statements for eval
        for key, val in exports:
            print(f'export {key}="{val}"')

    print(f"✅ Loaded {pipeline} ({len(exports)} variables):", file=sys.stderr)
    for key, val in exports:
        print(f"  {key}={val}", file=sys.stderr)


if __name__ == "__main__":
    main()
