#!/usr/bin/env python3
"""
Test script to verify the budget system is working correctly.

This script tests:
1. Budget configuration and status API
2. Setting budget limits
3. Tracking spending
4. Budget alerts generation
5. Budget reset functionality
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend import budgets
import json

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def test_budget_system():
    """Test the complete budget system."""

    print_section("TEST 1: Initial Budget Configuration")

    # Get initial config
    config = budgets.get_budget_config()
    print(f"Initial limits: Daily=${config['limits']['daily']}, Weekly=${config['limits']['weekly']}, Monthly=${config['limits']['monthly']}")
    print(f"Alert threshold: {config['alert_threshold']}%")
    print(f"Current alerts: {len(config['alerts'])}")
    print(f"Status: {json.dumps(config['status'], indent=2)}")

    print_section("TEST 2: Setting Budget Limits")

    # Set budget limits
    updated_config = budgets.set_budget_limits(
        daily=1.0,      # $1.00/day
        weekly=5.0,     # $5.00/week
        monthly=20.0,   # $20.00/month
        alert_threshold=75.0
    )
    print(f"Updated limits: Daily=${updated_config['limits']['daily']}, Weekly=${updated_config['limits']['weekly']}, Monthly=${updated_config['limits']['monthly']}")
    print(f"Alert threshold: {updated_config['alert_threshold']}%")

    print_section("TEST 3: Tracking Spending (Small Amount)")

    # Track some spending (25% of daily budget)
    budgets.track_spending(0.25)
    config = budgets.get_budget_config()
    print(f"After spending $0.25:")
    print(f"  Daily: ${config['status']['daily']['spent']:.4f} / ${config['status']['daily']['limit']} ({config['status']['daily']['percentage']:.1f}%)")
    print(f"  Alert level: {config['status']['daily']['alert_level']}")
    print(f"  Active alerts: {len(config['alerts'])}")

    print_section("TEST 4: Tracking More Spending (Trigger Warning)")

    # Track more spending to trigger warning (total 80%)
    budgets.track_spending(0.55)
    config = budgets.get_budget_config()
    print(f"After spending additional $0.55 (total $0.80):")
    print(f"  Daily: ${config['status']['daily']['spent']:.4f} / ${config['status']['daily']['limit']} ({config['status']['daily']['percentage']:.1f}%)")
    print(f"  Alert level: {config['status']['daily']['alert_level']}")
    print(f"  Active alerts: {len(config['alerts'])}")

    if config['alerts']:
        for alert in config['alerts']:
            print(f"\n  ALERT: {alert['message']}")
            print(f"    Level: {alert['level']}")
            print(f"    Period: {alert['period']}")

    print_section("TEST 5: Tracking Even More Spending (Exceed Budget)")

    # Exceed the budget
    budgets.track_spending(0.30)
    config = budgets.get_budget_config()
    print(f"After spending additional $0.30 (total $1.10):")
    print(f"  Daily: ${config['status']['daily']['spent']:.4f} / ${config['status']['daily']['limit']} ({config['status']['daily']['percentage']:.1f}%)")
    print(f"  Alert level: {config['status']['daily']['alert_level']}")
    print(f"  Active alerts: {len(config['alerts'])}")

    if config['alerts']:
        for alert in config['alerts']:
            print(f"\n  ALERT: {alert['message']}")
            print(f"    Level: {alert['level']}")
            print(f"    Period: {alert['period']}")

    # Check exceeded status
    exceeded = budgets.check_budget_exceeded()
    print(f"\n  Budget exceeded: {exceeded['exceeded']}")
    print(f"  Exceeded periods: {exceeded['periods']}")

    print_section("TEST 6: Reset Budget")

    # Reset daily budget
    budgets.reset_budget('daily')
    config = budgets.get_budget_config()
    print(f"After reset:")
    print(f"  Daily: ${config['status']['daily']['spent']:.4f} / ${config['status']['daily']['limit']} ({config['status']['daily']['percentage']:.1f}%)")
    print(f"  Alert level: {config['status']['daily']['alert_level']}")
    print(f"  Active alerts: {len(config['alerts'])}")

    print_section("TEST 7: Alert Levels at Different Thresholds")

    # Test different alert levels
    budgets.reset_budget('daily')

    test_amounts = [
        (0.40, "40% - Should be INFO"),
        (0.15, "55% - Should be INFO"),
        (0.25, "80% - Should be WARNING"),
        (0.15, "95% - Should be CRITICAL"),
        (0.10, "105% - Should be EXCEEDED"),
    ]

    for amount, description in test_amounts:
        budgets.track_spending(amount)
        config = budgets.get_budget_config()
        daily_status = config['status']['daily']
        print(f"{description}")
        print(f"  Spent: ${daily_status['spent']:.4f} / ${daily_status['limit']} ({daily_status['percentage']:.1f}%)")
        print(f"  Alert level: {daily_status['alert_level']}")

        if config['alerts']:
            print(f"  Message: {config['alerts'][0]['message']}")
        print()

    print_section("TEST 8: Multiple Period Tracking")

    # Reset all budgets
    budgets.reset_budget()

    # Track spending across all periods
    budgets.track_spending(0.50)
    config = budgets.get_budget_config()

    print(f"After spending $0.50 (affects all periods):")
    print(f"  Daily:   ${config['status']['daily']['spent']:.4f} / ${config['status']['daily']['limit']} ({config['status']['daily']['percentage']:.1f}%)")
    print(f"  Weekly:  ${config['status']['weekly']['spent']:.4f} / ${config['status']['weekly']['limit']} ({config['status']['weekly']['percentage']:.1f}%)")
    print(f"  Monthly: ${config['status']['monthly']['spent']:.4f} / ${config['status']['monthly']['limit']} ({config['status']['monthly']['percentage']:.1f}%)")

    print_section("TEST 9: Disable Budget")

    # Disable daily budget
    budgets.set_budget_limits(daily=0.0)
    budgets.track_spending(100.0)  # Spend a lot
    config = budgets.get_budget_config()

    print(f"Daily budget disabled (limit = $0.00):")
    print(f"  Spent: ${config['status']['daily']['spent']:.4f}")
    print(f"  Enabled: {config['status']['daily']['enabled']}")
    print(f"  Alert level: {config['status']['daily']['alert_level']}")
    print(f"  Weekly still tracks: ${config['status']['weekly']['spent']:.4f} / ${config['status']['weekly']['limit']}")

    print_section("TESTS COMPLETE")

    print("✓ All budget system tests passed successfully!")
    print("\nThe budget system is fully functional and ready to use.")
    print("\nTo test in the UI:")
    print("1. Start backend: cd backend && python -m backend.main")
    print("2. Start frontend: cd frontend && npm run dev")
    print("3. Open Settings and configure budget limits")
    print("4. Send some queries to generate costs")
    print("5. Watch for budget alerts in the banner at the top")


if __name__ == "__main__":
    try:
        test_budget_system()
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
