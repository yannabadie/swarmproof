"""Pont vers le moteur NEXUS original (`swarm-os`, branche NX-CG) — extraction, pas réécriture.

Le moteur NEXUS n'est PAS copié dans ce package : il est importé depuis une copie jetable de
`swarm-os` (lecture seule côté source), via son point d'injection `invoke_agent` qui accepte
n'importe quel callback `(agent_id, task_type, context, session_uuid, isolated_env) -> str`.

Trois `__init__.py` avides empêchent l'import direct (`sqlmodel`, `tiktoken`) : ils sont
contournés par un shim de modules « package » minimal (mesuré : import + init ≈ 40 ms).
Voir `reports/nexus-engine-e2e.md`.
"""

from __future__ import annotations

import os
import shutil
import sys
import types
from pathlib import Path
from typing import Any

from swarmproof.retry import CallBudget, invoke_with_retries
from swarmproof.trace import TraceWriter

BYPASS_PACKAGES = ("core.observability", "core.infrastructure", "core.intelligence")

_WORKSPACE_GUESS = Path(__file__).resolve().parents[3]


def find_nexus_src(explicit: str | Path | None = None) -> Path | None:
    """Localise le dépôt `swarm-os` (argument, env NEXUS_SRC, ou workspace voisin)."""
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit).expanduser())
    env_value = os.environ.get("NEXUS_SRC")
    if env_value:
        candidates.append(Path(env_value).expanduser())
    candidates.append(_WORKSPACE_GUESS / "swarm-os")
    candidates.append(Path.cwd() / "swarm-os")
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        marker = resolved / "core" / "intelligence" / "swarm" / "hybrid_swarm_engine.py"
        if marker.is_file():
            return resolved
    return None


def ensure_nexus_copy(nexus_src: Path, copy_root: Path | None = None) -> Path:
    """Copie jetable et réutilisable du moteur NEXUS (jamais le dépôt source lui-même)."""
    root = copy_root or Path(os.environ.get("SWARMPROOF_NEXUS_COPY", "/tmp/swarmproof-nexus"))
    marker = root / "core" / "intelligence" / "swarm" / "hybrid_swarm_engine.py"
    if marker.is_file():
        return root.resolve()
    if root.exists():
        shutil.rmtree(root)
    ignore = shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache", "workspace", "*.pyc")
    shutil.copytree(nexus_src, root, ignore=ignore)
    return root.resolve()


def activate(nexus_root: Path) -> Path:
    """Rend importables les modules du moteur depuis la copie jetable (sans toucher au repo)."""
    root = Path(nexus_root).resolve()
    if not (root / "core" / "intelligence" / "swarm" / "hybrid_swarm_engine.py").is_file():
        raise FileNotFoundError(f"moteur NEXUS introuvable sous {root}")
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    import core  # noqa: F401  (core/__init__.py est léger : version uniquement)

    for name in BYPASS_PACKAGES:
        if name in sys.modules:
            continue
        module = types.ModuleType(name)
        module.__path__ = [str(root / name.replace(".", "/"))]
        module.__package__ = name
        module.__file__ = None
        sys.modules[name] = module
        parent, _, child = name.rpartition(".")
        if parent in sys.modules:
            setattr(sys.modules[parent], child, module)
    return root


class _RegistryDriverAdapter:
    """Adapte un driver CLI au `DriverProtocol` async attendu par le registre NEXUS."""

    def __init__(self, driver: Any) -> None:
        self._driver = driver

    async def invoke(self, prompt: str, **kwargs: Any) -> str:
        return self._driver.invoke(prompt, role=kwargs.get("role", "support"))


