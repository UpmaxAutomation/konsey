# Budget System UI Guide

Visual guide to using the Cost Budgets & Alerts system in LLM Council.

## 1. Settings Page - Budget Configuration

### Location
Click the ⚙️ **Settings** icon in the sidebar, then scroll to the **"Cost Budgets"** section.

### Budget Section Layout

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Cost Budgets                                              ┃
┃ Set spending limits and receive alerts when approaching  ┃
┃ budgets.                                                  ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃                                                           ┃
┃ Daily Limit ($)                                           ┃
┃ ┌────────────────────────────────────┐                   ┃
┃ │ 1.00                                │                   ┃
┃ └────────────────────────────────────┘                   ┃
┃                                                           ┃
┃ $0.75 / $1.00                        75.0% [WARNING]     ┃
┃ ████████████████████░░░░░░░                              ┃
┃                                                           ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃                                                           ┃
┃ Weekly Limit ($)                                          ┃
┃ ┌────────────────────────────────────┐                   ┃
┃ │ 5.00                                │                   ┃
┃ └────────────────────────────────────┘                   ┃
┃                                                           ┃
┃ $2.30 / $5.00                        46.0% [INFO]        ┃
┃ ████████████░░░░░░░░░░░░░░░                              ┃
┃                                                           ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃                                                           ┃
┃ Monthly Limit ($)                                         ┃
┃ ┌────────────────────────────────────┐                   ┃
┃ │ 20.00                               │                   ┃
┃ └────────────────────────────────────┘                   ┃
┃                                                           ┃
┃ $8.50 / $20.00                       42.5%               ┃
┃ ███████████░░░░░░░░░░░░░░░░                              ┃
┃                                                           ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃                                                           ┃
┃ Alert Threshold (%)                                       ┃
┃ ━━━━━━━━━━━━━━━●━━━━━━━━━━━━━━━━━━  75%                  ┃
┃ Alert when budget reaches this percentage                ┃
┃                                                           ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

### Alert Level Color Coding

**Progress Bars:**
- 🟢 **Green** (0-50%): Good - budget under control
- 🔵 **Blue-Green** (50-75%): Info - moderate usage
- 🟠 **Orange** (75-90%): Warning - approaching limit
- 🔴 **Red** (90-100%): Critical - very close to limit
- 🔴 **Dark Red** (>100%): Exceeded - over budget

**Percentage Badges:**
- No badge (0-50%)
- `INFO` badge with green background (50-75%)
- `WARNING` badge with orange background (75-90%)
- `CRITICAL` badge with red background (90-100%)
- `EXCEEDED` badge with dark red background (>100%)

## 2. Budget Alert Banner

### Banner Appearance

When you approach or exceed budget limits, a banner appears at the very top of the application:

#### INFO Alert (50-75%)
```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  💰  Daily budget: 55.0% used ($0.55 of $1.00)                  ×  ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
*Light green gradient background*

#### WARNING Alert (75-90%)
```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  💰  Weekly budget warning: 80.0% used ($4.00 of $5.00)         ×  ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
*Yellow-orange gradient background*

#### CRITICAL Alert (90-100%)
```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  ⚠️  Monthly budget critical! Spent $18.50 of $20.00 (92.5%)     ×  ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
*Red gradient background*

#### EXCEEDED Alert (>100%)
```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  🚫  Daily budget exceeded! Spent $1.20 of $1.00 (120.0%)        ×  ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
*Dark red gradient background, white text, bold*

### Banner Features
- **Auto-refresh**: Updates every 30 seconds
- **Dismissible**: Click the `×` button to close
- **Reappears**: Will show again if alert conditions still met
- **Priority**: Shows the most severe alert if multiple exist
- **Animation**: Slides down smoothly when appearing

## 3. Complete Workflow Example

### Step-by-Step Usage

#### 1️⃣ **Initial Setup**
```
Settings → Cost Budgets
Set:
  Daily: $1.00
  Weekly: $5.00
  Monthly: $20.00
  Alert Threshold: 75%
Click "Save Changes"
```

#### 2️⃣ **Normal Usage (0-50%)**
```
You spend: $0.40 on queries

Settings shows:
  Daily: $0.40 / $1.00 (40.0%)
  [████████░░░░░░░░░░░░]

Banner: Not shown
```

#### 3️⃣ **Info Alert (50-75%)**
```
You spend: $0.20 more (total $0.60)

Settings shows:
  Daily: $0.60 / $1.00 (60.0%) [INFO]
  [████████████░░░░░░░░]

Banner appears (green):
  💰 Daily budget: 60.0% used ($0.60 of $1.00) ×
```

