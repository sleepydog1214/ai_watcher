import json
import tempfile
import unittest

from ai_watch import create_app


def sample_service() -> dict:
    return {
        "id": "claude_code_pro",
        "name": "Claude Code Pro",
        "category": "coding",
        "provider": "Anthropic",
        "website_url": "https://claude.ai",
        "docs_url": "https://docs.anthropic.com",
        "billing_url": "https://claude.ai/settings/billing",
    }


def sample_account() -> dict:
    return {
        "id": "acc_77",
        "service_id": "claude_code_pro",
        "email": "builder@example.com",
        "plan_name": "Pro",
        "monthly_cost_usd": 17.0,
        "renewal_day": 10,
        "status": "active",
        "notes": "Repo scale edits",
        "tags": ["coding", "deep_repo"],
    }


def sample_budget() -> dict:
    return {
        "id": "bud_77",
        "account_id": "acc_77",
        "monthly_budget_usd": 30.0,
        "alert_threshold_percent": 80.0,
        "current_month_spend_usd": 26.0,
    }


def sample_recommendation() -> dict:
    return {
        "id": "rec_77",
        "account_id": "acc_77",
        "service_id": None,
        "title": "Coding workflow",
        "body": "Use this account for multi-file edits.",
        "priority": 1,
    }


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = f"{self.temp_dir.name}\\db.json"
        self.app = create_app(db_path)
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_health_endpoint(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "ok"})

    def test_create_service_and_account_then_fetch_dashboard(self):
        service_response = self.client.post("/api/services", json=sample_service())
        account_response = self.client.post("/api/accounts", json=sample_account())
        dashboard_response = self.client.get("/api/dashboard")

        self.assertEqual(service_response.status_code, 201)
        self.assertEqual(account_response.status_code, 201)
        self.assertEqual(dashboard_response.status_code, 200)
        dashboard = dashboard_response.get_json()
        self.assertEqual(dashboard["total_monthly_spend_usd"], 17.0)
        self.assertEqual(dashboard["category_breakdown_usd"]["coding"], 17.0)

    def test_filter_accounts_by_status(self):
        self.client.post("/api/services", json=sample_service())
        self.client.post("/api/accounts", json=sample_account())
        paused = {**sample_account(), "id": "acc_88", "status": "paused"}
        self.client.post("/api/accounts", json=paused)

        response = self.client.get("/api/accounts?status=active")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.get_json()), 1)

    def test_reject_password_field_from_api(self):
        bad_payload = {**sample_service(), "password": "not-allowed"}
        response = self.client.post("/api/services", json=bad_payload)

        self.assertEqual(response.status_code, 400)
        self.assertIn("Password fields are not allowed.", response.get_json()["error"])

    def test_not_found_for_missing_service(self):
        response = self.client.get("/api/services/does-not-exist")
        self.assertEqual(response.status_code, 404)

    def test_service_delete_blocked_when_account_exists(self):
        self.client.post("/api/services", json=sample_service())
        self.client.post("/api/accounts", json=sample_account())

        delete_response = self.client.delete("/api/services/claude_code_pro")
        self.assertEqual(delete_response.status_code, 400)

    def test_home_dashboard_page_renders(self):
        self.client.post("/api/services", json=sample_service())
        self.client.post("/api/accounts", json=sample_account())

        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("SleepyDogDev AI Page", html)
        self.assertIn("builder@example.com", html)

    def test_crud_page_renders(self):
        response = self.client.get("/crud")
        self.assertEqual(response.status_code, 200)
        self.assertIn("CRUD Workspace", response.get_data(as_text=True))

    def test_budget_and_recommendation_api_flow(self):
        self.client.post("/api/services", json=sample_service())
        self.client.post("/api/accounts", json=sample_account())

        budget_response = self.client.post("/api/budgets", json=sample_budget())
        recommendation_response = self.client.post("/api/recommendations", json=sample_recommendation())
        dashboard_response = self.client.get("/api/dashboard")

        self.assertEqual(budget_response.status_code, 201)
        self.assertEqual(recommendation_response.status_code, 201)
        self.assertEqual(dashboard_response.status_code, 200)
        dashboard = dashboard_response.get_json()
        self.assertEqual(len(dashboard["budget_alerts"]), 1)

    def test_web_forms_add_and_update_service(self):
        create_response = self.client.post(
            "/services/save",
            data={
                "id": "chatgpt_plus",
                "name": "ChatGPT Plus",
                "category": "general",
                "provider": "OpenAI",
                "website_url": "https://chatgpt.com",
                "docs_url": "",
                "billing_url": "",
                "edit_id": "",
            },
        )
        self.assertEqual(create_response.status_code, 302)

        update_response = self.client.post(
            "/services/save",
            data={
                "id": "chatgpt_plus",
                "name": "ChatGPT Plus Updated",
                "category": "general",
                "provider": "OpenAI",
                "website_url": "https://chatgpt.com",
                "docs_url": "",
                "billing_url": "",
                "edit_id": "chatgpt_plus",
            },
        )
        self.assertEqual(update_response.status_code, 302)
        get_response = self.client.get("/api/services/chatgpt_plus")
        self.assertEqual(get_response.get_json()["name"], "ChatGPT Plus Updated")

    def test_web_forms_add_and_update_account(self):
        self.client.post("/api/services", json=sample_service())
        create_response = self.client.post(
            "/accounts/save",
            data={
                "id": "acc_900",
                "service_id": "claude_code_pro",
                "email": "a@example.com",
                "plan_name": "Pro",
                "monthly_cost_usd": "19.99",
                "renewal_day": "8",
                "status": "active",
                "notes": "n",
                "tags": "coding, deep_repo",
                "edit_id": "",
            },
        )
        self.assertEqual(create_response.status_code, 302)

        update_response = self.client.post(
            "/accounts/save",
            data={
                "id": "acc_900",
                "service_id": "claude_code_pro",
                "email": "updated@example.com",
                "plan_name": "Pro",
                "monthly_cost_usd": "21",
                "renewal_day": "",
                "status": "paused",
                "notes": "changed",
                "tags": "",
                "edit_id": "acc_900",
            },
        )
        self.assertEqual(update_response.status_code, 302)
        get_response = self.client.get("/api/accounts/acc_900")
        payload = get_response.get_json()
        self.assertEqual(payload["email"], "updated@example.com")
        self.assertEqual(payload["status"], "paused")

    def test_import_config_from_web(self):
        payload = {
            "services": [sample_service()],
            "accounts": [sample_account()],
            "usage_budgets": [sample_budget()],
            "recommendations": [sample_recommendation()],
        }
        response = self.client.post("/config/import", data={"config_json": json.dumps(payload)})
        self.assertEqual(response.status_code, 302)
        dashboard = self.client.get("/api/dashboard").get_json()
        self.assertEqual(dashboard["total_monthly_spend_usd"], 17.0)


if __name__ == "__main__":
    unittest.main()