def build_engine(
    nexus_copy: Path,
    drivers: dict[str, Any],
    roles: dict[str, str],
    mode: str,
    trace: TraceWriter,
    *,
    max_retries: int = 1,
    budget: CallBudget | None = None,
) -> dict:
    """Instancie le moteur NEXUS original avec 1 ou 2 agents CLI hétérogènes."""
    import time

    started = time.time()
    if budget is None:
        budget = CallBudget(max_calls=8)
    outcomes: list[dict] = []
    activate(nexus_copy)

    from core.foundation.agents.unified_registry import get_registry
    from core.intelligence.swarm.agent_metrics import AgentPool, AgentProfile
    from core.intelligence.swarm.hybrid_swarm_engine import HybridSwarmEngine

    nexus_version: dict[str, str] = {}
    try:
        from core.version import NEXUS_CODENAME, NEXUS_VERSION

        nexus_version = {"version": NEXUS_VERSION, "codename": NEXUS_CODENAME}
    except Exception:  # pragma: no cover - defensive
        nexus_version = {"version": "unknown", "codename": "unknown"}

    registry = get_registry()
    order = [("lead_agent", roles["lead"]), ("support_agent", roles["support"])]
    if mode == "specialist":
        order = [("lead_agent", roles["lead"])]
    mapping: dict[str, str] = {agent_id: provider for agent_id, provider in order}
    role_of = {"lead_agent": "lead", "support_agent": "support"}

    # Le registre global exige ≥2 drivers pour ne pas dégrader les modes multi-agents.
    registry.register_driver("claude", _RegistryDriverAdapter(drivers["claude"]))
    registry.register_driver("gemini", _RegistryDriverAdapter(drivers["codex"]))

    pool = AgentPool()
    profile_capabilities = {"lead": ["coding", "architecture", "analysis"], "support": ["reasoning", "research", "general"]}
    for agent_id, provider in order:
        role = role_of[agent_id]
        pool.register(
            AgentProfile(
                agent_id=agent_id,
                provider=("claude" if provider == "claude" else "gemini"),
                model=f"{provider}-cli",
                capabilities=profile_capabilities[role],
            )
        )

    def invoke_agent(
        agent_id: str,
        task_type: str,
        context: str,
        session_uuid: str | None = None,
        isolated_env: dict[str, str] | None = None,
    ) -> str:
        provider = mapping.get(agent_id)
        if provider is None:
            # alias éventuel émis par un mode (ex: "claude_opus") → role par défaut
            provider = roles["lead"] if "lead" in agent_id.lower() or "opus" in agent_id.lower() else roles["support"]
        role = role_of.get(agent_id, "support")
        trace.event(
            "agent_invocation",
            role=role,
            agent_id=agent_id,
            provider=provider,
            task_type=task_type,
            context_chars=len(context),
        )
        outcome = invoke_with_retries(
            drivers[provider],
            context,
            role,
            max_retries=max_retries,
            budget=budget,
            trace=trace,
        )
        outcomes.append(outcome.to_dict())
        if not outcome.ok:
            raise RuntimeError(outcome.error or "appel agent échoué")
        return outcome.text

    engine = HybridSwarmEngine(agent_pool=pool, model_router=None, config=None, invoke_agent=invoke_agent, workspace_path=None)
    info = {
        "version": nexus_version,
        "build_seconds": round(time.time() - started, 3),
        "registry_ids": registry.get_active_builtin_ids(),
        "agent_mapping": mapping,
        "mode": mode,
    }
    trace.event("engine_built", **info)
    return {"engine": engine, "info": info, "mapping": mapping, "outcomes": outcomes, "budget": budget}


