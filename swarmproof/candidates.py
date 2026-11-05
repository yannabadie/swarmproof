"""Extraction et validation des correctifs candidats (v0.2 — multi-fichiers).

Un correctif candidat = un **ensemble atomique** de fichiers complets. Règles :
- format recommandé : un marqueur `--- FILE: chemin/relatif.py ---` suivi d'un bloc ```python ;
- chaque fichier doit être une cible connue du dépôt (pas de chemin hors arborescence) ;
- un bloc doit être du **Python complet et syntaxiquement valide** (`ast.parse`) ;
- sont rejetés : blocs partiels (`...`, `# unchanged`, marqueurs de diff), doublons de fichier,
  blocs non étiquetés quand plusieurs cibles existent, fichiers hors cible ;
- l'application est **atomique** : tout ou rien, jamais de demi-correctif.

Les fonctions mono-fichier de la v0.1 restent disponibles (compatibilité interne/tests).
"""

from __future__ import annotations

import ast
import dataclasses
import re
from pathlib import Path

FENCED_BLOCK = re.compile(r"```(?:python|py)?[ \t]*\n(.*?)```", re.DOTALL)
FILE_MARKER = re.compile(
    r"^[ \t]*(?:-{2,}|#{2,})?[ \t]*(?:FILE[ \t]*:[ \t]*)?([A-Za-z0-9_][A-Za-z0-9_./-]*\.py)[ \t]*(?:-{2,})?[ \t]*$",
    re.MULTILINE,
)
RAW_MARKER = re.compile(r"^[ \t]*(?:-{2,}|#{2,})[ \t]*(?:FILE[ \t]*:[ \t]*)?([A-Za-z0-9_][A-Za-z0-9_./-]*\.py)[ \t]*-{2,}[ \t]*$", re.MULTILINE)
SYMBOL = re.compile(r"^(?:def|class)\s+([A-Za-z_]\w*)", re.MULTILINE)
IDENTIFIER = re.compile(r"[A-Za-z_]\w{2,}")
TEST_MARKERS = ("import unittest", "class Test", "import pytest", "def test_")
PLACEHOLDER_MARKERS = (
    "# ...",
    "# (...)",
    "... # unchanged",
    "# unchanged",
    "# rest of",
    "# reste inchangé",
    "# reste du fichier",
    "<...>",
    "[...]",
    "TODO: rest",
    "```",
)
DIFF_MARKERS = ("@@ ", "--- a/", "+++ b/")
ANY_FILE_HINT = re.compile(r"FILE\s*:\s*([^\n]+?\.py)", re.IGNORECASE)
MIN_BLOCK_CHARS = 20


@dataclasses.dataclass
class CandidateFile:
    path: str
    content: str

    def to_dict(self) -> dict:
        return {"path": self.path, "chars": len(self.content)}


@dataclasses.dataclass
class CandidateSet:
    """Ensemble atomique de fichiers complets proposé par un agent."""

    files: list[CandidateFile]
    agent_id: str = "?"
    role: str = "?"
    raw_sha256: str = ""

    @property
    def n_files(self) -> int:
        return len(self.files)

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "role": self.role,
            "n_files": self.n_files,
            "files": [item.to_dict() for item in self.files],
            "raw_sha256": self.raw_sha256,
        }


@dataclasses.dataclass
class Rejection:
    reason: str
    detail: str = ""
    agent_id: str = "?"
    role: str = "?"

    def to_dict(self) -> dict:
        return {"reason": self.reason, "detail": self.detail, "agent_id": self.agent_id, "role": self.role}


# ---------------------------------------------------------------------------
# Compatibilité v0.1 (mono-fichier, utilisé par les tests historiques)
# ---------------------------------------------------------------------------
def extract_code_blocks(text: str) -> list[str]:
    """Blocs de code candidats d'une réponse agent (fences ; fallback texte brut)."""
    if not text or not text.strip():
        return []
    blocks = FENCED_BLOCK.findall(text)
    if not blocks and ("def " in text or "class " in text):
        blocks = [text]
    candidates: list[str] = []
    for block in blocks:
        stripped = block.strip("\n")
        if len(stripped) < MIN_BLOCK_CHARS:
            continue
        if not ("def " in stripped or "class " in stripped):
            continue
        if any(marker in stripped for marker in TEST_MARKERS[:2]):
            continue
        if stripped not in candidates:
            candidates.append(stripped)
    return candidates


