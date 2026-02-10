# Budget System Implementation

Complete cost budgeting and alerts system for LLM Council with automatic tracking, real-time alerts, and visual progress indicators.

## Overview

The budget system allows users to set daily, weekly, and monthly spending limits, automatically tracks costs against these limits, generates color-coded alerts at configurable thresholds, and displays visual warnings when approaching or exceeding budgets.

## Implementation Details

### Backend Components

#### 1. `/Users/sezars/llm-council/backend/budgets.py`
Complete budget tracking module with:

**Core Functions:**
- `get_budget_config()` - Get current budget configuration and status
- `set_budget_limits()` - Set budget limits (daily/weekly/monthly) and alert threshold
- `track_spending()` - Track spending and generate alerts automatically
- `get_active_alerts()` - Get all currently active budget alerts
- `check_budget_exceeded()` - Check if any budget period has been exceeded
- `reset_budget()` - Manually reset budget spending for a period
- `clear_alerts()` - Clear all active alerts

**Budget Periods:**
- Daily (resets at midnight)
- Weekly (resets on Monday)
- Monthly (resets on 1st of month)

**Alert Levels:**
- `none` - Under 50% of budget
- `info` - 50-75% of budget (green)
- `warning` - 75-90% of budget (yellow)
- `critical` - 90-100% of budget (red)
- `exceeded` - Over 100% of budget (dark red)

**Data Storage:**
- File: `data/budgets.json`
- Automatically created on first use
- Persists limits, spending, and alerts

#### 2. `/Users/sezars/llm-council/backend/main.py`
Added 5 new API endpoints:

```python
GET /api/budget
# Returns: budget config with limits, spending, status per period, and alerts

POST /api/budget
# Body: { daily, weekly, monthly, alert_threshold }
# Returns: updated budget configuration

GET /api/budget/alerts
# Returns: { alerts: [], exceeded: bool, exceeded_periods: [] }

POST /api/budget/reset?period=<daily|weekly|monthly>
# Manually reset spending for a period (or all if period omitted)

POST /api/budget/alerts/clear
# Clear all active budget alerts
```

#### 3. `/Users/sezars/llm-council/backend/analytics.py`
Integrated automatic cost tracking:

- Every query recorded via `record_query()` now automatically calls `budgets.track_spending()`
- Spending is tracked in real-time across all budget periods
- Alerts are generated automatically when thresholds are crossed
- Graceful degradation if budgets module unavailable

### Frontend Components

#### 1. `/Users/sezars/llm-council/frontend/src/api.js`
Added 5 budget API methods:

```javascript
api.getBudget()              // Get budget config and status
api.setBudget(budgetConfig)  // Set budget limits
api.getBudgetAlerts()        // Get active alerts
api.resetBudget(period)      // Reset budget period
api.clearBudgetAlerts()      // Clear all alerts
```

#### 2. `/Users/sezars/llm-council/frontend/src/components/Settings.jsx`
New "Cost Budgets" section with:

**Input Controls:**
- Daily limit input ($) with real-time validation
- Weekly limit input ($) with real-time validation
- Monthly limit input ($) with real-time validation
- Alert threshold slider (50-100%)
- All inputs show placeholder "0 = disabled"

**Visual Feedback:**
- Real-time progress bars for each enabled budget period
- Color-coded percentage indicators (green/yellow/red/dark red)
- Spending display: "$X spent / $Y limit (Z%)"
- Progress bars with gradient fills matching alert level
- Automatic updates when budget data changes

**Budget State Management:**
- Loads budget config on settings open
- Saves budget limits alongside other settings
- Validates numeric inputs (min: 0, step: 0.01)

#### 3. `/Users/sezars/llm-council/frontend/src/App.jsx`
Budget alert banner system:

**Features:**
- Top-of-page banner with color-coded alerts
- Auto-loads budget alerts on mount
- Polls for new alerts every 30 seconds
- Dismissible with X button
- Animated slide-down entrance

**Alert Display:**
- Green (info): 💰 icon - "Budget: X% used ($Y of $Z)"
- Yellow (warning): 💰 icon - "Budget warning: X% used"
- Red (critical): ⚠️ icon - "Budget critical: X% used"
- Dark Red (exceeded): 🚫 icon - "Budget exceeded! Consider pausing queries"

**Banner Logic:**
- Shows highest severity alert across all periods
- Displays most urgent message
- Re-appears when new alerts generated
- Can be dismissed temporarily (reappears on new alerts)

#### 4. `/Users/sezars/llm-council/frontend/src/components/Settings.css`
Complete styling for budget UI:

- `.budget-inputs` - Vertical layout with spacing
- `.budget-input-group` - Input containers with labels
- `.budget-progress-bar` - 8px height progress bars
- `.budget-progress-fill` - Color-coded gradient fills
- `.budget-percentage` - Pill-style percentage badges
- `.threshold-input-container` - Range slider with value display
- Responsive hover states and focus indicators
- Custom range slider styling (webkit + moz)

