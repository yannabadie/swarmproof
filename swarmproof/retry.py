"""Budget d'appels modèles et politique de retry (robustesse infra CLI).

Règles v0.2 :
- un appel peut être retenté sur erreur infra (timeout, exit non nul, refus transitoire) ;
- `--max-retries` (défaut 1) : nombre de retries *par appel logique*, comptés séparément ;
- `--max-calls` : plafond global d'appels CLI réels (retries inclus) ; à épuisement,
  plus aucun appel n'est émis et le verdict devient INCONCLUSIVE (jamais PASS silencieux) ;
- tout échec définitif est journalisé (trace + run.json), jamais masqué.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from swarmproof.drivers import CLICallError
from swarmproof.trace import TraceWriter

RETRYABLE_MARKERS = (
    "timeout",
    "timed out",
    "exit=",
    "rate limit",
    "429",
    "overloaded",
    "connexion",
    "connection",
    "temporaire",
    "temporarily",
    "api error",
    "safeguard",
    "unavailable",
)


class BudgetExhausted(RuntimeError):
    """Le plafond global d'appels CLI est atteint : plus aucun appel ne sera émis."""


def is_retryable_error(message: str | None) -> bool:
    """Erreur infra/timeout justifiant un retry (tout échec CLI est traité comme infra)."""
    if not message:
        return False
    lowered = message.lower()
    return any(marker in lowered for marker in RETRYABLE_MARKERS)


@dataclass
class CallBudget:
    """Plafond global d'appels CLI réels (retries inclus)."""

    max_calls: int = 4
    used: int = 0
    exhausted_events: int = 0
    calls: list[dict] = field(default_factory=list)

    def remaining(self) -> int:
        return max(self.max_calls - self.used, 0)

    def try_consume(self, role: str) -> bool:
        if self.used >= self.max_calls:
            self.exhausted_events += 1
            return False
        self.used += 1
        self.calls.append({"index": self.used, "role": role})
        return True

    def to_dict(self) -> dict:
        return {
            "max_calls": self.max_calls,
            "used": self.used,
            "remaining": self.remaining(),
            "exhausted_events": self.exhausted_events,
        }


@dataclass
class InvocationOutcome:
    """Résultat d'un appel logique (avec ses retries éventuels)."""

    role: str
    provider: str
    text: str | None = None
    error: str | None = None
    attempts: int = 0
    retries: int = 0
    budget_exhausted: bool = False
    retry_errors: list[str] = field(default_factory=list)
    records: list[dict] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.error is None and self.text is not None

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "provider": self.provider,
            "ok": self.ok,
            "attempts": self.attempts,
            "retries": self.retries,
            "budget_exhausted": self.budget_exhausted,
            "error": self.error,
            "retry_errors": self.retry_errors,
            "records": self.records,
        }


def invoke_with_retries(
    driver,
    prompt: str,
    role: str,
    *,
    max_retries: int,
    budget: CallBudget,
    trace: TraceWriter,
) -> InvocationOutcome:
    """Appelle un driver avec retry borné et budget global ; ne lève jamais d'exception infra."""
    outcome = InvocationOutcome(role=role, provider=getattr(driver, "provider", "?"))
    attempts_allowed = max(int(max_retries), 0) + 1

    for attempt in range(1, attempts_allowed + 1):
        if not budget.try_consume(role):
            outcome.budget_exhausted = True
            outcome.error = "budget d'appels épuisé (--max-calls) : verdict INCONCLUSIVE"
            trace.event("call_budget_exhausted", role=role, max_calls=budget.max_calls, used=budget.used)
            break

        outcome.attempts = attempt
        started_records = len(getattr(driver, "records", []))
        trace.event("model_call", role=role, provider=outcome.provider, attempt=attempt, phase="start")
        try:
            text = driver.invoke(prompt, role=role)
            outcome.text = text
            outcome.error = None
            record = _last_record(driver, started_records)
            if record:
                record["attempt"] = attempt
                record["retry"] = attempt > 1
                outcome.records.append(record)
            trace.event(
                "model_call",
                role=role,
                provider=outcome.provider,
                attempt=attempt,
                phase="ok",
                output_chars=len(text or ""),
                duration_seconds=(record or {}).get("duration_seconds"),
                tokens_in=(record or {}).get("tokens_in"),
                tokens_out=(record or {}).get("tokens_out"),
                tokens_total=(record or {}).get("tokens_total"),
                cost_usd=(record or {}).get("cost_usd"),
                model=(record or {}).get("model"),
                prompt_sha256=(record or {}).get("prompt_sha256"),
            )
            break
        except CLICallError as exc:
            message = str(exc) or "erreur CLI inconnue"
            outcome.error = message
            outcome.retry_errors.append(message)
            record = _last_record(driver, started_records)
            if record:
                record["attempt"] = attempt
                record["retry"] = attempt > 1
                outcome.records.append(record)
            trace.event(
                "model_call",
                role=role,
                provider=outcome.provider,
                attempt=attempt,
                phase="error",
                error=message[:300],
                retryable=is_retryable_error(message),
            )
            if attempt < attempts_allowed and budget.remaining() > 0:
                outcome.retries += 1
                trace.event("call_retry", role=role, provider=outcome.provider, attempt=attempt + 1, reason=message[:200])
                continue
            if attempt < attempts_allowed and budget.remaining() <= 0:
                outcome.budget_exhausted = True
                trace.event(
                    "call_budget_exhausted",
                    role=role,
                    max_calls=budget.max_calls,
                    used=budget.used,
                    reason="retry impossible : plafond --max-calls atteint",
                )
            break
        except Exception as exc:  # défensif : aucune exception inattendue ne doit fuir
            outcome.error = f"{type(exc).__name__}: {exc}"
            trace.event("model_call_error", role=role, provider=outcome.provider, error=outcome.error[:300])
            break

    return outcome


def _last_record(driver, started: int) -> dict | None:
    records = getattr(driver, "records", None) or []
    if len(records) > started:
        record = records[-1]
        try:
            return record.to_dict()
        except AttributeError:
            return None
    return None