def run_mode(engine_handle: dict, task_text: str) -> dict:
    """Exécute `process_task` dans le mode demandé ; le statut retourné n'est PAS la vérité."""
    import time

    from core.intelligence.swarm.collaboration_modes import CollaborationMode

    mode_name = engine_handle["info"]["mode"]
    mode = CollaborationMode[mode_name.upper()]
    started = time.time()
    result = engine_handle["engine"].process_task(
        task_text,
        blackboard={},
        force_mode=mode,
        skip_negotiation=True,
    )
    duration = round(time.time() - started, 2)
    execution = result.execution_result
    outputs = []
    for index, response in enumerate(getattr(execution, "agent_outputs", []) or []):
        outputs.append(
            {
                "index": index,
                "agent_id": getattr(response, "agent_id", "?"),
                "role": "lead" if index == 0 else ("support" if index == 1 else f"agent{index}"),
                "status": getattr(response, "status", "?"),
                "content": getattr(response, "content", ""),
                "error": getattr(response, "error", None),
                "time_seconds": round(getattr(response, "time_seconds", 0.0), 2),
            }
        )
    analysis = result.task_analysis
    return {
        "declared_status": str(result.status),
        "selected_mode": result.selected_mode.value,
        "duration_seconds": duration,
        "analysis": {
            "complexity": getattr(analysis.complexity, "name", str(analysis.complexity)),
            "domains": [getattr(domain, "value", str(domain)) for domain in analysis.domains],
        },
        "execution_metadata": dict(execution.metadata or {}),
        "outputs": outputs,
        "final_output": execution.final_output,
    }


def summarize_engine(outputs: list[dict], declared_status: str) -> dict:
    """Transforme le résultat du moteur en faits vérifiables — sans croire son statut.

    Point clé hérité de l'audit E2E : le moteur peut rapporter ``COMPLETED`` alors qu'un
    agent a échoué. On expose donc ``engine_ok`` et ``errors`` à côté du statut déclaré.
    """
    errors = [
        {"role": output.get("role"), "agent_id": output.get("agent_id"), "error": output.get("error")}
        for output in outputs
        if output.get("status") == "error"
    ]
    declared_completed = str(declared_status).endswith("COMPLETED")
    return {
        "errors": errors,
        "engine_ok": declared_completed and not errors,
        "declared_completed": declared_completed,
        "declared_status": declared_status,
    }


def build_task_text(repo: Path, targets: list[str], test_paths: list[str]) -> str:
    """Prompt de tâche envoyé aux agents : contexte + fichiers + format de sortie strict."""
    import json

    parts: list[str] = []
    task_file = repo / "task.json"
    if task_file.is_file():
        try:
            payload = json.loads(task_file.read_text(encoding="utf-8"))
            title = payload.get("title")
            context = payload.get("context")
            if title:
                parts.append(f"TASK: {title}")
            if context:
                parts.append(f"CONTEXT: {context}")
        except (OSError, json.JSONDecodeError):
            pass
    readme = repo / "README.md"
    if readme.is_file() and not parts:
        parts.append("TASK: repair the failing tests in this repository.")
    parts.append("You must fix the source code so that the repository's test suite passes.")
    parts.append(
        "MODIFICATION POLICY: modify one or more of the existing source files listed below. "
        "For EACH file that needs a change, output exactly this format:\n"
        "--- FILE: <relative path> ---\n```python\n<COMPLETE new content of the file>\n```"
    )
    parts.append("Files allowed to change: " + ", ".join(targets))
    parts.append("")
    for target in targets:
        content = (repo / target).read_text(encoding="utf-8", errors="replace")
        parts.append(f"--- FILE: {target} (current, contains the bug) ---")
        parts.append(content.rstrip("\n"))
        parts.append(f"--- END FILE: {target} ---")
        parts.append("")
    for test_path in test_paths[:3]:
        candidate = repo / test_path
        if candidate.is_dir():
            test_files = sorted(candidate.rglob("*.py"))[:3]
        else:
            test_files = [candidate]
        for test_file in test_files:
            if not test_file.is_file():
                continue
            rel = str(test_file.relative_to(repo)).replace("\\", "/")
            parts.append(f"--- FILE: {rel} (tests, MUST NOT be modified) ---")
            parts.append(test_file.read_text(encoding="utf-8", errors="replace").rstrip("\n"))
            parts.append(f"--- END FILE: {rel} ---")
            parts.append("")
    parts.append(
        "Rules: output COMPLETE files only (no partial snippets, no diffs, no comments like 'rest unchanged'); "
        "one fenced block per file, each preceded by '--- FILE: <path> ---'; "
        "do not modify the tests; do not create new files; do not use any tools."
    )
    return "\n".join(parts)
