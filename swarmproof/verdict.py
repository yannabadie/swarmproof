"""Calcul du verdict SwarmProof v0.2.

Trois verdicts seulement :
- PASS          : l'oracle externe a exécuté au moins un candidat et il passe ;
- FAIL          : l'oracle a jugé au moins un candidat et aucun ne passe (échec réel) ;
- INCONCLUSIVE  : impossible de juger — erreur infra définitive, budget d'appels épuisé,
                  aucun candidat exploitable produit par les agents, ou oracle en timeout.

Le statut auto-déclaré du moteur NEXUS n'entre jamais dans ce calcul.
"""

from __future__ import annotations

VERDICT_PASS = "PASS"
VERDICT_FAIL = "FAIL"
VERDICT_INCONCLUSIVE = "INCONCLUSIVE"
VERDICT_DRY_RUN = "DRY_RUN"


def compute_verdict(
    *,
    dry_run: bool = False,
    attempts: list[dict] | None = None,
    engine_errors: list[dict] | None = None,
    agent_calls_ok: int = 0,
    candidate_sets_found: int = 0,
    rejected_candidate_sets: int = 0,
    budget_exhausted: bool = False,
    oracle_timed_out: bool = False,
) -> dict:
    """Retourne `{"verdict", "reason", "basis", "explain"}` — jamais de PASS silencieux."""
    attempts = attempts or []
    engine_errors = engine_errors or []
    judged = [attempt for attempt in attempts if not attempt.get("simulated")]
    passed = [attempt for attempt in judged if attempt.get("passed") and attempt.get("execution_verified", True)]
    unverified = [attempt for attempt in judged if attempt.get("execution_verified") is False]
    timed_out_attempts = [attempt for attempt in judged if attempt.get("timed_out")]
    genuine = [attempt for attempt in judged if not attempt.get("timed_out")]

    if dry_run:
        return {
            "verdict": VERDICT_DRY_RUN,
            "reason": "simulation dry-run : aucun verdict réel",
            "basis": "simulated",
            "explain": ["exécution simulée sans modèle ni oracle réels"],
        }

    if passed:
        return {
            "verdict": VERDICT_PASS,
            "reason": f"oracle PASS sur la tentative {passed[0].get('attempt')}",
            "basis": "oracle",
            "explain": [
                f"{len(judged)} candidat(s) jugé(s) par l'oracle externe",
                f"{len(passed)} tentative(s) PASS",
            ],
        }

    reasons: list[str] = []
    if unverified:
        reasons.append(
            f"{len(unverified)} tentative(s) avec exit 0 SANS preuve d'exécution de tests "
            "— possible contournement de l'oracle, non concluant"
        )
    if oracle_timed_out or timed_out_attempts:
        reasons.append("oracle en timeout : résultat non concluant")
    if engine_errors:
        reasons.append(
            f"{len(engine_errors)} agent(s) NEXUS en échec définitif : "
            + "; ".join(f"{error.get('role')}: {str(error.get('error'))[:120]}" for error in engine_errors)
        )
    if budget_exhausted:
        reasons.append("budget d'appels (--max-calls) épuisé avant jugement exploitable")
    if agent_calls_ok == 0 and not judged:
        reasons.append("aucun appel agent n'a abouti : impossible de produire un correctif")
    if candidate_sets_found == 0 and agent_calls_ok > 0:
        reasons.append("aucun correctif exploitable produit par les agents")
    if rejected_candidate_sets > 0 and not judged:
        reasons.append(f"{rejected_candidate_sets} proposition(s) rejetée(s) (partielle/ambiguë/hors cible)")
    if not reasons:
        reasons.append(
            "impossible de conclure : aucun résultat d'oracle exploitable "
            f"(tentatives={len(judged)})"
        )

    # Un exit 0 sans preuve de tests n'est pas un échec de code mais une preuve manquante.
    if unverified and not [attempt for attempt in judged if attempt.get("execution_verified", True)]:
        return {
            "verdict": VERDICT_INCONCLUSIVE,
            "reason": "oracle exit 0 sans preuve d'exécution de tests (tests_run/parseur absents) : contournement possible, aucun PASS",
            "basis": "infrastructure",
            "explain": reasons,
        }

    # Un timeout oracle ne produit pas de jugement exploitable → INCONCLUSIVE, jamais FAIL silencieux.
    if timed_out_attempts and not genuine:
        return {
            "verdict": VERDICT_INCONCLUSIVE,
            "reason": "oracle en timeout : aucun verdict exploitable",
            "basis": "infrastructure",
            "explain": reasons + [f"{len(timed_out_attempts)} tentative(s) oracle en timeout"],
        }

    # Si l'oracle a réellement jugé au moins un candidat complet et l'a refusé, c'est un FAIL.
    if genuine:
        return {
            "verdict": VERDICT_FAIL,
            "reason": f"oracle FAIL sur {len(judged)} tentative(s) — aucune ne passe",
            "basis": "oracle",
            "explain": reasons + [f"{len(judged)} tentative(s) jugée(s), 0 PASS"],
        }

    return {
        "verdict": VERDICT_INCONCLUSIVE,
        "reason": " ; ".join(reasons),
        "basis": "infrastructure",
        "explain": reasons,
    }