#### 4️⃣ **Warning Alert (75-90%)**
```
You spend: $0.20 more (total $0.80)

Settings shows:
  Daily: $0.80 / $1.00 (80.0%) [WARNING]
  [████████████████░░░░] (orange bar)

Banner appears (yellow-orange):
  💰 Daily budget warning: 80.0% used ($0.80 of $1.00) ×
```

#### 5️⃣ **Critical Alert (90-100%)**
```
You spend: $0.15 more (total $0.95)

Settings shows:
  Daily: $0.95 / $1.00 (95.0%) [CRITICAL]
  [███████████████████░] (red bar)

Banner appears (red):
  ⚠️ Daily budget critical! Spent $0.95 of $1.00 (95.0%) ×
```

#### 6️⃣ **Exceeded (>100%)**
```
You spend: $0.10 more (total $1.05)

Settings shows:
  Daily: $1.05 / $1.00 (105.0%) [EXCEEDED]
  [████████████████████] (dark red bar, full)

Banner appears (dark red, white text):
  🚫 Daily budget exceeded! Spent $1.05 of $1.00 (105.0%) ×

Actions:
  - Stop sending queries (recommended)
  - Increase daily limit
  - Wait for automatic reset at midnight
```

## 4. Mobile/Responsive View

### Mobile Budget Section (< 600px width)

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Daily Limit ($)           ┃
┃ ┌──────────────────────┐  ┃
┃ │ 1.00                  │  ┃
┃ └──────────────────────┘  ┃
┃ $0.75 / $1.00  75% [WARN] ┃
┃ █████████████████░░░░░░   ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃ Weekly Limit ($)          ┃
┃ ┌──────────────────────┐  ┃
┃ │ 5.00                  │  ┃
┃ └──────────────────────┘  ┃
┃ $2.30 / $5.00  46% [INFO] ┃
┃ ████████████░░░░░░░░░░░   ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃ Monthly Limit ($)         ┃
┃ ┌──────────────────────┐  ┃
┃ │ 20.00                 │  ┃
┃ └──────────────────────┘  ┃
┃ $8.50 / $20.00  42.5%     ┃
┃ ███████████░░░░░░░░░░░░   ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃ Alert Threshold (%)       ┃
┃ ━━━━━━━●━━━━━━━━━   75%  ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

### Mobile Banner

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ 💰 Daily: 80% used     × ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```
*Shorter message on mobile*

## 5. Visual States Summary

### Progress Bar Colors

| Usage | Color | Gradient |
|-------|-------|----------|
| 0-50% | Green | `#10b981 → #059669` |
| 50-75% | Blue-Green | `#10b981 → #059669` |
| 75-90% | Orange | `#f59e0b → #d97706` |
| 90-100% | Red | `#ef4444 → #dc2626` |
| >100% | Dark Red | `#dc2626 → #991b1b` |

### Banner Background Colors

| Level | Background | Text Color |
|-------|------------|------------|
| INFO | Light Green Gradient | Dark Green |
| WARNING | Yellow-Orange Gradient | Dark Brown |
| CRITICAL | Light Red Gradient | Dark Red |
| EXCEEDED | Dark Red Gradient | White |

## 6. Quick Reference

### Disable a Budget Period
Set limit to `0` in Settings

### Change When Alerts Appear
Adjust "Alert Threshold" slider
- Lower = Earlier warnings (e.g., 50%)
- Higher = Later warnings (e.g., 90%)

### Dismiss Banner Temporarily
Click the `×` button
- Banner will reappear on next auto-refresh (30s) if alert still active

### Check Current Spending
Settings → Cost Budgets
- See all three periods at once
- Real-time updates

### When Budget Resets
- **Daily**: Midnight (00:00) local time
- **Weekly**: Monday at midnight
- **Monthly**: 1st of month at midnight

## 7. Tips for Best Experience

1. **Set Conservative Limits**: Start low, adjust up as needed
2. **Use All Three Periods**:
   - Daily for immediate control
   - Weekly for projects
   - Monthly for overall budget
3. **Lower Threshold for Peace of Mind**: Set to 50% if you want early warnings
4. **Monitor in Settings**: Check before large query batches
5. **Don't Dismiss Repeatedly**: If banner keeps appearing, you're over budget!

## 8. Troubleshooting Visual Issues

### Progress Bar Not Showing
- Budget limit must be > 0
- Refresh Settings page
- Check browser console for errors

### Wrong Colors Displayed
- Hard refresh: Cmd/Ctrl + Shift + R
- Clear browser cache
- Check CSS variables are loaded

### Banner Not Appearing
- Alert threshold must be reached
- Check Settings page shows alerts
- Banner may be dismissed (will reappear in 30s)
- Verify budget limits are enabled (> 0)

### Percentages Don't Update
- Close and reopen Settings
- Hard refresh browser
- Check network tab for API errors
