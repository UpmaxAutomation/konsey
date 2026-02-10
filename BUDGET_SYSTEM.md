# Cost Budgets & Alerts System

## Overview

The LLM Council now includes a comprehensive cost budgets and alerts system to help you monitor and control spending on API calls. The system tracks costs across three time periods (daily, weekly, monthly) and provides real-time alerts when approaching or exceeding budget limits.

## Features

### 1. Multi-Period Budget Tracking
- **Daily Budget**: Reset automatically at midnight
- **Weekly Budget**: Reset automatically every Monday
- **Monthly Budget**: Reset automatically on the 1st of each month

### 2. Alert Levels
The system provides graduated alerts as you approach your budget limits:

| Alert Level | Threshold | Color | Description |
|------------|-----------|-------|-------------|
| **NONE** | < 50% | Green | Budget usage is under control |
| **INFO** | 50-75% | Blue-Green | Budget usage is moderate |
| **WARNING** | 75-90% | Orange | Approaching budget limit |
| **CRITICAL** | 90-100% | Red | Very close to budget limit |
| **EXCEEDED** | > 100% | Dark Red | Budget limit exceeded |

### 3. Customizable Alert Threshold
- Set the percentage (50-100%) at which you want to receive warnings
- Default: 75% (WARNING at 75%, CRITICAL at 90%)
- Slider control in Settings UI

### 4. Real-Time Budget Banner
- Displays at the top of the application when alerts are active
- Color-coded by alert severity
- Shows most critical alert message
- Dismissible (can be closed)
- Auto-refreshes every 30 seconds

### 5. Progress Visualization
In the Settings page, you can see:
- Current spending vs. limit for each period
- Percentage used (color-coded)
- Progress bars with gradient colors
- Remaining budget

## Usage

### Setting Up Budgets

1. **Open Settings**
   - Click the ⚙️ Settings icon in the sidebar

2. **Navigate to Cost Budgets Section**
   - Scroll to the "Cost Budgets" section

3. **Configure Budget Limits**
   - **Daily Limit**: Enter maximum spend per day (e.g., `1.00` for $1/day)
   - **Weekly Limit**: Enter maximum spend per week (e.g., `5.00` for $5/week)
   - **Monthly Limit**: Enter maximum spend per month (e.g., `20.00` for $20/month)
   - Set to `0` to disable a budget period

4. **Set Alert Threshold**
   - Use the slider to set when you want to receive warnings
   - Range: 50-100%
   - Example: 75% means you'll get WARNING at 75% usage

5. **Save Changes**
   - Click "Save Changes" at the bottom

### Monitoring Spending

#### In Settings

Each enabled budget period shows:
```
Daily Limit ($)
[Input: 1.00]

$0.45 / $1.00                    75.0% [WARNING badge]
[████████████░░░░] (progress bar)
```

#### Alert Banner

When budgets are triggered, a banner appears at the top:

```
💰 Daily budget warning: 80.0% used ($0.80 of $1.00)  [×]
```

Click `×` to dismiss (will reappear if conditions still met).

### Managing Budgets

#### Reset Spending

You can manually reset spending for any period:

1. Via API:
   ```bash
   # Reset specific period
   curl -X POST http://localhost:8001/api/budget/reset?period=daily

   # Reset all periods
   curl -X POST http://localhost:8001/api/budget/reset
   ```

2. The frontend doesn't have reset buttons yet, but you can:
   - Wait for automatic reset (midnight/Monday/1st of month)
   - Use the API endpoint above
   - Clear the data file: `rm backend/data/budgets.json`

#### Disable Budget Alerts

To disable alerts without changing limits:
- Set Alert Threshold to 100%
- This will only show EXCEEDED alerts (when over 100%)

To completely disable budget tracking:
- Set all budget limits to `0`

## API Reference

### GET /api/budget
Get current budget configuration and status.

**Response:**
```json
{
  "limits": {
    "daily": 1.0,
    "weekly": 5.0,
    "monthly": 20.0
  },
  "alert_threshold": 75.0,
  "spending": {
    "daily": {"amount": 0.45, "date": "2025-12-25"},
    "weekly": {"amount": 2.30, "week_start": "2025-12-23"},
    "monthly": {"amount": 8.50, "month_start": "2025-12-01"}
  },
  "status": {
    "daily": {
      "percentage": 45.0,
      "alert_level": "none",
      "remaining": 0.55,
      "spent": 0.45,
      "limit": 1.0,
      "enabled": true
    },
    "weekly": {...},
    "monthly": {...}
  },
  "alerts": [
    {
      "period": "weekly",
      "level": "warning",
      "percentage": 76.0,
      "spent": 3.8,
      "limit": 5.0,
      "message": "Weekly budget warning: 76.0% used ($3.8000 of $5.00)",
      "timestamp": "2025-12-25T14:30:00.123456"
    }
  ]
}
```

### POST /api/budget
Set budget limits and alert threshold.

**Request:**
```json
{
  "daily": 1.0,
  "weekly": 5.0,
  "monthly": 20.0,
  "alert_threshold": 75.0
}
```

**Response:** Same as GET /api/budget

### GET /api/budget/alerts
Get all currently active budget alerts.

**Response:**
```json
{
  "alerts": [
    {
      "period": "daily",
      "level": "exceeded",
      "percentage": 110.0,
      "spent": 1.1,
      "limit": 1.0,
      "message": "Daily budget exceeded! Spent $1.1000 of $1.00 (110.0%)",
      "timestamp": "2025-12-25T15:45:00.123456"
    }
  ],
  "exceeded": true,
  "exceeded_periods": ["daily"]
}
```

