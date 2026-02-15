import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from threading import Lock

from ai_watch.validation import (
    ValidationError,
    validate_account_payload,
    validate_budget_payload,
    validate_recommendation_payload,
    validate_service_payload,
)


DEFAULT_DB = {"services": [], "accounts": [], "usage_budgets": [], "recommendations": []}


class FileDatabase:
    def __init__(self, path: Path):
        self.path = path
        self._lock = Lock()
        self._ensure_exists()

    def _ensure_exists(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write(DEFAULT_DB)

    def _read(self) -> dict:
        with self._lock:
            with self.path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        if "services" not in data or "accounts" not in data:
            raise ValidationError("Invalid database format.")
        data.setdefault("usage_budgets", [])
        data.setdefault("recommendations", [])
        return data

    def _write(self, data: dict) -> None:
        with self._lock:
            with NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                delete=False,
                dir=str(self.path.parent),
            ) as tmp:
                json.dump(data, tmp, indent=2)
                tmp.flush()
                os.fsync(tmp.fileno())
                temp_path = tmp.name
            os.replace(temp_path, self.path)

    def get_config(self) -> dict:
        return self._read()

    def list_services(self, category: str | None = None) -> list[dict]:
        services = self._read()["services"]
        if category:
            return [svc for svc in services if svc["category"] == category]
        return services

    def get_service(self, service_id: str) -> dict | None:
        services = self._read()["services"]
        return next((svc for svc in services if svc["id"] == service_id), None)

    def create_service(self, payload: dict) -> dict:
        validate_service_payload(payload)
        data = self._read()
        if any(svc["id"] == payload["id"] for svc in data["services"]):
            raise ValidationError(f"Service '{payload['id']}' already exists.")
        data["services"].append(payload)
        self._write(data)
        return payload

    def update_service(self, service_id: str, payload: dict) -> dict:
        validate_service_payload(payload)
        if payload["id"] != service_id:
            raise ValidationError("Service ID in path and payload must match.")
        data = self._read()
        service = next((svc for svc in data["services"] if svc["id"] == service_id), None)
        if not service:
            raise ValidationError(f"Service '{service_id}' was not found.")
        service.update(payload)
        self._write(data)
        return service

    def delete_service(self, service_id: str) -> None:
        data = self._read()
        if any(acc["service_id"] == service_id for acc in data["accounts"]):
            raise ValidationError("Cannot delete a service used by an account.")
        before = len(data["services"])
        data["services"] = [svc for svc in data["services"] if svc["id"] != service_id]
        if len(data["services"]) == before:
            raise ValidationError(f"Service '{service_id}' was not found.")
        self._write(data)

    def list_accounts(self, category: str | None = None, status: str | None = None) -> list[dict]:
        data = self._read()
        services = {svc["id"]: svc for svc in data["services"]}
        accounts = data["accounts"]
        if status:
            accounts = [acc for acc in accounts if acc["status"] == status]
        if category:
            accounts = [
                acc for acc in accounts if services.get(acc["service_id"], {}).get("category") == category
            ]
        return accounts

    def get_account(self, account_id: str) -> dict | None:
        accounts = self._read()["accounts"]
        return next((acc for acc in accounts if acc["id"] == account_id), None)

    def create_account(self, payload: dict) -> dict:
        data = self._read()
        validate_account_payload(payload, data["services"])
        if any(acc["id"] == payload["id"] for acc in data["accounts"]):
            raise ValidationError(f"Account '{payload['id']}' already exists.")
        data["accounts"].append(payload)
        self._write(data)
        return payload

    def update_account(self, account_id: str, payload: dict) -> dict:
        data = self._read()
        validate_account_payload(payload, data["services"])
        if payload["id"] != account_id:
            raise ValidationError("Account ID in path and payload must match.")
        account = next((acc for acc in data["accounts"] if acc["id"] == account_id), None)
        if not account:
            raise ValidationError(f"Account '{account_id}' was not found.")
        account.update(payload)
        self._write(data)
        return account

    def delete_account(self, account_id: str) -> None:
        data = self._read()
        before = len(data["accounts"])
        data["accounts"] = [acc for acc in data["accounts"] if acc["id"] != account_id]
        if len(data["accounts"]) == before:
            raise ValidationError(f"Account '{account_id}' was not found.")
        data["usage_budgets"] = [budget for budget in data["usage_budgets"] if budget["account_id"] != account_id]
        data["recommendations"] = [
            rec for rec in data["recommendations"] if rec.get("account_id") != account_id
        ]
        self._write(data)

    def list_budgets(self) -> list[dict]:
        return self._read()["usage_budgets"]

    def get_budget(self, budget_id: str) -> dict | None:
        budgets = self._read()["usage_budgets"]
        return next((budget for budget in budgets if budget["id"] == budget_id), None)

    def create_budget(self, payload: dict) -> dict:
        data = self._read()
        validate_budget_payload(payload, data["accounts"])
        if any(budget["id"] == payload["id"] for budget in data["usage_budgets"]):
            raise ValidationError(f"Budget '{payload['id']}' already exists.")
        if any(budget["account_id"] == payload["account_id"] for budget in data["usage_budgets"]):
            raise ValidationError(f"Account '{payload['account_id']}' already has a budget.")
        data["usage_budgets"].append(payload)
        self._write(data)
        return payload

    def update_budget(self, budget_id: str, payload: dict) -> dict:
        data = self._read()
        validate_budget_payload(payload, data["accounts"])
        if payload["id"] != budget_id:
            raise ValidationError("Budget ID in path and payload must match.")
        budget = next((item for item in data["usage_budgets"] if item["id"] == budget_id), None)
        if not budget:
            raise ValidationError(f"Budget '{budget_id}' was not found.")
        for existing in data["usage_budgets"]:
            if existing["id"] != budget_id and existing["account_id"] == payload["account_id"]:
                raise ValidationError(f"Account '{payload['account_id']}' already has a budget.")
        budget.update(payload)
        self._write(data)
        return budget

    def delete_budget(self, budget_id: str) -> None:
        data = self._read()
        before = len(data["usage_budgets"])
        data["usage_budgets"] = [budget for budget in data["usage_budgets"] if budget["id"] != budget_id]
        if len(data["usage_budgets"]) == before:
            raise ValidationError(f"Budget '{budget_id}' was not found.")
        self._write(data)

    def list_recommendations(self) -> list[dict]:
        return sorted(self._read()["recommendations"], key=lambda rec: rec["priority"])

    def get_recommendation(self, recommendation_id: str) -> dict | None:
        recommendations = self._read()["recommendations"]
        return next((rec for rec in recommendations if rec["id"] == recommendation_id), None)

    def create_recommendation(self, payload: dict) -> dict:
        data = self._read()
        validate_recommendation_payload(payload, data["accounts"], data["services"])
        if any(rec["id"] == payload["id"] for rec in data["recommendations"]):
            raise ValidationError(f"Recommendation '{payload['id']}' already exists.")
        data["recommendations"].append(payload)
        self._write(data)
        return payload

    def update_recommendation(self, recommendation_id: str, payload: dict) -> dict:
        data = self._read()
        validate_recommendation_payload(payload, data["accounts"], data["services"])
        if payload["id"] != recommendation_id:
            raise ValidationError("Recommendation ID in path and payload must match.")
        recommendation = next(
            (rec for rec in data["recommendations"] if rec["id"] == recommendation_id), None
        )
        if not recommendation:
            raise ValidationError(f"Recommendation '{recommendation_id}' was not found.")
        recommendation.update(payload)
        self._write(data)
        return recommendation

    def delete_recommendation(self, recommendation_id: str) -> None:
        data = self._read()
        before = len(data["recommendations"])
        data["recommendations"] = [
            rec for rec in data["recommendations"] if rec["id"] != recommendation_id
        ]
        if len(data["recommendations"]) == before:
            raise ValidationError(f"Recommendation '{recommendation_id}' was not found.")
        self._write(data)

    def dashboard_summary(self) -> dict:
        data = self._read()
        service_by_id = {svc["id"]: svc for svc in data["services"]}
        budgets_by_account_id = {
            budget["account_id"]: budget for budget in data["usage_budgets"]
        }
        active_accounts = [acc for acc in data["accounts"] if acc["status"] == "active"]
        total = round(sum(acc["monthly_cost_usd"] for acc in active_accounts), 2)
        breakdown = {"coding": 0.0, "art": 0.0, "music": 0.0, "general": 0.0}
        budget_alerts = []
        for account in active_accounts:
            category = service_by_id.get(account["service_id"], {}).get("category", "general")
            breakdown[category] += account["monthly_cost_usd"]
            budget = budgets_by_account_id.get(account["id"])
            if budget and budget["monthly_budget_usd"] > 0:
                percent = round((budget["current_month_spend_usd"] / budget["monthly_budget_usd"]) * 100, 2)
                if percent >= budget["alert_threshold_percent"]:
                    budget_alerts.append(
                        {
                            "account_id": account["id"],
                            "email": account["email"],
                            "percent_used": percent,
                        }
                    )
        breakdown = {key: round(value, 2) for key, value in breakdown.items()}
        return {
            "total_monthly_spend_usd": total,
            "category_breakdown_usd": breakdown,
            "budget_alerts": budget_alerts,
        }
