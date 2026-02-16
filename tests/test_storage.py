import json
import tempfile
import unittest
from pathlib import Path

from ai_watch.storage import FileDatabase
from ai_watch.validation import ValidationError


def sample_service() -> dict:
    return {
        "id": "chatgpt_plus",
        "name": "ChatGPT Plus",
        "category": "general",
        "provider": "OpenAI",
        "website_url": "https://chatgpt.com",
        "docs_url": "https://platform.openai.com/docs",
        "billing_url": "https://platform.openai.com/settings/billing",
    }


def sample_account() -> dict:
    return {
        "id": "acc_1",
        "service_id": "chatgpt_plus",
        "email": "owner@example.com",
        "plan_name": "Plus",
        "monthly_cost_usd": 20.0,
        "renewal_day": 3,
        "status": "active",
        "notes": "Primary prompt service.",
        "tags": ["general", "prompt_engineer"],
    }


def sample_budget() -> dict:
    return {
        "id": "bud_1",
        "account_id": "acc_1",
        "monthly_budget_usd": 30.0,
        "alert_threshold_percent": 80.0,
        "current_month_spend_usd": 25.0,
    }


def sample_recommendation() -> dict:
    return {
        "id": "rec_1",
        "account_id": "acc_1",
        "service_id": None,
        "title": "When to use this account",
        "body": "Use this for deep coding sessions.",
        "priority": 1,
    }


class FileDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "db.json"
        self.db = FileDatabase(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_initializes_file_with_expected_shape(self):
        with self.db_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        self.assertEqual(
            payload,
            {"services": [], "accounts": [], "usage_budgets": [], "recommendations": []},
        )

    def test_create_and_get_service(self):
        created = self.db.create_service(sample_service())
        found = self.db.get_service(created["id"])
        self.assertEqual(found, created)

    def test_rejects_duplicate_service_id(self):
        self.db.create_service(sample_service())
        with self.assertRaises(ValidationError):
            self.db.create_service(sample_service())

    def test_create_and_filter_accounts(self):
        self.db.create_service(sample_service())
        active = sample_account()
        paused = {**sample_account(), "id": "acc_2", "status": "paused"}
        self.db.create_account(active)
        self.db.create_account(paused)

        all_accounts = self.db.list_accounts()
        active_accounts = self.db.list_accounts(status="active")
        general_accounts = self.db.list_accounts(category="general")

        self.assertEqual(len(all_accounts), 2)
        self.assertEqual(len(active_accounts), 1)
        self.assertEqual(len(general_accounts), 2)

    def test_dashboard_summary_uses_active_accounts_only(self):
        self.db.create_service(sample_service())
        self.db.create_account(sample_account())
        paused = {**sample_account(), "id": "acc_2", "status": "paused", "monthly_cost_usd": 50.0}
        self.db.create_account(paused)

        summary = self.db.dashboard_summary()

        self.assertEqual(summary["total_monthly_spend_usd"], 20.0)
        self.assertEqual(summary["category_breakdown_usd"]["general"], 20.0)

    def test_rejects_password_fields(self):
        bad_service = {**sample_service(), "password_hint": "secret"}
        with self.assertRaises(ValidationError):
            self.db.create_service(bad_service)

    def test_rejects_unknown_service_on_account(self):
        with self.assertRaises(ValidationError):
            self.db.create_account(sample_account())

    def test_delete_service_restricted_when_accounts_exist(self):
        self.db.create_service(sample_service())
        self.db.create_account(sample_account())
        with self.assertRaises(ValidationError):
            self.db.delete_service("chatgpt_plus")

    def test_update_account(self):
        self.db.create_service(sample_service())
        self.db.create_account(sample_account())
        updated = {**sample_account(), "monthly_cost_usd": 22.0}
        self.db.update_account("acc_1", updated)
        found = self.db.get_account("acc_1")
        self.assertEqual(found["monthly_cost_usd"], 22.0)

    def test_create_update_budget_and_budget_alert(self):
        self.db.create_service(sample_service())
        self.db.create_account(sample_account())
        self.db.create_budget(sample_budget())

        updated = {**sample_budget(), "current_month_spend_usd": 28.0}
        self.db.update_budget("bud_1", updated)
        found = self.db.get_budget("bud_1")
        self.assertEqual(found["current_month_spend_usd"], 28.0)

        summary = self.db.dashboard_summary()
        self.assertEqual(len(summary["budget_alerts"]), 1)
        self.assertEqual(summary["budget_alerts"][0]["account_id"], "acc_1")

    def test_rejects_budget_when_account_missing(self):
        with self.assertRaises(ValidationError):
            self.db.create_budget(sample_budget())

    def test_create_and_list_recommendations(self):
        self.db.create_service(sample_service())
        self.db.create_account(sample_account())
        self.db.create_recommendation(sample_recommendation())
        recs = self.db.list_recommendations()
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["id"], "rec_1")

    def test_recommendation_requires_target(self):
        self.db.create_service(sample_service())
        self.db.create_account(sample_account())
        payload = {**sample_recommendation(), "account_id": None, "service_id": None}
        with self.assertRaises(ValidationError):
            self.db.create_recommendation(payload)

    def test_replace_config(self):
        payload = {
            "services": [sample_service()],
            "accounts": [sample_account()],
            "usage_budgets": [sample_budget()],
            "recommendations": [sample_recommendation()],
        }
        self.db.replace_config(payload)
        summary = self.db.dashboard_summary()
        self.assertEqual(summary["total_monthly_spend_usd"], 20.0)
        self.assertEqual(len(self.db.list_recommendations()), 1)


if __name__ == "__main__":
    unittest.main()