### POST /api/budget/reset?period=<period>
Manually reset budget spending for a period.

**Parameters:**
- `period` (optional): `daily`, `weekly`, or `monthly`
- Omit `period` to reset all periods

**Response:**
```json
{
  "status": "reset",
  "period": "daily"
}
```

### POST /api/budget/alerts/clear
Clear all active budget alerts (doesn't reset spending).

**Response:**
```json
{
  "status": "cleared"
}
```

## Backend Integration

The budget system is automatically integrated with cost tracking in `backend/analytics.py`:

```python
def record_query(models, chairman, tokens_used, cost, response_times, aggregate_rankings):
    """Record analytics and track budget spending."""
    # ... record analytics ...

    # Track cost against budgets
    if cost > 0:
        budgets.track_spending(cost)
```

Every time a council query is made, the cost is automatically:
1. Recorded in analytics
2. Added to all active budget periods (daily/weekly/monthly)
3. Checked against limits to generate alerts

## Data Storage

Budget data is stored in `backend/data/budgets.json`:

```json
{
  "limits": {
    "daily": 1.0,
    "weekly": 5.0,
    "monthly": 20.0
  },
  "alert_threshold": 75.0,
  "spending": {
    "daily": {"amount": 0.45, "date": "2025-12-25"},
    "weekly": {"amount": 2.30, "week_start": "2025-12-23"},
    "monthly": {"amount": 8.50, "month_start": "2025-12-01"}
  },
  "alerts": [],
  "last_reset": {
    "daily": "2025-12-25T00:00:00.000000",
    "weekly": "2025-12-23T00:00:00.000000",
    "monthly": "2025-12-01T00:00:00.000000"
  }
}
```

## Testing

Run the comprehensive test suite:

```bash
python3 test_budget_system.py
```

This tests:
- ✓ Budget configuration
- ✓ Setting limits
- ✓ Tracking spending
- ✓ Alert generation at different levels
- ✓ Budget reset functionality
- ✓ Multiple period tracking
- ✓ Disabled budgets

## UI Components

### Settings Page (Budget Section)

Location: `frontend/src/components/Settings.jsx` (lines 319-429)

Features:
- Three number inputs for daily/weekly/monthly limits
- Range slider for alert threshold (50-100%)
- Real-time progress bars showing current usage
- Color-coded percentage badges (none/info/warning/critical/exceeded)
- Spending display: "$X.XX / $Y.YY"

### Budget Alert Banner

Location: `frontend/src/App.jsx` (lines 12-66, 223-276)

Features:
- Displays at top of application
- Color-coded by alert level (gradient backgrounds)
- Icon: 💰 (info/warning), ⚠️ (critical), 🚫 (exceeded)
- Dismissible with × button
- Auto-refreshes every 30 seconds
- Slide-down animation on appearance

## Best Practices

1. **Start Conservative**: Begin with lower limits and adjust based on usage
2. **Monitor Regularly**: Check the Settings page to see spending trends
3. **Set Multiple Periods**: Use daily for immediate control, monthly for overall budget
4. **Adjust Threshold**: Lower threshold (e.g., 50%) for early warnings
5. **Test First**: Set a small budget and run test queries to verify alerts work

## Troubleshooting

### Alerts Not Showing

1. Check if budgets are enabled (limits > 0)
2. Verify spending has reached threshold percentage
3. Check console for API errors: `GET /api/budget/alerts`
4. Ensure backend is running on port 8001

### Spending Not Tracking

1. Verify queries are being sent through the council system
2. Check `backend/data/budgets.json` exists
3. Verify `backend/analytics.py` is calling `budgets.track_spending(cost)`
4. Check backend logs for errors

### Budget Not Resetting

1. Automatic resets happen when backend loads budget data
2. Check system date/time is correct
3. Verify `last_reset` timestamps in `budgets.json`
4. Manually reset via API if needed

### Progress Bars Not Updating

1. Hard refresh browser (Cmd/Ctrl + Shift + R)
2. Close and reopen Settings modal
3. Check browser console for JavaScript errors
4. Verify API is returning correct data: `GET /api/budget`

## Future Enhancements

Potential improvements (not yet implemented):

- [ ] Budget reset buttons in Settings UI
- [ ] Historical spending charts
- [ ] Budget recommendations based on usage patterns
- [ ] Email/webhook notifications for alerts
- [ ] Per-model budget tracking
- [ ] Budget templates/presets
- [ ] Export budget reports
- [ ] Forecast when budget will be exceeded

## Related Files

**Backend:**
- `backend/budgets.py` - Core budget tracking logic
- `backend/main.py` (lines 1030-1103) - API endpoints
- `backend/analytics.py` (lines 80-84) - Integration with cost tracking
- `backend/data/budgets.json` - Budget data storage

**Frontend:**
- `frontend/src/api.js` (lines 445-524) - API client methods
- `frontend/src/components/Settings.jsx` (lines 319-429) - Budget UI
- `frontend/src/components/Settings.css` (lines 824-1006) - Budget styling
- `frontend/src/App.jsx` (lines 12-66, 223-276) - Alert banner
- `frontend/src/App.css` (lines 20-102) - Banner styling

**Tests:**
- `test_budget_system.py` - Comprehensive test suite

## Support

For issues or questions:
1. Check this documentation
2. Review backend logs: `python -m backend.main`
3. Check browser console for frontend errors
4. Verify API responses with curl/Postman
5. Run test suite: `python3 test_budget_system.py`