def candidate_symbols(candidate: str) -> set[str]:
    return set(SYMBOL.findall(candidate))


def target_score(candidate: str, target_content: str) -> int:
    symbols = candidate_symbols(candidate)
    if not symbols:
        return 0
    present = set(IDENTIFIER.findall(target_content))
    return len(symbols & present)


def choose_target(candidate: str, targets: dict[str, str], preferred: list[str] | None = None) -> str | None:
    """Choisit LE fichier cible d'un candidat mono-fichier (v0.1)."""
    if not targets:
        return None
    if preferred:
        for rel_path in preferred:
            if rel_path in targets:
                return rel_path
    if len(targets) == 1:
        return next(iter(targets))
    scored = [(target_score(candidate, content), rel_path) for rel_path, content in targets.items()]
    scored.sort(reverse=True)
    best_score, best_path = scored[0]
    if best_score <= 0:
        return None
    return best_path


def detect_targets(repo: Path) -> list[str]:
    """Fichiers Python candidats à la correction : `src/`, sinon racine, hors tests."""
    def _relative(path: Path) -> str:
        return str(path.relative_to(repo)).replace("\\", "/")

    def _valid(path: Path) -> bool:
        rel = _relative(path)
        if "__pycache__" in rel or rel.endswith(".pyc"):
            return False
        name = path.name
        if name.startswith("test_") or name.endswith("_test.py") or name == "conftest.py":
            return False
        if "/tests/" in f"/{rel}" or rel.startswith("tests/"):
            return False
        if name == "__init__.py" and path.stat().st_size == 0:
            return False
        return True

    source_dir = repo / "src"
    if source_dir.is_dir():
        candidates = [path for path in sorted(source_dir.rglob("*.py")) if _valid(path)]
        if candidates:
            return [_relative(path) for path in candidates]
    candidates = [path for path in sorted(repo.glob("*.py")) if _valid(path)]
    return [_relative(path) for path in candidates]