#### 5. `/Users/sezars/llm-council/frontend/src/App.css`
Budget banner styling:

- Gradient backgrounds per alert level
- Slide-down animation (@keyframes)
- Flexbox layout for content + close button
- Color-coded text and backgrounds
- Responsive padding and spacing
- Fixed layout structure (flex-direction: column)

## User Experience Flow

### Setting Up Budgets

1. User opens Settings (gear icon in sidebar)
2. Scrolls to "Cost Budgets" section
3. Enters desired limits:
   - Daily: e.g., $5.00
   - Weekly: e.g., $25.00
   - Monthly: e.g., $100.00
4. Adjusts alert threshold slider (default: 75%)
5. Clicks "Save Changes"
6. Budget limits are now active

### Budget Tracking

1. User sends query to council
2. Backend runs 3-stage council process
3. Cost calculated from token usage
4. `analytics.record_query()` called with cost
5. `budgets.track_spending()` automatically invoked
6. Spending added to all active periods
7. Alerts generated if thresholds crossed

### Alert Display

1. Budget threshold crossed (e.g., 80% of daily limit used)
2. Alert generated: `{ period: "daily", level: "warning", message: "...", percentage: 80 }`
3. Frontend polls `/api/budget/alerts` every 30s
4. Banner appears at top with yellow background
5. Message: "Daily budget warning: 80% used ($4.00 of $5.00)"
6. User can dismiss or take action

### Budget Exceeded

1. Spending exceeds 100% of any limit
2. Alert level: `exceeded`
3. Banner shows dark red background with 🚫 icon
4. Message: "Daily budget exceeded! Spent $5.20 of $5.00 (104%)"
5. User can:
   - Pause queries
   - Increase budget limits in Settings
   - Reset budget for testing

### Viewing Budget Status

1. Open Settings at any time
2. Budget section shows real-time status:
   - Daily: $3.45 / $5.00 (69%) - Green progress bar
   - Weekly: $12.80 / $25.00 (51%) - Green progress bar
   - Monthly: $48.20 / $100.00 (48%) - No alert (under 50%)
3. Progress bars visually indicate proximity to limits
4. Percentages color-coded for quick assessment

## Configuration Examples

### Conservative Budget (Testing)
```json
{
  "daily": 1.00,
  "weekly": 5.00,
  "monthly": 20.00,
  "alert_threshold": 75
}
```

### Standard Budget (Regular Use)
```json
{
  "daily": 5.00,
  "weekly": 25.00,
  "monthly": 100.00,
  "alert_threshold": 75
}
```

### High-Volume Budget (Production)
```json
{
  "daily": 20.00,
  "weekly": 100.00,
  "monthly": 400.00,
  "alert_threshold": 80
}
```

### Early Warning Budget (Cost-Conscious)
```json
{
  "daily": 2.00,
  "weekly": 10.00,
  "monthly": 40.00,
  "alert_threshold": 50
}
```

## API Usage Examples

### Check Current Budget Status
```javascript
const budget = await api.getBudget();
console.log(budget.status.daily);
// { percentage: 68.4, alert_level: "info", remaining: 1.58, spent: 3.42, limit: 5.00, enabled: true }
```

### Update Budget Limits
```javascript
await api.setBudget({
  daily: 10.00,
  weekly: 50.00,
  monthly: 200.00,
  alert_threshold: 80
});
```

### Check for Active Alerts
```javascript
const alerts = await api.getBudgetAlerts();
if (alerts.exceeded) {
  console.log('Budget exceeded for:', alerts.exceeded_periods);
  // Block queries or show warning
}
```

### Reset Budget (Testing)
```javascript
// Reset all periods
await api.resetBudget();

// Reset specific period
await api.resetBudget('daily');
```

## Data Flow

```
User Query
    ↓
Council Processing (3 stages)
    ↓
Cost Calculation (tokens × pricing)
    ↓
analytics.record_query(cost)
    ↓
budgets.track_spending(cost)
    ↓
Update spending: daily += cost, weekly += cost, monthly += cost
    ↓
Check thresholds: if (percentage >= threshold) → generate alert
    ↓
Save to data/budgets.json
    ↓
Frontend polls /api/budget/alerts (every 30s)
    ↓
Banner displays if alerts present
    ↓
User sees warning and can take action
```

## Budget Reset Logic

### Automatic Resets
- **Daily**: Resets at midnight (00:00 local time)
- **Weekly**: Resets on Monday (week start)
- **Monthly**: Resets on 1st of month

### Reset Detection
Every time budget data is loaded:
```python
def _check_and_reset_periods(data):
    now = datetime.now()
    today = now.date().isoformat()

    # Daily reset
    if data["spending"]["daily"]["date"] != today:
        data["spending"]["daily"] = {"amount": 0.0, "date": today}

    # Weekly reset (Monday)
    week_start = (now - timedelta(days=now.weekday())).date().isoformat()
    if data["spending"]["weekly"]["week_start"] != week_start:
        data["spending"]["weekly"] = {"amount": 0.0, "week_start": week_start}

    # Monthly reset (1st)
    month_start = now.replace(day=1).date().isoformat()
    if data["spending"]["monthly"]["month_start"] != month_start:
        data["spending"]["monthly"] = {"amount": 0.0, "month_start": month_start}
```

