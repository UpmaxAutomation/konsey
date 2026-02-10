# Phase 1: Critical Security Fixes

## Overview
**Priority**: 🔴 IMMEDIATE
**Estimated Time**: 2 hours
**Impact**: Fixes data leakage and security vulnerabilities

---

## Task 1.1: Remove External Telemetry

<task type="auto">
  <name>Remove agent logging from App.jsx</name>
  <files>frontend/src/App.jsx</files>
  <action>
    1. Open frontend/src/App.jsx
    2. Search for "127.0.0.1:7242" - should find 2-4 occurrences
    3. Delete entire blocks marked with `#region agent log` / `#endregion`
    4. Remove lines 68-70 (first telemetry block)
    5. Remove lines 81-83 (second telemetry block)
    6. Search for any other fetch calls to localhost ports
    7. Save file
  </action>
  <verify>
    - Run: grep -r "127.0.0.1:7242" frontend/
    - Expected: 0 results
    - Run: grep -r "agent log" frontend/
    - Expected: 0 results
  </verify>
  <done>No external telemetry calls in frontend code</done>
</task>

<task type="auto">
  <name>Search entire codebase for telemetry</name>
  <files>frontend/src/**/*.jsx, frontend/src/**/*.js</files>
  <action>
    1. Run: grep -r "fetch.*localhost" frontend/src/
    2. Run: grep -r "fetch.*127\.0\.0\.1" frontend/src/
    3. Review each result - remove any non-API debug logging
    4. Keep legitimate API calls to backend
  </action>
  <verify>
    - Only legitimate backend API calls remain
    - No calls to unknown ports
  </verify>
  <done>Codebase clean of debug telemetry</done>
</task>

---

## Task 1.2: Remove Hardcoded Debug Paths

<task type="auto">
  <name>Create logging configuration</name>
  <files>backend/logging_config.py (new)</files>
  <action>
    1. Create backend/logging_config.py
    2. Configure Python logging with:
       - LOG_LEVEL from environment (default: INFO)
       - Structured JSON format for production
       - Console format for development
       - Request ID injection
    3. Export `get_logger(name)` function
  </action>
  <code>
import logging
import os
import sys
from typing import Optional

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = os.getenv("LOG_FORMAT", "console")  # "console" or "json"

def setup_logging():
    """Configure application logging."""
    root = logging.getLogger()
    root.setLevel(LOG_LEVEL)

    # Clear existing handlers
    root.handlers = []

    if LOG_FORMAT == "json":
        # JSON format for production
        import json
        class JsonFormatter(logging.Formatter):
            def format(self, record):
                return json.dumps({
                    "timestamp": self.formatTime(record),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                    "module": record.module,
                    "line": record.lineno,
                })
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
    else:
        # Console format for development
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"
        ))

    root.addHandler(handler)

