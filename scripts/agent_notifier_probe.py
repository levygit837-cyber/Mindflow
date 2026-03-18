#!/usr/bin/env python3
"""Probe MindFlow agent streaming outputs for notifier/UI mapping.

This script:
1. Creates three isolated fixture codebases under /tmp.
2. Sends real SSE requests to the running MindFlow backend.
3. Captures raw stream events per scenario.
4. Produces per-scenario and aggregate summaries for UI notifier analysis.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import textwrap
import time
import urllib.error
import uuid
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_BASE_URL = "http://127.0.0.1:8000/v1/agent/chat/stream"
DEFAULT_FIXTURE_ROOT = Path("/tmp/mindflow-agent-notifier-lab")


@dataclass(frozen=True)
class Scenario:
    name: str
    prompt: str
    files: dict[str, str]


def _dedent(value: str) -> str:
    return textwrap.dedent(value).strip() + "\n"


SCENARIOS: list[Scenario] = [
    Scenario(
        name="easy",
        prompt=(
            "Analise este diretório pequeno e identifique por que o total final está incorreto. "
            "Aponte o arquivo e a função responsáveis. Se ajudar, confira o teste. "
            "Não modifique nada."
        ),
        files={
            "README.md": _dedent(
                """
                # Easy Fixture

                Regra de negócio:
                - total = subtotal + tax - discount
                - o desconto sempre reduz o valor final
                """
            ),
            "app/__init__.py": "",
            "app/calculator.py": _dedent(
                """
                def calculate_invoice_total(subtotal: float, tax: float, discount: float) -> float:
                    gross = subtotal + tax
                    return round(gross + discount, 2)
                """
            ),
            "tests/test_calculator.py": _dedent(
                """
                from app.calculator import calculate_invoice_total


                def test_calculate_invoice_total_subtracts_discount() -> None:
                    assert calculate_invoice_total(100.0, 10.0, 5.0) == 105.0
                """
            ),
        },
    ),
    Scenario(
        name="medium",
        prompt=(
            "Analise esta codebase e explique por que o desconto premium sai errado para clientes "
            "legacy da região BR. Use o README e o contexto do diretório antes de concluir. "
            "Se precisar confirmar a hipótese, rode os testes. Não altere arquivos."
        ),
        files={
            "README.md": _dedent(
                """
                # Medium Fixture

                Contexto:
                - clientes premium recebem desconto base por plano
                - clientes legacy da região BR mantêm bônus regional negociado
                - o bônus regional só deve ser desligado quando DISABLE_LEGACY_BONUS=True
                """
            ),
            "docs/context.md": _dedent(
                """
                # Pricing Context

                Regras críticas:
                1. Plano premium = 10% de desconto base
                2. Região BR = +2% de bônus regional
                3. Contratos legacy na BR = +5% adicionais
                4. O item 3 só pode ser removido por config explícita
                """
            ),
            "app/__init__.py": "",
            "app/config.py": _dedent(
                """
                DISABLE_LEGACY_BONUS = False
                """
            ),
            "app/pricing/__init__.py": "",
            "app/pricing/models.py": _dedent(
                """
                from dataclasses import dataclass


                @dataclass(frozen=True)
                class Quote:
                    subtotal: float
                    plan: str
                    region: str
                    legacy_contract: bool
                """
            ),
            "app/pricing/helpers.py": _dedent(
                """
                def normalize_region(region: str) -> str:
                    return region.strip().upper()
                """
            ),
            "app/pricing/rules.py": _dedent(
                """
                from app.config import DISABLE_LEGACY_BONUS
                from app.pricing.helpers import normalize_region
                from app.pricing.models import Quote


                def base_discount(quote: Quote) -> int:
                    return 10 if quote.plan == "premium" else 0


                def regional_bonus(quote: Quote) -> int:
                    region = normalize_region(quote.region)
                    if region == "BR" and quote.legacy_contract:
                        if DISABLE_LEGACY_BONUS:
                            return 0
                        return 0
                    if region == "BR":
                        return 2
                    return 0


                def final_discount_percentage(quote: Quote) -> int:
                    return base_discount(quote) + regional_bonus(quote)
                """
            ),
            "app/pricing/service.py": _dedent(
                """
                from app.pricing.models import Quote
                from app.pricing.rules import final_discount_percentage


                def final_price(quote: Quote) -> float:
                    discount = final_discount_percentage(quote)
                    return round(quote.subtotal * (1 - discount / 100), 2)
                """
            ),
            "tests/test_pricing_service.py": _dedent(
                """
                from app.pricing.models import Quote
                from app.pricing.service import final_price


                def test_legacy_br_premium_keeps_negotiated_bonus() -> None:
                    quote = Quote(subtotal=100.0, plan="premium", region="br", legacy_contract=True)
                    assert final_price(quote) == 83.0
                """
            ),
        },
    ),
    Scenario(
        name="hard",
        prompt=(
            "Analise esta codebase maior para descobrir por que contas enterprise perdem o add-on "
            "`priority_support` após invoice renewal. Mapeie o fluxo end-to-end, leia os arquivos "
            "necessários, e rode os testes relevantes para confirmar a hipótese. Não modifique nada; "
            "quero causa raiz, evidências e correção mínima sugerida."
        ),
        files={
            "README.md": _dedent(
                """
                # Hard Fixture

                Pipeline de renovação:
                1. API recebe renewal request
                2. RenewalService carrega conta e invoice
                3. InvoiceService normaliza invoice lines
                4. FeatureMapper traduz SKUs em entitlements
                5. AddOnPolicy decide quais add-ons permanecem
                6. AccountRepository persiste o snapshot final

                Incidente:
                - contas enterprise perdem `priority_support` após renovação
                - reproduz com invoices sem metadata explícita de preservação
                """
            ),
            "docs/incident.md": _dedent(
                """
                # Incident Note

                Sintoma:
                - plano principal continua correto
                - add-ons contratados antes da renovação desaparecem
                - comportamento esperado: preservar add-ons quando a flag global
                  PRESERVE_ADD_ONS_ON_RENEWAL estiver ativa
                """
            ),
            "pyproject.toml": _dedent(
                """
                [tool.pytest.ini_options]
                testpaths = ["tests"]
                """
            ),
            "app/__init__.py": "",
            "app/bootstrap.py": _dedent(
                """
                from app.api.renewal_controller import RenewalController
                from app.repositories.account_repo import AccountRepository
                from app.repositories.audit_repo import AuditRepository
                from app.repositories.invoice_repo import InvoiceRepository
                from app.services.invoice_service import InvoiceService
                from app.services.renewal_service import RenewalService


                def build_controller() -> RenewalController:
                    account_repo = AccountRepository()
                    invoice_repo = InvoiceRepository()
                    audit_repo = AuditRepository()
                    invoice_service = InvoiceService()
                    renewal_service = RenewalService(
                        account_repo=account_repo,
                        invoice_repo=invoice_repo,
                        invoice_service=invoice_service,
                        audit_repo=audit_repo,
                    )
                    return RenewalController(renewal_service=renewal_service)
                """
            ),
            "app/events.py": _dedent(
                """
                RENEWAL_STARTED = "renewal.started"
                RENEWAL_COMPLETED = "renewal.completed"
                ENTITLEMENTS_SAVED = "entitlements.saved"
                """
            ),
            "app/feature_flags.py": _dedent(
                """
                PRESERVE_ADD_ONS_ON_RENEWAL = True
                """
            ),
            "app/api/__init__.py": "",
            "app/api/renewal_controller.py": _dedent(
                """
                from app.services.renewal_service import RenewalService


                class RenewalController:
                    def __init__(self, renewal_service: RenewalService) -> None:
                        self._renewal_service = renewal_service

                    def renew(self, account_id: str):
                        return self._renewal_service.renew(account_id)
                """
            ),
            "app/domain/__init__.py": "",
            "app/domain/account.py": _dedent(
                """
                from dataclasses import dataclass, field


                @dataclass
                class Account:
                    account_id: str
                    plan_features: list[str]
                    add_ons: list[str] = field(default_factory=list)
                """
            ),
            "app/domain/entitlements.py": _dedent(
                """
                from dataclasses import dataclass


                @dataclass(frozen=True)
                class EntitlementsSnapshot:
                    plan_features: list[str]
                    add_ons: list[str]
                """
            ),
            "app/domain/invoice.py": _dedent(
                """
                from dataclasses import dataclass, field


                @dataclass(frozen=True)
                class InvoiceLine:
                    sku: str
                    kind: str = "feature"


                @dataclass(frozen=True)
                class Invoice:
                    account_id: str
                    lines: list[InvoiceLine]
                    metadata: dict[str, bool] = field(default_factory=dict)
                """
            ),
            "app/repositories/__init__.py": "",
            "app/repositories/account_repo.py": _dedent(
                """
                from app.domain.account import Account
                from app.domain.entitlements import EntitlementsSnapshot


                class AccountRepository:
                    def __init__(self) -> None:
                        self._accounts = {
                            "acct-enterprise-1": Account(
                                account_id="acct-enterprise-1",
                                plan_features=["api_access", "analytics_dashboard"],
                                add_ons=["priority_support"],
                            )
                        }
                        self._snapshots: dict[str, EntitlementsSnapshot] = {}

                    def get(self, account_id: str) -> Account:
                        return self._accounts[account_id]

                    def save_entitlements(self, account_id: str, snapshot: EntitlementsSnapshot) -> None:
                        self._snapshots[account_id] = snapshot
                """
            ),
            "app/repositories/invoice_repo.py": _dedent(
                """
                from app.domain.invoice import Invoice, InvoiceLine


                class InvoiceRepository:
                    def latest_for(self, account_id: str) -> Invoice:
                        return Invoice(
                            account_id=account_id,
                            lines=[
                                InvoiceLine("core.api"),
                                InvoiceLine("core.analytics"),
                            ],
                            metadata={},
                        )
                """
            ),
            "app/repositories/audit_repo.py": _dedent(
                """
                class AuditRepository:
                    def __init__(self) -> None:
                        self.records: list[dict[str, object]] = []

                    def record(self, event: str, payload: dict[str, object]) -> None:
                        self.records.append({"event": event, "payload": payload})
                """
            ),
            "app/services/__init__.py": "",
            "app/services/add_on_policy.py": _dedent(
                """
                def merge_add_ons(mapped_features: list[str], existing_add_ons: list[str], *, preserve: bool) -> list[str]:
                    if preserve:
                        return sorted(set(mapped_features + existing_add_ons))
                    return sorted(mapped_features)
                """
            ),
            "app/services/feature_mapper.py": _dedent(
                """
                from app.domain.invoice import Invoice


                SKU_TO_FEATURE = {
                    "core.api": "api_access",
                    "core.analytics": "analytics_dashboard",
                    "addon.support.priority": "priority_support",
                }


                def map_invoice_features(invoice: Invoice) -> list[str]:
                    mapped: list[str] = []
                    for line in invoice.lines:
                        if line.kind != "feature":
                            continue
                        feature = SKU_TO_FEATURE.get(line.sku)
                        if feature:
                            mapped.append(feature)
                    return mapped
                """
            ),
            "app/services/invoice_service.py": _dedent(
                """
                from app.domain.invoice import Invoice


                class InvoiceService:
                    def normalize(self, invoice: Invoice) -> Invoice:
                        return invoice
                """
            ),
            "app/services/renewal_service.py": _dedent(
                """
                from app.domain.entitlements import EntitlementsSnapshot
                from app.events import ENTITLEMENTS_SAVED, RENEWAL_COMPLETED, RENEWAL_STARTED
                from app.feature_flags import PRESERVE_ADD_ONS_ON_RENEWAL
                from app.services.add_on_policy import merge_add_ons
                from app.services.feature_mapper import map_invoice_features


                class RenewalService:
                    def __init__(self, account_repo, invoice_repo, invoice_service, audit_repo) -> None:
                        self._account_repo = account_repo
                        self._invoice_repo = invoice_repo
                        self._invoice_service = invoice_service
                        self._audit_repo = audit_repo

                    def renew(self, account_id: str) -> EntitlementsSnapshot:
                        self._audit_repo.record(RENEWAL_STARTED, {"account_id": account_id})

                        account = self._account_repo.get(account_id)
                        invoice = self._invoice_service.normalize(self._invoice_repo.latest_for(account_id))
                        mapped_features = map_invoice_features(invoice)

                        preserve_add_ons = invoice.metadata.get(
                            "preserve_add_ons",
                            False if PRESERVE_ADD_ONS_ON_RENEWAL else False,
                        )
                        final_add_ons = merge_add_ons(
                            mapped_features=[],
                            existing_add_ons=account.add_ons,
                            preserve=preserve_add_ons,
                        )

                        snapshot = EntitlementsSnapshot(
                            plan_features=sorted(set(account.plan_features + mapped_features)),
                            add_ons=final_add_ons,
                        )
                        self._account_repo.save_entitlements(account_id, snapshot)
                        self._audit_repo.record(ENTITLEMENTS_SAVED, {"account_id": account_id, "snapshot": snapshot})
                        self._audit_repo.record(RENEWAL_COMPLETED, {"account_id": account_id})
                        return snapshot
                """
            ),
            "tests/test_feature_mapper.py": _dedent(
                """
                from app.domain.invoice import Invoice, InvoiceLine
                from app.services.feature_mapper import map_invoice_features


                def test_feature_mapper_understands_priority_support_sku() -> None:
                    invoice = Invoice(
                        account_id="acct-enterprise-1",
                        lines=[InvoiceLine("addon.support.priority")],
                    )
                    assert map_invoice_features(invoice) == ["priority_support"]
                """
            ),
            "tests/test_renewal_service.py": _dedent(
                """
                from app.repositories.account_repo import AccountRepository
                from app.repositories.audit_repo import AuditRepository
                from app.repositories.invoice_repo import InvoiceRepository
                from app.services.invoice_service import InvoiceService
                from app.services.renewal_service import RenewalService


                def test_renewal_preserves_existing_priority_support_add_on() -> None:
                    service = RenewalService(
                        account_repo=AccountRepository(),
                        invoice_repo=InvoiceRepository(),
                        invoice_service=InvoiceService(),
                        audit_repo=AuditRepository(),
                    )

                    snapshot = service.renew("acct-enterprise-1")

                    assert "priority_support" in snapshot.add_ons
                """
            ),
        },
    ),
]


def write_fixture(root: Path, files: dict[str, str]) -> None:
    if root.exists():
        shutil.rmtree(root)
    for relative_path, content in files.items():
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def parse_sse_events(
    base_url: str,
    payload: dict[str, Any],
    *,
    total_timeout_seconds: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    started_at = time.time()
    events: list[dict[str, Any]] = []
    payload_json = json.dumps(payload, ensure_ascii=False)

    try:
        command = [
            "curl",
            "-sS",
            "-N",
            "--max-time",
            str(total_timeout_seconds),
            "-H",
            "Content-Type: application/json",
            "-H",
            "Accept: text/event-stream",
            "-d",
            payload_json,
            base_url,
        ]
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )

        for line in completed.stdout.splitlines():
            if not line.startswith("data: "):
                continue
            event = json.loads(line[6:])
            events.append(event)

        if completed.returncode == 0:
            status = "ok"
        elif completed.returncode == 28:
            status = "timeout"
        else:
            status = "runtime_error"

        meta: dict[str, Any] = {
            "status": status,
            "duration_seconds": round(time.time() - started_at, 3),
            "curl_exit_code": completed.returncode,
        }
        if completed.stderr.strip():
            meta["error"] = completed.stderr.strip()
        return events, meta
    except urllib.error.HTTPError as exc:  # pragma: no cover - compatibility fallback
        body = exc.read().decode("utf-8", "replace")
        return events, {
            "status": "http_error",
            "http_status": exc.code,
            "duration_seconds": round(time.time() - started_at, 3),
            "error": body,
        }
    except Exception as exc:  # pragma: no cover - probe script
        return events, {
            "status": "runtime_error",
            "duration_seconds": round(time.time() - started_at, 3),
            "error": str(exc),
        }


def _safe_json_loads(raw: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(raw)
    except Exception:
        return None
    return parsed if isinstance(parsed, dict) else None


def summarize_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    event_types = Counter()
    agents = Counter()
    tool_calls = Counter()
    tool_results = Counter()
    notifier_kinds = Counter()
    response_categories = Counter()
    statuses = Counter()
    delegation_targets = Counter()
    errors: list[str] = []
    first_response_seq: int | None = None

    for event in events:
        event_type = str(event.get("type", "unknown"))
        event_types[event_type] += 1

        meta = event.get("meta") or {}
        if isinstance(meta, dict):
            agent = meta.get("agent")
            status = meta.get("status")
            category = meta.get("category")
            if agent:
                agents[str(agent)] += 1
            if status:
                statuses[str(status)] += 1
            if category and event_type == "response":
                response_categories[str(category)] += 1

        if first_response_seq is None and event_type == "response":
            first_response_seq = int(event.get("seq", 0))

        payload = _safe_json_loads(str(event.get("data", "")))
        if event_type == "tool_call" and payload:
            tool_calls[str(payload.get("name") or payload.get("tool") or "unknown")] += 1
        elif event_type == "tool_result" and payload:
            tool_results[str(payload.get("name") or payload.get("tool") or "unknown")] += 1
        elif event_type == "notifier" and payload:
            notifier_kinds[str(payload.get("kind") or payload.get("category") or "unknown")] += 1
        elif event_type == "agent_delegation_start" and payload:
            delegation_targets[str(payload.get("agent_type") or "unknown")] += 1
        elif event_type == "error":
            errors.append(str(event.get("data", "")))

    return {
        "total_events": len(events),
        "event_type_counts": dict(event_types.most_common()),
        "agent_event_counts": dict(agents.most_common()),
        "tool_call_counts": dict(tool_calls.most_common()),
        "tool_result_counts": dict(tool_results.most_common()),
        "notifier_kind_counts": dict(notifier_kinds.most_common()),
        "response_category_counts": dict(response_categories.most_common()),
        "status_counts": dict(statuses.most_common()),
        "delegation_targets": dict(delegation_targets.most_common()),
        "error_messages": errors,
        "first_response_seq": first_response_seq,
    }


def aggregate_summaries(results: list[dict[str, Any]]) -> dict[str, Any]:
    aggregate_event_types = Counter()
    aggregate_tool_calls = Counter()
    aggregate_notifier_kinds = Counter()
    aggregate_agents = Counter()
    scenario_totals: dict[str, int] = {}

    for result in results:
        name = result["scenario"]
        summary = result["summary"]
        scenario_totals[name] = summary["total_events"]
        aggregate_event_types.update(summary["event_type_counts"])
        aggregate_tool_calls.update(summary["tool_call_counts"])
        aggregate_notifier_kinds.update(summary["notifier_kind_counts"])
        aggregate_agents.update(summary["agent_event_counts"])

    return {
        "scenario_totals": scenario_totals,
        "common_event_types": dict(aggregate_event_types.most_common()),
        "common_tool_calls": dict(aggregate_tool_calls.most_common()),
        "common_notifier_kinds": dict(aggregate_notifier_kinds.most_common()),
        "common_agents": dict(aggregate_agents.most_common()),
    }


def run_probe(
    base_url: str,
    output_root: Path,
    fixture_root: Path,
    total_timeout_seconds: int,
) -> dict[str, Any]:
    fixture_root.mkdir(parents=True, exist_ok=True)
    output_root.mkdir(parents=True, exist_ok=True)

    run_dir = output_root / time.strftime("agent-notifier-probe-%Y%m%d-%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []

    for scenario in SCENARIOS:
        scenario_root = fixture_root / scenario.name
        write_fixture(scenario_root, scenario.files)

        payload = {
            "message": scenario.prompt,
            "session_id": f"probe-{scenario.name}-{uuid.uuid4().hex[:8]}",
            "orchestrate": True,
            "folder_path": str(scenario_root),
        }
        events, request_meta = parse_sse_events(
            base_url,
            payload,
            total_timeout_seconds=total_timeout_seconds,
        )
        summary = summarize_events(events)

        scenario_dir = run_dir / scenario.name
        scenario_dir.mkdir(parents=True, exist_ok=True)
        (scenario_dir / "prompt.txt").write_text(scenario.prompt + "\n", encoding="utf-8")
        (scenario_dir / "request.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (scenario_dir / "events.json").write_text(
            json.dumps(events, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (scenario_dir / "summary.json").write_text(
            json.dumps({"request_meta": request_meta, **summary}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        results.append(
            {
                "scenario": scenario.name,
                "fixture_root": str(scenario_root),
                "request_meta": request_meta,
                "summary": summary,
            }
        )

    aggregate = aggregate_summaries(results)
    probe_summary = {
        "base_url": base_url,
        "fixture_root": str(fixture_root),
        "run_dir": str(run_dir),
        "results": results,
        "aggregate": aggregate,
    }

    (run_dir / "aggregate-summary.json").write_text(
        json.dumps(probe_summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    return probe_summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Probe MindFlow notifier/event outputs.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument(
        "--output-root",
        default=str(Path("/home/levybonito/Projetos/MindFlow/docs/analysis")),
    )
    parser.add_argument("--fixture-root", default=str(DEFAULT_FIXTURE_ROOT))
    parser.add_argument("--total-timeout-seconds", type=int, default=180)
    args = parser.parse_args()

    summary = run_probe(
        base_url=args.base_url,
        output_root=Path(args.output_root),
        fixture_root=Path(args.fixture_root),
        total_timeout_seconds=args.total_timeout_seconds,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
