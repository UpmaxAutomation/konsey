# Phase 13 Plan 02: Semantic File Ranking Summary

**Added TF-IDF style file relevance scoring so most relevant files appear first in LLM context.**

## Accomplishments

- **Stopwords Filter**: Added common English stopwords set for better keyword extraction
- **Keyword Extraction**: `extract_keywords()` tokenizes and filters query text
- **Relevance Scoring**: `score_file_relevance()` scores files based on:
  - Keyword frequency in file content
  - Filename matches (10x boost)
  - Normalized by content length (log scale) to avoid bias toward long files
- **File Ranking**: `rank_files_by_relevance()` sorts files by score (highest first)
- **Context Integration**: Both `format_files_for_context()` and `format_files_for_vision()` accept optional `query` parameter
- **Backward Compatible**: Functions work unchanged when no query provided

## Files Created/Modified

- `backend/files.py`:
  - Added `STOPWORDS` constant
  - Added `extract_keywords()` function
  - Added `score_file_relevance()` function
  - Added `rank_files_by_relevance()` function
  - Updated `format_files_for_context()` to accept `query` parameter
  - Updated `format_files_for_vision()` to accept `query` parameter

- `backend/council.py`:
  - Updated `run_full_council()` to pass `user_query` to file formatting
  - Updated `run_full_council_stream()` to pass `user_query` to file formatting

- `backend/main.py`:
  - Quick mode endpoint already passes `request.content` as query

## Decisions Made

1. **TF-IDF Style Scoring**: Used simple keyword matching (no external embedding models) for speed
2. **Filename Boost**: 10x weight for query term appearing in filename
3. **Log Normalization**: `log10(len/1000 + 1)` prevents long files from dominating
4. **Image Handling**: Images get neutral score (0.0) - they're always included after text
5. **Error Handling**: Files that error during scoring get neutral score, still included

## Issues Encountered

None - implementation went smoothly.

## Next Step

Phase 13 complete - document processing significantly improved:
- PDF OCR for scanned documents
- Accurate tiktoken-based token counting
- Code-aware truncation at function boundaries
- Semantic file ranking by query relevance