def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name."""
    return logging.getLogger(name)

# Initialize on import
setup_logging()
  </code>
  <verify>
    - File exists at backend/logging_config.py
    - Import works: python -c "from backend.logging_config import get_logger"
  </verify>
  <done>Logging configuration module created</done>
</task>

<task type="auto">
  <name>Remove hardcoded paths from openrouter.py</name>
  <files>backend/openrouter.py</files>
  <action>
    1. Search for "/Users/sezars" in file
    2. Search for ".cursor/debug.log" in file
    3. Remove all debug_log file operations
    4. Replace with proper logger calls
    5. Import: from .logging_config import get_logger
    6. Create logger: logger = get_logger(__name__)
    7. Replace debug writes with logger.debug()
  </action>
  <verify>
    - Run: grep -r "/Users/" backend/openrouter.py
    - Expected: 0 results
    - Run: grep -r "debug.log" backend/openrouter.py
    - Expected: 0 results
  </verify>
  <done>openrouter.py uses proper logging</done>
</task>

<task type="auto">
  <name>Remove hardcoded paths from council.py</name>
  <files>backend/council.py</files>
  <action>
    1. Search for "/Users/sezars" in file
    2. Remove debug_log file operations
    3. Replace with logger calls
    4. Import logging_config
  </action>
  <verify>
    - Run: grep -r "/Users/" backend/council.py
    - Expected: 0 results
  </verify>
  <done>council.py uses proper logging</done>
</task>

<task type="auto">
  <name>Remove hardcoded paths from middleware.py</name>
  <files>backend/middleware.py</files>
  <action>
    1. Search for hardcoded paths
    2. Replace with proper logging
  </action>
  <verify>
    - Run: grep -r "/Users/" backend/middleware.py
    - Expected: 0 results
  </verify>
  <done>middleware.py uses proper logging</done>
</task>

<task type="auto">
  <name>Remove hardcoded paths from auth.py</name>
  <files>backend/auth.py</files>
  <action>
    1. Search for hardcoded paths
    2. Replace with proper logging
  </action>
  <verify>
    - Run: grep -r "/Users/" backend/auth.py
    - Expected: 0 results
  </verify>
  <done>auth.py uses proper logging</done>
</task>

---

## Task 1.3: Stop Logging API Keys

<task type="auto">
  <name>Remove API key logging</name>
  <files>backend/openrouter.py</files>
  <action>
    1. Find line ~201 with key_prefix logging
    2. Remove any logging of API key prefixes
    3. Create redaction utility if needed
    4. Search for other api_key logging patterns
  </action>
  <verify>
    - Run: grep -rn "api_key\|apikey" backend/*.py | grep -i "log\|print\|debug"
    - Expected: 0 results that show key values
  </verify>
  <done>No API keys logged anywhere</done>
</task>

<task type="auto">
  <name>Add redaction utility</name>
  <files>backend/utils.py or backend/logging_config.py</files>
  <action>
    1. Add function to redact sensitive values
    2. Redact: API keys, passwords, tokens
    3. Keep only type indicator: "[REDACTED:api_key]"
  </action>
  <code>
def redact_sensitive(data: dict, keys: list = None) -> dict:
    """Redact sensitive values from a dictionary."""
    if keys is None:
        keys = ['api_key', 'apikey', 'password', 'token', 'secret', 'authorization']

    result = {}
    for k, v in data.items():
        if any(sensitive in k.lower() for sensitive in keys):
            result[k] = f"[REDACTED:{k}]"
        elif isinstance(v, dict):
            result[k] = redact_sensitive(v, keys)
        else:
            result[k] = v
    return result
  </code>
  <verify>
    - Import works
    - redact_sensitive({"api_key": "sk-123"}) returns {"api_key": "[REDACTED:api_key]"}
  </verify>
  <done>Redaction utility available for logging</done>
</task>

---

## Final Verification

<task type="manual">
  <name>Full security scan</name>
  <action>
    Run these commands and verify 0 results:

    ```bash
    # Check for external telemetry
    grep -r "127.0.0.1:7242" .

    # Check for hardcoded paths
    grep -r "/Users/sezars" . --include="*.py" --include="*.js" --include="*.jsx"

    # Check for debug.log references
    grep -r "debug.log" . --include="*.py"

    # Check for API key logging
    grep -rn "api_key" backend/*.py | grep -i "print\|log"
    ```
  </action>
  <verify>
    All commands return 0 results
  </verify>
  <done>Security scan passes</done>
</task>

<task type="auto">
  <name>Commit changes</name>
  <action>
    1. Stage all changes
    2. Run tests to ensure nothing broke
    3. Commit with message: "security(01-23): remove telemetry, hardcoded paths, and key logging"
  </action>
  <verify>
    - git status shows clean
    - Tests pass
  </verify>
  <done>Phase 1 complete and committed</done>
</task>

---

## Rollback Plan

If issues arise:
1. `git stash` or `git checkout -- .` to revert changes
2. Specific file revert: `git checkout HEAD -- backend/openrouter.py`

---

## Expected Outcome

After Phase 1:
- ✅ No data leaking to external services
- ✅ No system paths exposed in code
- ✅ No API keys logged
- ✅ Proper Python logging configured
- ✅ Score improvement: 6/10 → 7/10