def apply_candidate(tree: Path, target_rel: str, candidate: str) -> None:
    """Écrit un contenu candidat dans un fichier cible (compatibilité v0.1)."""
    target = (tree / target_rel).resolve()
    root = tree.resolve()
    if not str(target).startswith(str(root)):
        raise ValueError(f"cible hors arborescence: {target_rel}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(candidate.rstrip("\n") + "\n", encoding="utf-8", newline="\n")


# ---------------------------------------------------------------------------
# v0.2 : multi-fichiers
# ---------------------------------------------------------------------------
def _validate_content(content: str) -> str | None:
    """Retourne une raison de rejet, ou None si le bloc est un fichier complet plausible."""
    stripped = content.strip("\n")
    if len(stripped) < MIN_BLOCK_CHARS:
        return "bloc trop court"
    if any(marker in stripped for marker in DIFF_MARKERS):
        return "bloc au format diff, pas un fichier complet"
    if any(marker in stripped for marker in PLACEHOLDER_MARKERS):
        return "bloc partiel (marqueur de troncature/placeholder)"
    if any(marker in stripped for marker in TEST_MARKERS[:2]):
        return "bloc de test interdit (les tests ne sont jamais modifiés)"
    try:
        ast.parse(stripped)
    except SyntaxError as exc:
        return f"code Python incomplet/invalide (ligne {exc.lineno}: {exc.msg})"
    return None


def _split_tagged_blocks(text: str) -> list[tuple[str, str]]:
    """Extrait couples (chemin, contenu) à partir des marqueurs FILE et fences."""
    markers = list(RAW_MARKER.finditer(text))
    if not markers:
        markers = [match for match in FILE_MARKER.finditer(text) if match.group(1)]
    pairs: list[tuple[str, str]] = []
    for position, match in enumerate(markers):
        path = match.group(1)
        start = match.end()
        end = markers[position + 1].start() if position + 1 < len(markers) else len(text)
        segment = text[start:end]
        blocks = FENCED_BLOCK.findall(segment)
        content = blocks[0] if blocks else segment
        pairs.append((path.replace("\\", "/"), content.strip("\n")))
    return pairs


def parse_candidate_sets(
    text: str,
    allowed_targets: list[str],
    *,
    agent_id: str = "?",
    role: str = "?",
    raw_sha256: str = "",
) -> tuple[list[CandidateSet], list[Rejection]]:
    """Analyse une réponse agent en ensembles de correctifs multi-fichiers valides."""
    if not text or not text.strip():
        return [], [Rejection("réponse vide", agent_id=agent_id, role=role)]

    allowed = set(allowed_targets)
    rejections: list[Rejection] = []

    # Sécurité : tout chemin hinté hors arborescence (traversée, absolu) invalide la proposition.
    for hint in ANY_FILE_HINT.findall(text):
        raw_path = hint.strip().strip("`'\" ")
        normalized_hint = raw_path.replace("\\", "/")
        if normalized_hint.startswith(("/", "~")) or ".." in normalized_hint.split("/"):
            rejections.append(Rejection("chemin hors arborescence (traversée/absolu)", raw_path, agent_id, role))
    if rejections:
        return [], rejections

    pairs = _split_tagged_blocks(text)

    if pairs:
        seen: set[str] = set()
        files: list[CandidateFile] = []
        for path, content in pairs:
            normalized = path.strip().lstrip("./")
            if normalized not in allowed:
                rejections.append(
                    Rejection(
                        "fichier hors cible",
                        f"{normalized} (cibles autorisées: {', '.join(sorted(allowed)) or 'aucune'})",
                        agent_id,
                        role,
                    )
                )
                continue
            if normalized in seen:
                rejections.append(Rejection("fichier en double (ambigu)", normalized, agent_id, role))
                continue
            seen.add(normalized)
            problem = _validate_content(content)
            if problem:
                rejections.append(Rejection(problem, normalized, agent_id, role))
                continue
            files.append(CandidateFile(path=normalized, content=content.strip("\n")))
        if rejections:
            # Ensemble rejeté en bloc : pas d'application partielle.
            return [], rejections
        if not files:
            return [], [Rejection("aucun bloc exploitable", agent_id=agent_id, role=role)]
        # Tout bloc de code non étiqueté rend la proposition ambiguë (pas d'application partielle).
        fences = len(FENCED_BLOCK.findall(text))
        if fences > len(pairs):
            return [], [
                Rejection(
                    "bloc(s) de code non étiqueté(s) : proposition ambiguë (tout ou rien)",
                    f"{fences} blocs pour {len(pairs)} marqueurs FILE",
                    agent_id,
                    role,
                )
            ]
        return [CandidateSet(files=files, agent_id=agent_id, role=role, raw_sha256=raw_sha256)], []

    # Pas de marqueur : fallback mono-fichier explicitement borné.
    blocks = extract_code_blocks(text)
    if not blocks:
        return [], [Rejection("aucun bloc de code complet détecté", agent_id=agent_id, role=role)]
    if len(allowed) != 1:
        return [], [
            Rejection(
                "bloc non étiqueté avec plusieurs cibles possibles (ambigu)",
                f"cibles: {', '.join(sorted(allowed))}",
                agent_id,
                role,
            )
        ]
    target = next(iter(allowed))
    if len(blocks) > 1:
        return [], [Rejection("plusieurs blocs non étiquetés (ambigu)", target, agent_id, role)]
    problem = _validate_content(blocks[0])
    if problem:
        return [], [Rejection(problem, target, agent_id, role)]
    return [
        CandidateSet(files=[CandidateFile(path=target, content=blocks[0].strip("\n"))], agent_id=agent_id, role=role, raw_sha256=raw_sha256)
    ], []


def apply_candidate_set(tree: Path, candidate_set: CandidateSet) -> list[str]:
    """Applique l'ensemble atomiquement (tout ou rien) ; retourne les chemins écrits."""
    root = tree.resolve()
    prepared: list[tuple[Path, str]] = []
    for item in candidate_set.files:
        target = (tree / item.path).resolve()
        if not str(target).startswith(str(root) + "/") and target != root:
            raise ValueError(f"cible hors arborescence: {item.path}")
        if not target.is_file():
            raise ValueError(f"cible inexistante (pas de création de fichier en v0.2): {item.path}")
        prepared.append((target, item.content.rstrip("\n") + "\n"))
    written: list[str] = []
    backups: list[tuple[Path, str]] = []
    try:
        for target, content in prepared:
            backups.append((target, target.read_text(encoding="utf-8")))
            target.write_text(content, encoding="utf-8", newline="\n")
            written.append(str(target.relative_to(root)).replace("\\", "/"))
    except Exception:
        for target, original in backups:  # rollback : atomicité
            target.write_text(original, encoding="utf-8", newline="\n")
        raise
    return written
