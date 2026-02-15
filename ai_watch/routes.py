from flask import Flask, jsonify, redirect, render_template, request, url_for

from ai_watch.validation import ALLOWED_CATEGORIES, ALLOWED_STATUSES, ValidationError


def _split_tags(raw_tags: str) -> list[str]:
    return [tag.strip() for tag in raw_tags.split(",") if tag.strip()]


def _parse_optional_int(raw_value: str) -> int | None:
    value = raw_value.strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise ValidationError("Expected an integer value.") from exc


def _parse_float(raw_value: str) -> float:
    try:
        return float(raw_value)
    except ValueError as exc:
        raise ValidationError("Expected a numeric value.") from exc


def register_routes(app: Flask) -> None:
    @app.errorhandler(ValidationError)
    def _handle_validation(error: ValidationError):
        return jsonify({"error": str(error)}), 400

    @app.route("/api/health", methods=["GET"])
    def health() -> tuple[dict, int]:
        return {"status": "ok"}, 200

    @app.route("/api/config", methods=["GET"])
    def get_config():
        return jsonify(app.config["DB"].get_config())

    @app.route("/api/dashboard", methods=["GET"])
    def dashboard():
        return jsonify(app.config["DB"].dashboard_summary())

    @app.route("/api/services", methods=["GET"])
    def list_services():
        category = request.args.get("category")
        return jsonify(app.config["DB"].list_services(category=category))

    @app.route("/api/services/<service_id>", methods=["GET"])
    def get_service(service_id: str):
        service = app.config["DB"].get_service(service_id)
        if not service:
            return jsonify({"error": "Service not found."}), 404
        return jsonify(service)

    @app.route("/api/services", methods=["POST"])
    def create_service():
        payload = request.get_json(force=True)
        created = app.config["DB"].create_service(payload)
        return jsonify(created), 201

    @app.route("/api/services/<service_id>", methods=["PUT"])
    def update_service(service_id: str):
        payload = request.get_json(force=True)
        updated = app.config["DB"].update_service(service_id, payload)
        return jsonify(updated)

    @app.route("/api/services/<service_id>", methods=["DELETE"])
    def delete_service(service_id: str):
        app.config["DB"].delete_service(service_id)
        return "", 204

    @app.route("/api/accounts", methods=["GET"])
    def list_accounts():
        category = request.args.get("category")
        status = request.args.get("status")
        return jsonify(app.config["DB"].list_accounts(category=category, status=status))

    @app.route("/api/accounts/<account_id>", methods=["GET"])
    def get_account(account_id: str):
        account = app.config["DB"].get_account(account_id)
        if not account:
            return jsonify({"error": "Account not found."}), 404
        return jsonify(account)

    @app.route("/api/accounts", methods=["POST"])
    def create_account():
        payload = request.get_json(force=True)
        created = app.config["DB"].create_account(payload)
        return jsonify(created), 201

    @app.route("/api/accounts/<account_id>", methods=["PUT"])
    def update_account(account_id: str):
        payload = request.get_json(force=True)
        updated = app.config["DB"].update_account(account_id, payload)
        return jsonify(updated)

    @app.route("/api/accounts/<account_id>", methods=["DELETE"])
    def delete_account(account_id: str):
        app.config["DB"].delete_account(account_id)
        return "", 204

    @app.route("/api/budgets", methods=["GET"])
    def list_budgets():
        return jsonify(app.config["DB"].list_budgets())

    @app.route("/api/budgets/<budget_id>", methods=["GET"])
    def get_budget(budget_id: str):
        budget = app.config["DB"].get_budget(budget_id)
        if not budget:
            return jsonify({"error": "Budget not found."}), 404
        return jsonify(budget)

    @app.route("/api/budgets", methods=["POST"])
    def create_budget():
        payload = request.get_json(force=True)
        created = app.config["DB"].create_budget(payload)
        return jsonify(created), 201

    @app.route("/api/budgets/<budget_id>", methods=["PUT"])
    def update_budget(budget_id: str):
        payload = request.get_json(force=True)
        updated = app.config["DB"].update_budget(budget_id, payload)
        return jsonify(updated)

    @app.route("/api/budgets/<budget_id>", methods=["DELETE"])
    def delete_budget(budget_id: str):
        app.config["DB"].delete_budget(budget_id)
        return "", 204

    @app.route("/api/recommendations", methods=["GET"])
    def list_recommendations():
        return jsonify(app.config["DB"].list_recommendations())

    @app.route("/api/recommendations/<recommendation_id>", methods=["GET"])
    def get_recommendation(recommendation_id: str):
        recommendation = app.config["DB"].get_recommendation(recommendation_id)
        if not recommendation:
            return jsonify({"error": "Recommendation not found."}), 404
        return jsonify(recommendation)

    @app.route("/api/recommendations", methods=["POST"])
    def create_recommendation():
        payload = request.get_json(force=True)
        created = app.config["DB"].create_recommendation(payload)
        return jsonify(created), 201

    @app.route("/api/recommendations/<recommendation_id>", methods=["PUT"])
    def update_recommendation(recommendation_id: str):
        payload = request.get_json(force=True)
        updated = app.config["DB"].update_recommendation(recommendation_id, payload)
        return jsonify(updated)

    @app.route("/api/recommendations/<recommendation_id>", methods=["DELETE"])
    def delete_recommendation(recommendation_id: str):
        app.config["DB"].delete_recommendation(recommendation_id)
        return "", 204

    @app.route("/services/save", methods=["POST"])
    def web_save_service():
        db = app.config["DB"]
        payload = {
            "id": request.form["id"].strip(),
            "name": request.form["name"].strip(),
            "category": request.form["category"].strip(),
            "provider": request.form["provider"].strip(),
            "website_url": request.form["website_url"].strip(),
            "docs_url": request.form.get("docs_url", "").strip() or None,
            "billing_url": request.form.get("billing_url", "").strip() or None,
        }
        edit_id = request.form.get("edit_id", "").strip()
        if edit_id:
            db.update_service(edit_id, payload)
        else:
            db.create_service(payload)
        return redirect(url_for("home"))

    @app.route("/accounts/save", methods=["POST"])
    def web_save_account():
        db = app.config["DB"]
        payload = {
            "id": request.form["id"].strip(),
            "service_id": request.form["service_id"].strip(),
            "email": request.form["email"].strip(),
            "plan_name": request.form["plan_name"].strip(),
            "monthly_cost_usd": _parse_float(request.form["monthly_cost_usd"]),
            "renewal_day": _parse_optional_int(request.form.get("renewal_day", "")),
            "status": request.form["status"].strip(),
            "notes": request.form.get("notes", "").strip(),
            "tags": _split_tags(request.form.get("tags", "")),
        }
        edit_id = request.form.get("edit_id", "").strip()
        if edit_id:
            db.update_account(edit_id, payload)
        else:
            db.create_account(payload)
        return redirect(url_for("home"))

    @app.route("/budgets/save", methods=["POST"])
    def web_save_budget():
        db = app.config["DB"]
        payload = {
            "id": request.form["id"].strip(),
            "account_id": request.form["account_id"].strip(),
            "monthly_budget_usd": _parse_float(request.form["monthly_budget_usd"]),
            "alert_threshold_percent": _parse_float(request.form["alert_threshold_percent"]),
            "current_month_spend_usd": _parse_float(request.form["current_month_spend_usd"]),
        }
        edit_id = request.form.get("edit_id", "").strip()
        if edit_id:
            db.update_budget(edit_id, payload)
        else:
            db.create_budget(payload)
        return redirect(url_for("home"))

    @app.route("/recommendations/save", methods=["POST"])
    def web_save_recommendation():
        db = app.config["DB"]
        account_id = request.form.get("account_id", "").strip() or None
        service_id = request.form.get("service_id", "").strip() or None
        payload = {
            "id": request.form["id"].strip(),
            "account_id": account_id,
            "service_id": service_id,
            "title": request.form["title"].strip(),
            "body": request.form["body"].strip(),
            "priority": int(request.form["priority"].strip()),
        }
        edit_id = request.form.get("edit_id", "").strip()
        if edit_id:
            db.update_recommendation(edit_id, payload)
        else:
            db.create_recommendation(payload)
        return redirect(url_for("home"))

    @app.route("/", methods=["GET"])
    def home():
        db = app.config["DB"]
        config = db.get_config()
        summary = db.dashboard_summary()

        edit_service_id = request.args.get("edit_service_id")
        edit_account_id = request.args.get("edit_account_id")
        edit_budget_id = request.args.get("edit_budget_id")
        edit_recommendation_id = request.args.get("edit_recommendation_id")

        service_by_id = {svc["id"]: svc for svc in config["services"]}
        account_by_id = {acc["id"]: acc for acc in config["accounts"]}

        service_form = db.get_service(edit_service_id) if edit_service_id else None
        account_form = db.get_account(edit_account_id) if edit_account_id else None
        budget_form = db.get_budget(edit_budget_id) if edit_budget_id else None
        recommendation_form = (
            db.get_recommendation(edit_recommendation_id) if edit_recommendation_id else None
        )

        accounts = []
        for account in config["accounts"]:
            service = service_by_id.get(account["service_id"], {})
            accounts.append({**account, "service_name": service.get("name", account["service_id"])})

        budgets = []
        for budget in config["usage_budgets"]:
            account = account_by_id.get(budget["account_id"], {})
            budgets.append({**budget, "account_email": account.get("email", budget["account_id"])})

        return render_template(
            "dashboard.html",
            summary=summary,
            services=config["services"],
            accounts=accounts,
            budgets=budgets,
            recommendations=db.list_recommendations(),
            service_form=service_form,
            account_form=account_form,
            budget_form=budget_form,
            recommendation_form=recommendation_form,
            categories=sorted(ALLOWED_CATEGORIES),
            statuses=sorted(ALLOWED_STATUSES),
        )
