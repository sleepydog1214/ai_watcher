ALLOWED_CATEGORIES = {"coding", "art", "music", "general"}
ALLOWED_STATUSES = {"active", "paused", "cancelled"}


class ValidationError(ValueError):
    pass


def _reject_password_fields(payload: dict) -> None:
    for key in payload:
        if "password" in key.lower():
            raise ValidationError("Password fields are not allowed.")


def _require(payload: dict, field: str) -> None:
    if field not in payload:
        raise ValidationError(f"Missing required field '{field}'.")


def validate_service_payload(payload: dict) -> None:
    _reject_password_fields(payload)
    required = ["id", "name", "category", "provider", "website_url"]
    for field in required:
        _require(payload, field)

    if payload["category"] not in ALLOWED_CATEGORIES:
        raise ValidationError(
            f"Invalid category '{payload['category']}'. Allowed: {sorted(ALLOWED_CATEGORIES)}."
        )

    for url_field in ("website_url", "docs_url", "billing_url"):
        value = payload.get(url_field)
        if value is not None and not isinstance(value, str):
            raise ValidationError(f"Field '{url_field}' must be a string or null.")


def validate_account_payload(payload: dict, services: list[dict]) -> None:
    _reject_password_fields(payload)
    required = ["id", "service_id", "email", "plan_name", "monthly_cost_usd", "status"]
    for field in required:
        _require(payload, field)

    if "@" not in payload["email"]:
        raise ValidationError("Field 'email' must look like an email address.")

    if payload["status"] not in ALLOWED_STATUSES:
        raise ValidationError(
            f"Invalid status '{payload['status']}'. Allowed: {sorted(ALLOWED_STATUSES)}."
        )

    if not any(svc["id"] == payload["service_id"] for svc in services):
        raise ValidationError(f"Unknown service_id '{payload['service_id']}'.")

    monthly_cost = payload["monthly_cost_usd"]
    if not isinstance(monthly_cost, (int, float)) or monthly_cost < 0:
        raise ValidationError("Field 'monthly_cost_usd' must be a non-negative number.")

    renewal_day = payload.get("renewal_day")
    if renewal_day is not None and (not isinstance(renewal_day, int) or renewal_day < 1 or renewal_day > 31):
        raise ValidationError("Field 'renewal_day' must be an integer between 1 and 31.")

    tags = payload.get("tags")
    if tags is not None:
        if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
            raise ValidationError("Field 'tags' must be a list of strings.")


def validate_budget_payload(payload: dict, accounts: list[dict]) -> None:
    _reject_password_fields(payload)
    required = ["id", "account_id", "monthly_budget_usd", "alert_threshold_percent", "current_month_spend_usd"]
    for field in required:
        _require(payload, field)

    if not any(acc["id"] == payload["account_id"] for acc in accounts):
        raise ValidationError(f"Unknown account_id '{payload['account_id']}'.")

    for number_field in ("monthly_budget_usd", "alert_threshold_percent", "current_month_spend_usd"):
        value = payload[number_field]
        if not isinstance(value, (int, float)) or value < 0:
            raise ValidationError(f"Field '{number_field}' must be a non-negative number.")

    if payload["alert_threshold_percent"] > 100:
        raise ValidationError("Field 'alert_threshold_percent' cannot be greater than 100.")


def validate_recommendation_payload(payload: dict, accounts: list[dict], services: list[dict]) -> None:
    _reject_password_fields(payload)
    required = ["id", "title", "body", "priority"]
    for field in required:
        _require(payload, field)

    account_id = payload.get("account_id")
    service_id = payload.get("service_id")
    if not account_id and not service_id:
        raise ValidationError("Recommendation requires either 'account_id' or 'service_id'.")

    if account_id and not any(acc["id"] == account_id for acc in accounts):
        raise ValidationError(f"Unknown account_id '{account_id}'.")
    if service_id and not any(svc["id"] == service_id for svc in services):
        raise ValidationError(f"Unknown service_id '{service_id}'.")

    if not isinstance(payload["priority"], int) or payload["priority"] < 1 or payload["priority"] > 5:
        raise ValidationError("Field 'priority' must be an integer between 1 and 5.")
