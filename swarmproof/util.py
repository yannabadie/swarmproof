"""Utilitaires fichiers, hashing, diff et sous-processus (stdlib uniquement)."""

from __future__ import annotations

import hashlib
import json
import re
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

IGNORED_DIRS = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".venv", "venv", "node_modules"}
IGNORED_SUFFIXES = {".pyc", ".pyo", ".so", ".dylib", ".dll"}
SECRET_NAME_PATTERNS = (
    ".env", ".env.*", "*.pem", "*.key", "*.p12", "*.pfx", "*.jks",
    "id_rsa*", "id_ed25519*", "*.ppk", "credentials*", ".npmrc", ".pypirc",
    ".netrc", "*.sqlite", "*.sqlite3", "*.db", "secrets.*", "*.secret",
)
SECRET_CONTENT_PATTERNS = (
    re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}"),
    re.compile(r"sk-proj-[A-Za-z0-9_-]{20,}"),
    re.compile(r"sk-[A-Za-z0-9]{32,}"),
    re.compile(r"AIza[0-9A-Za-z_-]{30,}"),
    re.compile(r"ghp_[A-Za-z0-9]{30,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----.*?-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", re.DOTALL),
    re.compile(r"(?i)\b(api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?[A-Za-z0-9_./+=-]{16,}"),
)
TEXT_SUFFIXES = {
    ".py", ".md", ".txt", ".json", ".toml", ".cfg", ".ini", ".yaml", ".yml", ".sh", ".patch",
    ".js", ".ts", ".tsx", ".jsx", ".css", ".html", ".sql", ".csv", ".gitignore", "",
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return utc_now().isoformat(timespec="seconds")


def stamp_slug(moment: datetime | None = None) -> str:
    moment = moment or utc_now()
    return moment.strftime("%Y%m%dT%H%M%SZ")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 256), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def write_json(path: Path, document: object) -> None:
    write_text(path, json.dumps(document, indent=2, ensure_ascii=False, sort_keys=True) + "\n")


def iter_files(root: Path) -> list[Path]:
    """Fichiers texte/utiles du dépôt, triés, sans artefacts de build."""
    files: list[Path] = []
    for current, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(name for name in dirnames if name not in IGNORED_DIRS)
        for filename in sorted(filenames):
            path = Path(current) / filename
            if path.suffix in IGNORED_SUFFIXES:
                continue
            files.append(path)
    return files


def is_text(path: Path) -> bool:
    if path.suffix.lower() not in TEXT_SUFFIXES:
        return False
    try:
        path.read_text(encoding="utf-8")
        return True
    except (UnicodeDecodeError, OSError):
        return False


def copy_tree(src: Path, dst: Path) -> Path:
    """Copie récursive en ignorant VCS/caches ; le dossier destination est recréé."""
    if dst.exists():
        shutil.rmtree(dst)
    ignore = shutil.ignore_patterns(
        *IGNORED_DIRS,
        *[f"*{suffix}" for suffix in IGNORED_SUFFIXES],
        *SECRET_NAME_PATTERNS,
    )
    shutil.copytree(src, dst, ignore=ignore)
    return dst


def remove_tree(path: Path) -> None:
    shutil.rmtree(path, ignore_errors=True)


def relative_files(root: Path) -> list[str]:
    return [str(path.relative_to(root)).replace(os.sep, "/") for path in iter_files(root)]


def unified_diff_dirs(source: Path, tree: Path, label_source: str = "a", label_tree: str = "b") -> str:
    """Diff unifié des fichiers texte entre deux arborescences (preuve des modifications)."""
    import difflib

    chunks: list[str] = []
    source_files = set(relative_files(source)) if source.is_dir() else set()
    tree_files = set(relative_files(tree)) if tree.is_dir() else set()
    for rel_path in sorted(source_files | tree_files):
        left = (source / rel_path) if (source / rel_path).is_file() else None
        right = (tree / rel_path) if (tree / rel_path).is_file() else None
        left_lines = left.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True) if left else []
        right_lines = right.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True) if right else []
        if left_lines == right_lines:
            continue
        if not left or not right or not is_text(left if left else right):
            chunks.append(f"--- {label_source}/{rel_path}\n+++ {label_tree}/{rel_path}\n[binaire ou illisible]\n")
            continue
        diff = difflib.unified_diff(
            left_lines,
            right_lines,
            fromfile=f"{label_source}/{rel_path}",
            tofile=f"{label_tree}/{rel_path}",
            n=3,
        )
        chunks.append("".join(diff))
    return "".join(chunks)


def changed_files(source: Path, tree: Path) -> list[str]:
    changed: list[str] = []
    source_files = set(relative_files(source))
    tree_files = set(relative_files(tree))
    for rel_path in sorted(source_files | tree_files):
        left = source / rel_path
        right = tree / rel_path
        if not left.is_file() or not right.is_file():
            changed.append(rel_path)
            continue
        if sha256_file(left) != sha256_file(right):
            changed.append(rel_path)
    return changed


