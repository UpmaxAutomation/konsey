# Analytics Dashboard

## Overview

The analytics dashboard tracks and visualizes LLM Council performance metrics including model rankings, costs, response times, and usage trends.

## Features

### 1. Overview Tab
- Total queries processed
- Total cost across all queries
- Number of unique models used
- Average tokens per query

### 2. Model Performance Tab
- **Leaderboard**: Models ranked by Stage 2 performance (wins + average ranking position)
- Wins count: Times a model was ranked #1 (avg_rank <= 1.5)
- Average ranking position: Lower is better (1.0 = always ranked first)
- Total appearances in Stage 2 evaluations
- Token usage and cost per model

### 3. Costs Tab
- Total cost visualization
- Cost breakdown by model (bar chart with percentages)
- Cost by day (table view)
- Costs are approximated by dividing equally among all models in a query

### 4. Usage Trends Tab
- Queries per day (bar chart)
- Queries by hour of day (bar chart)
- Total query count

## Data Storage

Analytics data is stored in `/backend/data/analytics.json`:

```json
{
  "queries": [
    {
      "timestamp": "2025-12-25T10:30:00",
      "models": ["openai/gpt-4o", "anthropic/claude-sonnet-4"],
      "chairman": "google/gemini-2.5-pro",
      "tokens_used": {
        "openai/gpt-4o": 1500,
        "anthropic/claude-sonnet-4": 1200
      },
      "cost": 0.0042,
      "response_times": {
        "openai/gpt-4o": 2.5,
        "anthropic/claude-sonnet-4": 3.1
      },
      "aggregate_rankings": [
        {"model": "openai/gpt-4o", "avg_rank": 1.2, "votes": 3},
        {"model": "anthropic/claude-sonnet-4", "avg_rank": 1.8, "votes": 3}
      ]
    }
  ]
}
```

## API Endpoints

- `GET /api/analytics` - Complete analytics summary
- `GET /api/analytics/models` - Model performance statistics
- `GET /api/analytics/costs` - Cost breakdown
- `GET /api/analytics/times` - Response time statistics
- `GET /api/analytics/trends` - Usage trends over time
- `POST /api/analytics/clear` - Clear all analytics data

## Implementation Details

### Backend Components

**`backend/analytics.py`**
- Core analytics tracking and aggregation logic
- Functions for recording queries and computing statistics
- File-based JSON storage

**`backend/analytics_tracker.py`**
- Helper module to extract usage data from council results
- Integrates with `council.py` to automatically track queries
- Graceful error handling (analytics failures don't break queries)

**`backend/council.py`**
- Integrated analytics tracking in `run_full_council()`
- Automatically records after each successful council query

### Frontend Components

**`frontend/src/components/Analytics.jsx`**
- Modal-based dashboard with 4 tabs
- Fetches analytics on open
- Refresh and clear data buttons
- Responsive design

**`frontend/src/components/Analytics.css`**
- Clean, professional styling
- Bar charts using CSS gradients
- Mobile-responsive layout

**`frontend/src/components/Sidebar.jsx`**
- Analytics button in header (bar chart icon)
- Opens analytics modal

## Metrics Explained

### Win Definition
A model "wins" when its average ranking position is <= 1.5, meaning it was ranked #1 by most evaluators.

### Average Rank
The mean position in Stage 2 rankings across all queries. Lower is better:
- 1.0 = Always ranked first
- 2.0 = Always ranked second
- 3.0 = Always ranked third

### Cost Calculation
Costs are approximate, calculated by dividing the total query cost equally among all participating models (council members + chairman). This is a simplified approach since actual costs depend on token usage per model.

## Usage

1. **Access Analytics**: Click the bar chart icon in the sidebar
2. **Navigate Tabs**: Switch between Overview, Models, Costs, and Trends
3. **Refresh Data**: Click "Refresh" to reload latest analytics
4. **Clear Data**: Click "Clear Analytics Data" to reset all tracking

## Privacy & Data

- Analytics data is stored locally in `backend/data/analytics.json`
- No data is sent to external servers
- Clearing analytics removes all historical data
- Analytics tracking can be disabled by removing the tracking call in `council.py`

## Future Enhancements

- Export analytics to CSV/JSON
- Date range filtering
- Model comparison charts
- Cost projections based on usage trends
- Real-time response time tracking
- Per-conversation analytics breakdown
- Custom analytics queries (e.g., "most expensive day")
