# Budget System - Quick Start Guide

## Setup (30 seconds)

1. **Open Settings**
   - Click gear icon in sidebar
   - Scroll to "Cost Budgets" section

2. **Set Your Limits**
   ```
   Daily Limit:    $5.00
   Weekly Limit:   $25.00
   Monthly Limit:  $100.00
   Alert Threshold: 75%
   ```

3. **Save**
   - Click "Save Changes"
   - Budget tracking is now active

## What Happens Next

- Every query automatically tracks cost
- Progress bars update in real-time
- Alerts appear when reaching threshold
- Color changes: Green → Yellow → Red → Dark Red

## Alert Meanings

| Color | Percentage | Icon | Meaning |
|-------|-----------|------|---------|
| Green | 0-74% | 💰 | Safe - Continue normally |
| Yellow | 75-89% | 💰 | Warning - Approaching limit |
| Red | 90-99% | ⚠️ | Critical - Very close to limit |
| Dark Red | 100%+ | 🚫 | Exceeded - Consider pausing |

## Viewing Status

**In Settings:**
- See spending for each period
- View progress bars
- Check percentage used
- See remaining budget

**In Alert Banner:**
- Appears at top when threshold crossed
- Shows most urgent alert
- Click X to dismiss temporarily
- Re-appears on new alerts

## Common Actions

### Increase Limits
1. Open Settings
2. Update budget inputs
3. Save Changes

### Reset for Testing
```bash
curl -X POST http://localhost:8001/api/budget/reset
```

### Disable Budget
Set all limits to `0` in Settings

### Change Alert Threshold
Move slider in Settings:
- Left (50%) = Alert early
- Right (100%) = Alert late
- Default: 75%

## Budget Periods

| Period | Resets | Example |
|--------|--------|---------|
| Daily | Midnight | Today's spending only |
| Weekly | Monday | This week's spending |
| Monthly | 1st of month | This month's spending |

## API Quick Reference

```javascript
// Get status
const budget = await api.getBudget();

// Update limits
await api.setBudget({
  daily: 10,
  weekly: 50,
  monthly: 200
});

// Check alerts
const alerts = await api.getBudgetAlerts();

// Reset all
await api.resetBudget();
```

## Example Budgets

**Light Use** (Testing, learning)
- Daily: $1
- Weekly: $5
- Monthly: $20

**Medium Use** (Regular development)
- Daily: $5
- Weekly: $25
- Monthly: $100

**Heavy Use** (Production, team)
- Daily: $20
- Weekly: $100
- Monthly: $400

## Tips

1. **Start Conservative**: Begin with lower limits, increase as needed
2. **Monitor Weekly**: Check Settings weekly to see trends
3. **Set Early Alerts**: Use 50-60% threshold for advance warning
4. **Test Queries**: Check cost before running expensive queries
5. **Reset After Testing**: Use reset endpoint when testing

## Troubleshooting

**Budget not updating?**
- Wait 30 seconds (polling interval)
- Reload Settings to force refresh

**Alert won't dismiss?**
- It will reappear every 30s until spending drops below threshold
- To permanently dismiss: increase limit or reduce spending

**Need to pause tracking?**
- Set all limits to 0 (disables tracking)
- Save changes

## Files

- Budget data: `data/budgets.json`
- Backend module: `backend/budgets.py`
- API endpoints: `/api/budget/*`

## Next Steps

1. Set your initial budgets
2. Run a few test queries
3. Check Settings to see tracking
4. Adjust limits as needed
5. Monitor alerts as you work
