# Rating System - Quick Start Guide

## What is it?

A user feedback system that lets you rate model responses with 1-5 stars and see which models perform best based on real user ratings.

## How to Use

### Rating a Response

1. Ask a question to the LLM Council
2. View the Stage 1 responses
3. Scroll down to see 5 stars under each response
4. Click the stars to rate (1-5)
5. Optionally click "Add Feedback" to write a comment
6. That's it! Your rating is saved automatically

### Viewing Rating Analytics

1. Click "Analytics" in the sidebar
2. Click the "User Ratings" tab
3. See:
   - **Leaderboard**: Top models by average rating
   - **Win Rate**: Percentage of 5-star ratings
   - **Trend**: Whether model is improving/declining
   - **Best For**: Categories where model excels
   - **Distribution**: How many 1-5 star ratings each model has

## API Quick Reference

### Submit Rating
```bash
POST /api/ratings
{
  "conversation_id": "uuid",
  "message_index": 0,
  "model_id": "openai/gpt-4",
  "rating": 5,
  "feedback_text": "Great response!",
  "query_category": "code"
}
```

### Get Model Statistics
```bash
GET /api/ratings/models
```

### Get Recommendations
```bash
GET /api/ratings/recommendations?query=Write+code&num_recommendations=3
```

### Get Existing Rating
```bash
GET /api/ratings/{conversation_id}/{message_index}/{model_id}
```

### Get Overall Analytics
```bash
GET /api/ratings/analytics
```

### Clear All Ratings
```bash
POST /api/ratings/clear
```

## Key Features

- **Persistent Ratings**: Your ratings are saved and load automatically
- **Smart Recommendations**: System suggests best models for your query type
- **Trend Tracking**: See which models are improving over time
- **Category Detection**: Automatically categorizes queries (code/creative/research/reasoning)
- **Visual Analytics**: Beautiful charts and leaderboards

## Categories

The system automatically detects query types:

- **code**: Programming, debugging, algorithms
- **creative**: Writing, stories, brainstorming
- **research**: Analysis, explanations, learning
- **reasoning**: Math, logic, problem-solving
- **general**: Everything else

## Rating Guidelines

- **5 stars**: Excellent, exceeded expectations
- **4 stars**: Good, met expectations
- **3 stars**: Okay, acceptable but not great
- **2 stars**: Poor, did not meet expectations
- **1 star**: Very poor, completely wrong or unhelpful

## Data Storage

- Ratings stored in: `/backend/data/ratings.json`
- Format: JSON array of rating objects
- Safe to delete file to reset all ratings

## Tips

1. **Rate consistently** - The more ratings, the better the recommendations
2. **Add feedback** - Text feedback helps improve the system
3. **Check trends** - Look for "improving" models in analytics
4. **Compare models** - Use ratings alongside Stage 2 peer rankings
5. **Category leaders** - Check which models excel in specific areas

## Troubleshooting

**Ratings not saving?**
- Check console for errors
- Ensure backend is running on port 8001
- Verify conversation_id and message_index are valid

**Analytics empty?**
- Submit some ratings first
- Click Refresh in Analytics modal
- Check that ratings.json file exists

**Stars not showing?**
- Ensure you're viewing an assistant message (not user message)
- Check that Stage1 component received conversationId prop
- Verify CSS loaded correctly

## For Developers

**Import the module:**
```python
from backend import ratings
```

**Core functions:**
- `submit_rating()` - Save a rating
- `get_model_rating_stats()` - Get all statistics
- `get_recommendations_for_query()` - Get smart suggestions
- `get_rating_analytics()` - Get overall analytics

**Frontend components:**
- `Stage1.jsx` - Rating UI
- `Analytics.jsx` - Ratings tab

See `RATING_SYSTEM_IMPLEMENTATION.md` for full documentation.
