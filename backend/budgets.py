"""Budget tracking and alerts for LLM Council."""

from typing import Dict, Optional, List
import json
import os
from datetime import datetime, timedelta
from enum import Enum


class BudgetPeriod(str, Enum):
    """Budget period types."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class AlertLevel(str, Enum):
    """Alert severity levels."""
    NONE = "none"
    INFO = "info"      # 50-75%
    WARNING = "warning"  # 75-90%
    CRITICAL = "critical"  # 90-100%
    EXCEEDED = "exceeded"  # >100%


BUDGETS_FILE = "data/budgets.json"


def _ensure_budgets_file():
    """Ensure budgets file exists."""
    os.makedirs(os.path.dirname(BUDGETS_FILE), exist_ok=True)
    if not os.path.exists(BUDGETS_FILE):
        default_data = {
            "limits": {
                "daily": 0.0,    # 0 = disabled
                "weekly": 0.0,
                "monthly": 0.0
            },
            "alert_threshold": 75.0,  # Alert at 75% by default
            "spending": {
                "daily": {"amount": 0.0, "date": None},
                "weekly": {"amount": 0.0, "week_start": None},
                "monthly": {"amount": 0.0, "month_start": None}
            },
            "alerts": [],
            "last_reset": {
                "daily": None,
                "weekly": None,
                "monthly": None
            }
        }
        with open(BUDGETS_FILE, 'w') as f:
            json.dump(default_data, f, indent=2)


def _load_budgets() -> Dict:
    """Load budgets data from file."""
    _ensure_budgets_file()
    try:
        with open(BUDGETS_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        _ensure_budgets_file()
        with open(BUDGETS_FILE, 'r') as f:
            return json.load(f)


def _save_budgets(data: Dict):
    """Save budgets data to file."""
    _ensure_budgets_file()
    with open(BUDGETS_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def _check_and_reset_periods(data: Dict) -> Dict:
    """Check if any budget periods need to be reset."""
    now = datetime.now()
    today = now.date().isoformat()

    # Reset daily budget at midnight
    if data["spending"]["daily"]["date"] != today:
        data["spending"]["daily"] = {"amount": 0.0, "date": today}
        data["last_reset"]["daily"] = now.isoformat()

    # Reset weekly budget on Monday
    week_start = (now - timedelta(days=now.weekday())).date().isoformat()
    if data["spending"]["weekly"]["week_start"] != week_start:
        data["spending"]["weekly"] = {"amount": 0.0, "week_start": week_start}
        data["last_reset"]["weekly"] = now.isoformat()

    # Reset monthly budget on 1st of month
    month_start = now.replace(day=1).date().isoformat()
    if data["spending"]["monthly"]["month_start"] != month_start:
        data["spending"]["monthly"] = {"amount": 0.0, "month_start": month_start}
        data["last_reset"]["monthly"] = now.isoformat()

    return data


def get_budget_config() -> Dict:
    """
    Get current budget configuration and status.

    Returns:
        {
            "limits": {"daily": float, "weekly": float, "monthly": float},
            "alert_threshold": float,  # percentage (0-100)
            "spending": {
                "daily": {"amount": float, "date": str},
                "weekly": {"amount": float, "week_start": str},
                "monthly": {"amount": float, "month_start": str}
            },
            "status": {
                "daily": {"percentage": float, "alert_level": str, "remaining": float},
                "weekly": {...},
                "monthly": {...}
            },
            "alerts": [{"period": str, "level": str, "message": str, "timestamp": str}]
        }
    """
    data = _load_budgets()
    data = _check_and_reset_periods(data)
    _save_budgets(data)

    # Calculate status for each period
    status = {}
    for period in ["daily", "weekly", "monthly"]:
        limit = data["limits"][period]
        spent = data["spending"][period]["amount"]

        if limit > 0:
            percentage = (spent / limit) * 100
            remaining = max(0, limit - spent)
            alert_level = _get_alert_level(percentage, data["alert_threshold"])
        else:
            percentage = 0.0
            remaining = float('inf')
            alert_level = AlertLevel.NONE

        status[period] = {
            "percentage": round(percentage, 2),
            "alert_level": alert_level.value,
            "remaining": round(remaining, 4),
            "spent": round(spent, 4),
            "limit": limit,
            "enabled": limit > 0
        }

    return {
        "limits": data["limits"],
        "alert_threshold": data["alert_threshold"],
        "spending": data["spending"],
        "status": status,
        "alerts": data.get("alerts", [])
    }


def set_budget_limits(
    daily: Optional[float] = None,
    weekly: Optional[float] = None,
    monthly: Optional[float] = None,
    alert_threshold: Optional[float] = None
) -> Dict:
    """
    Set budget limits and alert threshold.

    Args:
        daily: Daily budget limit in USD (0 = disabled)
        weekly: Weekly budget limit in USD (0 = disabled)
        monthly: Monthly budget limit in USD (0 = disabled)
        alert_threshold: Alert threshold percentage (0-100)

    Returns:
        Updated budget configuration
    """
    data = _load_budgets()

    if daily is not None:
        data["limits"]["daily"] = max(0, daily)
    if weekly is not None:
        data["limits"]["weekly"] = max(0, weekly)
    if monthly is not None:
        data["limits"]["monthly"] = max(0, monthly)
    if alert_threshold is not None:
        data["alert_threshold"] = max(0, min(100, alert_threshold))

    _save_budgets(data)
    return get_budget_config()


def track_spending(cost: float):
    """
    Track spending against budgets and generate alerts.

    Args:
        cost: Cost in USD to add to current spending
    """
    data = _load_budgets()
    data = _check_and_reset_periods(data)

    # Add cost to all periods
    data["spending"]["daily"]["amount"] += cost
    data["spending"]["weekly"]["amount"] += cost
    data["spending"]["monthly"]["amount"] += cost

    # Check for new alerts
    new_alerts = []
    threshold = data["alert_threshold"]

    for period in ["daily", "weekly", "monthly"]:
        limit = data["limits"][period]
        if limit <= 0:
            continue  # Budget disabled for this period

        spent = data["spending"][period]["amount"]
        percentage = (spent / limit) * 100
        alert_level = _get_alert_level(percentage, threshold)

        # Generate alert if crossed threshold or exceeded
        if alert_level != AlertLevel.NONE:
            alert = {
                "period": period,
                "level": alert_level.value,
                "percentage": round(percentage, 2),
                "spent": round(spent, 4),
                "limit": limit,
                "message": _get_alert_message(period, percentage, spent, limit),
                "timestamp": datetime.now().isoformat()
            }
            new_alerts.append(alert)

    # Update alerts (keep only most recent for each period)
    data["alerts"] = new_alerts

    _save_budgets(data)


def _get_alert_level(percentage: float, threshold: float) -> AlertLevel:
    """Determine alert level based on percentage spent."""
    if percentage >= 100:
        return AlertLevel.EXCEEDED
    elif percentage >= 90:
        return AlertLevel.CRITICAL
    elif percentage >= threshold:
        return AlertLevel.WARNING
    elif percentage >= 50:
        return AlertLevel.INFO
    else:
        return AlertLevel.NONE


def _get_alert_message(period: str, percentage: float, spent: float, limit: float) -> str:
    """Generate alert message."""
    if percentage >= 100:
        return f"{period.capitalize()} budget exceeded! Spent ${spent:.4f} of ${limit:.2f} ({percentage:.1f}%)"
    elif percentage >= 90:
        return f"{period.capitalize()} budget critical! Spent ${spent:.4f} of ${limit:.2f} ({percentage:.1f}%)"
    elif percentage >= 75:
        return f"{period.capitalize()} budget warning: {percentage:.1f}% used (${spent:.4f} of ${limit:.2f})"
    else:
        return f"{period.capitalize()} budget: {percentage:.1f}% used (${spent:.4f} of ${limit:.2f})"


def get_active_alerts() -> List[Dict]:
    """
    Get all currently active alerts.

    Returns:
        List of alert dicts with period, level, message, timestamp
    """
    data = _load_budgets()
    data = _check_and_reset_periods(data)
    _save_budgets(data)

    return data.get("alerts", [])


def check_budget_exceeded(period: Optional[str] = None) -> Dict:
    """
    Check if any budget has been exceeded.

    Args:
        period: Specific period to check (daily/weekly/monthly), or None for all

    Returns:
        {
            "exceeded": bool,
            "periods": [list of exceeded period names],
            "details": {period: {spent, limit, percentage}}
        }
    """
    data = _load_budgets()
    data = _check_and_reset_periods(data)

    exceeded_periods = []
    details = {}

    periods_to_check = [period] if period else ["daily", "weekly", "monthly"]

    for p in periods_to_check:
        limit = data["limits"][p]
        if limit <= 0:
            continue  # Disabled

        spent = data["spending"][p]["amount"]
        percentage = (spent / limit) * 100

        if percentage >= 100:
            exceeded_periods.append(p)
            details[p] = {
                "spent": round(spent, 4),
                "limit": limit,
                "percentage": round(percentage, 2)
            }

    return {
        "exceeded": len(exceeded_periods) > 0,
        "periods": exceeded_periods,
        "details": details
    }


def reset_budget(period: Optional[str] = None):
    """
    Manually reset budget spending for a period.

    Args:
        period: Period to reset (daily/weekly/monthly), or None for all
    """
    data = _load_budgets()
    now = datetime.now()

    if period:
        periods = [period]
    else:
        periods = ["daily", "weekly", "monthly"]

    for p in periods:
        if p == "daily":
            data["spending"]["daily"] = {"amount": 0.0, "date": now.date().isoformat()}
        elif p == "weekly":
            week_start = (now - timedelta(days=now.weekday())).date().isoformat()
            data["spending"]["weekly"] = {"amount": 0.0, "week_start": week_start}
        elif p == "monthly":
            month_start = now.replace(day=1).date().isoformat()
            data["spending"]["monthly"] = {"amount": 0.0, "month_start": month_start}

        data["last_reset"][p] = now.isoformat()

    # Clear alerts
    data["alerts"] = []

    _save_budgets(data)


def clear_alerts():
    """Clear all active alerts."""
    data = _load_budgets()
    data["alerts"] = []
    _save_budgets(data)