### Manual Resets
Via API or Settings UI:
- Reset all periods: `POST /api/budget/reset`
- Reset specific: `POST /api/budget/reset?period=daily`

## Alert Threshold Logic

Alert level determined by percentage of budget used:

```python
def _get_alert_level(percentage: float, threshold: float) -> AlertLevel:
    if percentage >= 100:
        return AlertLevel.EXCEEDED      # >100% - Stop
    elif percentage >= 90:
        return AlertLevel.CRITICAL      # 90-100% - Urgent
    elif percentage >= threshold:
        return AlertLevel.WARNING       # threshold-90% - Caution
    elif percentage >= 50:
        return AlertLevel.INFO          # 50-threshold% - Aware
    else:
        return AlertLevel.NONE          # <50% - Safe
```

**Example with 75% threshold:**
- 0-49%: No alert (green)
- 50-74%: Info (green with label)
- 75-89%: Warning (yellow)
- 90-99%: Critical (red)
- 100%+: Exceeded (dark red)

## File Structure

```
llm-council/
├── backend/
│   ├── budgets.py              # NEW - Budget tracking module
│   ├── main.py                 # UPDATED - Added budget endpoints
│   └── analytics.py            # UPDATED - Integrated cost tracking
├── frontend/src/
│   ├── api.js                  # UPDATED - Added budget API methods
│   ├── App.jsx                 # UPDATED - Added budget banner
│   ├── App.css                 # UPDATED - Added banner styling
│   └── components/
│       ├── Settings.jsx        # UPDATED - Added budget section
│       └── Settings.css        # UPDATED - Added budget styles
└── data/
    └── budgets.json            # NEW - Budget data storage
```

## Testing the Implementation

### 1. Test Budget Initialization
```bash
python3 -c "from backend import budgets; print(budgets.get_budget_config())"
```

### 2. Test Setting Limits
```bash
python3 -c "from backend import budgets; budgets.set_budget_limits(daily=5.0, alert_threshold=75); print('Budget set')"
```

### 3. Test Spending Tracking
```bash
python3 -c "from backend import budgets; budgets.track_spending(2.50); print(budgets.get_active_alerts())"
```

### 4. Test Frontend
1. Start backend: `cd backend && python -m uvicorn main:app --reload --port 8001`
2. Start frontend: `cd frontend && npm run dev`
3. Open Settings, set budgets
4. Send queries, watch alerts appear

## Future Enhancements

### Possible Additions
1. **Budget History**: Track spending trends over time
2. **Budget Forecasting**: Predict when limits will be reached
3. **Per-Model Budgets**: Set limits for specific models
4. **Budget Notifications**: Email/webhook alerts
5. **Budget Rollover**: Unused budget carries to next period
6. **Spending Analytics**: Charts showing budget utilization
7. **Budget Templates**: Pre-configured budget sets
8. **Query Blocking**: Auto-block queries when exceeded (optional)
9. **Grace Period**: Allow X% over before blocking
10. **Multi-User Budgets**: Shared budgets across team

## Troubleshooting

### Budget Not Tracking
**Issue**: Spending not updating after queries
**Solution**: Check that `analytics.record_query()` includes cost parameter

### Alerts Not Showing
**Issue**: Banner doesn't appear
**Solution**:
1. Check `/api/budget/alerts` returns alerts
2. Verify polling interval (30s)
3. Check `showBudgetBanner` state not dismissed

### Budget Resets Unexpectedly
**Issue**: Budget resets at wrong time
**Solution**: Check server timezone matches expected timezone for resets

### Progress Bars Not Updating
**Issue**: Visual progress doesn't match spending
**Solution**: Reload Settings to fetch fresh budget data

## Security Considerations

1. **No User Authentication**: Current implementation is single-user
2. **File-Based Storage**: Suitable for local use, not production multi-user
3. **No Audit Trail**: Budget changes not logged
4. **Client-Side Polling**: 30s delay before alerts show
5. **No Rate Limiting**: User can reset budgets unlimited times

For production use, consider:
- Database storage instead of JSON files
- User authentication and authorization
- Budget modification audit logs
- Server-sent events for real-time alerts
- Rate limiting on budget resets

## Summary

The budget system provides comprehensive cost control for the LLM Council application with:

- ✅ Automatic cost tracking across daily/weekly/monthly periods
- ✅ Configurable alert thresholds (50-100%)
- ✅ Color-coded visual feedback (green/yellow/red/dark red)
- ✅ Real-time alerts with dismissible banners
- ✅ Progress bars in Settings showing budget utilization
- ✅ Automatic period resets (daily/weekly/monthly)
- ✅ Manual reset capability for testing
- ✅ Complete API for budget management
- ✅ Persistent storage in data/budgets.json
- ✅ Integration with existing analytics system

All implementation complete and tested.