def run_command(
    command: str,
    cwd: Path,
    timeout: float,
    env: dict[str, str] | None = None,
) -> dict:
    """Exécute une commande shell et retourne un résultat structuré (ne lève pas)."""
    started = time.time()
    merged_env = dict(os.environ)
    merged_env.setdefault("PYTHONIOENCODING", "utf-8")
    if env:
        merged_env.update(env)
    try:
        process = subprocess.run(
            command,
            shell=True,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=max(timeout, 1.0),
            env=merged_env,
        )
        return {
            "command": command,
            "cwd": str(cwd),
            "exit_code": process.returncode,
            "duration_seconds": round(time.time() - started, 2),
            "stdout": process.stdout or "",
            "stderr": process.stderr or "",
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        def _text(value: object) -> str:
            if isinstance(value, bytes):
                return value.decode("utf-8", errors="replace")
            return str(value or "")

        return {
            "command": command,
            "cwd": str(cwd),
            "exit_code": None,
            "duration_seconds": round(time.time() - started, 2),
            "stdout": _text(exc.stdout),
            "stderr": _text(exc.stderr),
            "timed_out": True,
        }
    except FileNotFoundError as exc:
        return {
            "command": command,
            "cwd": str(cwd),
            "exit_code": None,
            "duration_seconds": round(time.time() - started, 2),
            "stdout": "",
            "stderr": str(exc),
            "timed_out": False,
        }


def run_version(binary: str, timeout: float = 15.0) -> str | None:
    """Version d'un binaire CLI (best effort, jamais bloquant)."""
    try:
        process = subprocess.run(
            [binary, "--version"], capture_output=True, text=True, timeout=timeout
        )
        text = (process.stdout or process.stderr or "").strip().splitlines()
        return text[0][:120] if text else None
    except (OSError, subprocess.SubprocessError):
        return None


def platform_summary() -> dict:
    return {"python": sys.version.split()[0], "platform": sys.platform, "executable": sys.executable}


# ---------------------------------------------------------------------------
# v0.2 sécurité : secrets, chemins, entrées de pack
# ---------------------------------------------------------------------------
def find_secret_files(root: Path) -> list[str]:
    """Fichiers dont le NOM indique un secret (exclus des packs)."""
    import fnmatch

    found: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        name = path.name
        if any(fnmatch.fnmatch(name, pattern) for pattern in SECRET_NAME_PATTERNS):
            found.append(str(path.relative_to(root)).replace("\\", "/"))
    return sorted(found)


def contains_secret(text: str) -> bool:
    return any(pattern.search(text or "") for pattern in SECRET_CONTENT_PATTERNS)


def redact_secrets(text: str) -> str:
    redacted = text or ""
    for pattern in SECRET_CONTENT_PATTERNS:
        redacted = pattern.sub("[REDACTED_SECRET]", redacted)
    return redacted


def sanitize_paths(text: str, roots: list[Path] | None = None) -> str:
    """Remplace les chemins locaux absolus par des jetons neutres (pack publiable)."""
    sanitized = text or ""
    replacements: list[tuple[str, str]] = []
    for index, root in enumerate(roots or []):
        token = "<repo>" if index == 0 else "<workdir>"
        raw = str(root)
        if raw and raw != "/":
            replacements.append((raw, token))
        try:
            resolved = str(Path(root).resolve())
        except OSError:
            resolved = ""
        if resolved and resolved != "/" and resolved != raw:
            replacements.append((resolved, token))
    home = str(Path.home())
    if home and home != "/":
        replacements.append((home, "<home>"))
    for original, token in sorted(set(replacements), key=lambda item: -len(item[0])):
        sanitized = sanitized.replace(original, token)
    sanitized = sanitized.replace("/tmp/swarmproof-", "<tmp>/swarmproof-")
    return sanitized


def iter_all_files(root: Path) -> list[Path]:
    """Tous les fichiers (y compris cachés), sans filtre : utilisé pour l'intégrité de pack."""
    files: list[Path] = []
    for current, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for filename in sorted(filenames):
            files.append(Path(current) / filename)
    return files


def run_command_argv(command: str, cwd: Path, timeout: float) -> dict:
    """Exécute une commande SIMPLE (pas de shell) après refus des métacaractères shell."""
    import shlex

    forbidden = (";", "&&", "||", "|", ">", "<", "$(", "`", "\n")
    if any(token in command for token in forbidden):
        return {
            "command": command,
            "cwd": str(cwd),
            "exit_code": None,
            "duration_seconds": 0.0,
            "stdout": "",
            "stderr": "commande refusée : métacaractères shell interdits pour le rejeu",
            "timed_out": False,
            "refused": True,
        }
    try:
        argv = shlex.split(command)
    except ValueError as exc:
        return {
            "command": command,
            "cwd": str(cwd),
            "exit_code": None,
            "duration_seconds": 0.0,
            "stdout": "",
            "stderr": f"commande invalide: {exc}",
            "timed_out": False,
            "refused": True,
        }
    if not argv:
        return {
            "command": command,
            "cwd": str(cwd),
            "exit_code": None,
            "duration_seconds": 0.0,
            "stdout": "",
            "stderr": "commande vide",
            "timed_out": False,
            "refused": True,
        }
    started = time.time()
    try:
        process = subprocess.run(argv, cwd=str(cwd), capture_output=True, text=True, timeout=timeout)
        return {
            "command": command,
            "cwd": str(cwd),
            "exit_code": process.returncode,
            "duration_seconds": round(time.time() - started, 2),
            "stdout": process.stdout or "",
            "stderr": process.stderr or "",
            "timed_out": False,
            "refused": False,
        }
    except subprocess.TimeoutExpired:
        return {
            "command": command,
            "cwd": str(cwd),
            "exit_code": None,
            "duration_seconds": round(time.time() - started, 2),
            "stdout": "",
            "stderr": "timeout",
            "timed_out": True,
            "refused": False,
        }
