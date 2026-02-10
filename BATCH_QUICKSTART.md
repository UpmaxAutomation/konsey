# Batch Processing Quick Start Guide

## Overview
The Batch Processor allows you to run multiple questions through the LLM Council deliberation process in sequence, with progress tracking and CSV export capabilities.

## How to Use

### 1. Access Batch Processor
- Click the **Batch Processing** button (clipboard icon) in the sidebar header
- Located between the Projects and Analytics buttons

### 2. Create a Batch Job

**Option A: Manual Entry**
1. Click the "Create Batch" tab
2. Type or paste questions into the textarea (one per line)
3. Example:
   ```
   What is machine learning?
   Explain quantum computing in simple terms
   How does blockchain technology work?
   What are the benefits of renewable energy?
   ```
4. Click "Create Batch Job"

**Option B: File Upload**
1. Click "Upload CSV/TXT" button
2. Select a CSV or text file containing questions
3. For CSV: questions should be in the first column
4. For TXT: one question per line
5. Questions automatically populate the textarea
6. Click "Create Batch Job"

### 3. Monitor Progress
1. System automatically switches to "Batch Jobs" view
2. See all batch jobs in a grid layout
3. Each card shows:
   - Status (Pending → Running → Completed)
   - Progress bar with percentage
   - Completed/Total count
   - Creation timestamp
4. Running jobs update every 2 seconds automatically

### 4. View Results
1. Click any job card to view detailed results
2. Results table shows:
   - Question number
   - Question text
   - Success/failure status
   - Answer preview (first 200 characters)
3. Click answer to see full council deliberation details

### 5. Export Results
1. For completed jobs, click "Export to CSV"
2. Downloads a CSV file with:
   - All questions
   - Success/failure status
   - Complete final answers
   - Processing timestamps
3. File named: `batch-results-{job-id}.csv`

### 6. Manage Jobs
- **Delete Job:** Click the × button on any job card
- **Cancel Running Job:** Delete button also cancels in-progress jobs
- Jobs persist across browser sessions

## Status Indicators

| Status | Color | Meaning |
|--------|-------|---------|
| Pending | Yellow | Job created, not started yet |
| Running | Blue | Currently processing questions |
| Completed | Green | All questions processed successfully |
| Failed | Red | Job encountered an error |
| Cancelled | Gray | Job was cancelled by user |

## Tips & Best Practices

### Question Formatting
- Keep questions clear and concise
- One complete question per line
- Avoid very long questions (council works best with focused queries)
- Questions can be up to several paragraphs if needed

### Batch Size
- **Small batches (5-10 questions):** Quick testing, immediate results
- **Medium batches (20-50 questions):** Research projects, surveys
- **Large batches (up to 100 questions):** Comprehensive analysis

### Processing Time
- Each question takes approximately 30-90 seconds depending on:
  - Number of council members
  - Model response times
  - Question complexity
- Example: 10 questions ≈ 5-15 minutes total

### File Upload Format

**CSV Example:**
```csv
Question
What is artificial intelligence?
Explain machine learning
Define neural networks
```

**TXT Example:**
```
What is artificial intelligence?
Explain machine learning
Define neural networks
```

### Error Handling
- If a single question fails, the batch continues with remaining questions
- Failed questions show error messages in the results table
- You can still export partial results
- Common errors: Model timeout, network issues, malformed questions

## Example Use Cases

### 1. Research Survey
```
Create a batch with 20 questions about a research topic
Let it run while you work on something else
Export results to CSV for analysis
Import CSV into spreadsheet for further processing
```

### 2. Knowledge Base Creation
```
Upload a TXT file with 50 FAQs
Batch process all questions through council
Export comprehensive answers
Use as knowledge base documentation
```

### 3. Comparative Analysis
```
Create batch with same question phrased differently
Compare how council responds to variations
Identify best phrasing for specific topics
```

### 4. Automated Testing
```
Create batch of test questions
Run regularly to verify council consistency
Export and compare results over time
Track model performance changes
```

## Troubleshooting

### Job Stuck in "Pending"
- Refresh the browser
- Job should start automatically
- If persists, delete and recreate

### Job Shows "Running" but No Progress
- Wait 2-3 minutes (first question may take longer)
- Check browser console for errors
- Refresh to see latest status

### Export Button Not Appearing
- Export only available for completed jobs
- Wait for all questions to finish processing
- Check that status shows "Completed"

### Questions Not Processing
- Verify questions are non-empty
- Check for special characters that might cause issues
- Try simpler questions first to test

## Advanced Features

### Real-time Updates
- Progress automatically updates every 2 seconds
- No need to refresh manually
- Works across multiple browser tabs

### Persistent Storage
- Jobs saved in `data/batch_jobs/` directory
- Survive server restarts
- Can be backed up or transferred

### Full Council Deliberation
- Each result includes complete 3-stage process:
  - Stage 1: Individual model responses
  - Stage 2: Peer rankings and evaluations
  - Stage 3: Chairman's final synthesis
- Access via API for programmatic use

## API Integration

For developers who want to integrate batch processing:

```bash
# Create batch job
curl -X POST http://localhost:8001/api/batch \
  -H "Content-Type: application/json" \
  -d '{"questions": ["Q1", "Q2", "Q3"]}'

# List all jobs
curl http://localhost:8001/api/batch

# Get specific job
curl http://localhost:8001/api/batch/{job_id}

# Delete job
curl -X DELETE http://localhost:8001/api/batch/{job_id}
```

See `BATCH_PROCESSING_IMPLEMENTATION.md` for complete API documentation.

## Keyboard Shortcuts

- `Esc`: Close batch processor modal
- `Tab`: Switch between Create Batch and Batch Jobs tabs
- `Enter` in textarea: Add new line (Shift+Enter not needed)

## Performance Notes

- **Sequential Processing:** Questions processed one at a time for consistency
- **Background Processing:** Runs asynchronously, won't block other operations
- **Memory Usage:** Each result stored in memory until export
- **Maximum Limit:** 100 questions per batch (configurable in code)

## Getting Help

If you encounter issues:
1. Check the browser console for error messages
2. Verify backend server is running on port 8001
3. Check `data/batch_jobs/` directory for job files
4. Review error messages in results table
5. Try with a smaller batch to isolate issues

## What's Next?

After mastering batch processing:
- Explore Projects feature for organizing batches
- Use Analytics to track batch processing stats
- Create custom council configurations for different batch types
- Automate batch creation via API for recurring tasks

Enjoy efficient bulk processing with the LLM Council! 🚀
