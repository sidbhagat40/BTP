"""Small, dependency-free utilities shared by the CPT commands."""

import hashlib
import json
import platform
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path


def read_json(path):
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require_empty_directory(path):
    path = Path(path)
    if path.exists() and (not path.is_dir() or any(path.iterdir())):
        raise ValueError(f"Refusing to overwrite {path}. Choose a new output directory.")
    path.mkdir(parents=True, exist_ok=True)
    return path


def environment_versions():
    result = {"python": platform.python_version()}
    for package in ("torch", "transformers", "datasets", "accelerate", "tokenizers"):
        try:
            result[package] = version(package)
        except PackageNotFoundError:
            result[package] = None
    return result
