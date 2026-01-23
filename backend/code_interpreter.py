"""Sandboxed Python code execution for LLM Council."""

import subprocess
import tempfile
import os
import sys
import json
import base64
from typing import Dict, Any, Optional
from pathlib import Path
import asyncio

# Execution limits
MAX_EXECUTION_TIME = 30  # seconds
MAX_OUTPUT_SIZE = 100000  # characters
MAX_MEMORY_MB = 512

# Allowed imports (whitelist for safety)
ALLOWED_IMPORTS = {
    # Data analysis
    'pandas', 'numpy', 'scipy', 'statistics',
    # Visualization
    'matplotlib', 'seaborn', 'plotly',
    # Math
    'math', 'decimal', 'fractions', 'random',
    # Data formats
    'json', 'csv', 'xml',
    # Text processing
    're', 'string', 'textwrap',
    # Date/time
    'datetime', 'time', 'calendar',
    # Collections
    'collections', 'itertools', 'functools',
    # Other safe modules
    'hashlib', 'base64', 'urllib.parse',
}

# Blocked patterns for security
BLOCKED_PATTERNS = [
    'import os',
    'import sys',
    'import subprocess',
    'import shutil',
    '__import__',
    'eval(',
    'exec(',
    'compile(',
    'open(',
    'file(',
    'input(',
    'raw_input(',
    'execfile(',
    '__builtins__',
    'globals(',
    'locals(',
    'vars(',
    'dir(',
    'getattr(',
    'setattr(',
    'delattr(',
    'hasattr(',
]


def validate_code(code: str) -> tuple[bool, Optional[str]]:
    """
    Validate code for safety before execution.

    Args:
        code: Python code to validate

    Returns:
        Tuple of (is_safe, error_message)
    """
    code_lower = code.lower()

    for pattern in BLOCKED_PATTERNS:
        if pattern.lower() in code_lower:
            return False, f"Blocked pattern detected: {pattern}"

    # Check for file operations
    if 'with open' in code_lower or 'open(' in code_lower:
        return False, "File operations are not allowed"

    # Check for network operations
    if 'socket' in code_lower or 'requests' in code_lower or 'urllib' in code_lower:
        if 'urllib.parse' not in code_lower:
            return False, "Network operations are not allowed"

    return True, None


def create_sandbox_script(code: str, output_dir: str) -> str:
    """
    Create a sandboxed Python script with output capture.

    Args:
        code: User's Python code
        output_dir: Directory for output files

    Returns:
        Full script content
    """
    script = f'''
import sys
import io
import json
import base64
import traceback

# Redirect stdout
_stdout_capture = io.StringIO()
_stderr_capture = io.StringIO()
_original_stdout = sys.stdout
_original_stderr = sys.stderr
sys.stdout = _stdout_capture
sys.stderr = _stderr_capture

_result = {{
    "stdout": "",
    "stderr": "",
    "result": None,
    "error": None,
    "figures": []
}}

try:
    # Setup matplotlib for non-interactive backend
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    # Track figures
    _figure_count = 0
    _original_show = plt.show

    def _capture_show(*args, **kwargs):
        global _figure_count
        for fig_num in plt.get_fignums():
            fig = plt.figure(fig_num)
            import io as _io
            buf = _io.BytesIO()
            fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)
            img_base64 = base64.b64encode(buf.read()).decode('utf-8')
            _result["figures"].append({{
                "type": "image/png",
                "data": img_base64
            }})
            _figure_count += 1
            plt.close(fig)

    plt.show = _capture_show

    # Execute user code
    _exec_result = None
    exec("""
{code}
""", {{"__builtins__": __builtins__}})

except Exception as e:
    _result["error"] = {{
        "type": type(e).__name__,
        "message": str(e),
        "traceback": traceback.format_exc()
    }}

finally:
    sys.stdout = _original_stdout
    sys.stderr = _original_stderr
    _result["stdout"] = _stdout_capture.getvalue()[:100000]
    _result["stderr"] = _stderr_capture.getvalue()[:10000]

    # Output result as JSON
    print(json.dumps(_result))
'''
    return script


async def execute_code(code: str, timeout: int = MAX_EXECUTION_TIME) -> Dict[str, Any]:
    """
    Execute Python code in a sandboxed environment.

    Args:
        code: Python code to execute
        timeout: Maximum execution time in seconds

    Returns:
        Dict with stdout, stderr, result, figures, and any errors
    """
    # Validate code first
    is_safe, error = validate_code(code)
    if not is_safe:
        return {
            "success": False,
            "stdout": "",
            "stderr": "",
            "error": {
                "type": "SecurityError",
                "message": error
            },
            "figures": []
        }

    # Create temporary directory for execution
    with tempfile.TemporaryDirectory() as tmpdir:
        script_path = os.path.join(tmpdir, "script.py")
        script_content = create_sandbox_script(code, tmpdir)

        with open(script_path, 'w') as f:
            f.write(script_content)

        try:
            # Execute with timeout and resource limits
            process = await asyncio.create_subprocess_exec(
                sys.executable, script_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=tmpdir
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return {
                    "success": False,
                    "stdout": "",
                    "stderr": "",
                    "error": {
                        "type": "TimeoutError",
                        "message": f"Execution exceeded {timeout} second limit"
                    },
                    "figures": []
                }

            # Parse output
            stdout_str = stdout.decode('utf-8', errors='replace')
            stderr_str = stderr.decode('utf-8', errors='replace')

            # Try to parse JSON result from stdout
            try:
                # Find the JSON output (last line should be our result)
                lines = stdout_str.strip().split('\n')
                for line in reversed(lines):
                    try:
                        result = json.loads(line)
                        if isinstance(result, dict) and 'stdout' in result:
                            result["success"] = result.get("error") is None
                            return result
                    except json.JSONDecodeError:
                        continue

                # If no JSON found, return raw output
                return {
                    "success": process.returncode == 0,
                    "stdout": stdout_str[:MAX_OUTPUT_SIZE],
                    "stderr": stderr_str[:MAX_OUTPUT_SIZE],
                    "error": None if process.returncode == 0 else {
                        "type": "ExecutionError",
                        "message": stderr_str or "Unknown error"
                    },
                    "figures": []
                }

            except Exception as e:
                return {
                    "success": False,
                    "stdout": stdout_str[:MAX_OUTPUT_SIZE],
                    "stderr": stderr_str[:MAX_OUTPUT_SIZE],
                    "error": {
                        "type": "ParseError",
                        "message": str(e)
                    },
                    "figures": []
                }

        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": "",
                "error": {
                    "type": type(e).__name__,
                    "message": str(e)
                },
                "figures": []
            }


def format_execution_result(result: Dict[str, Any]) -> str:
    """
    Format execution result for display/LLM context.

    Args:
        result: Execution result dict

    Returns:
        Formatted string
    """
    parts = []

    if result.get("stdout"):
        parts.append("**Output:**")
        parts.append("```")
        parts.append(result["stdout"][:5000])
        parts.append("```")

    if result.get("stderr"):
        parts.append("**Stderr:**")
        parts.append("```")
        parts.append(result["stderr"][:2000])
        parts.append("```")

    if result.get("error"):
        error = result["error"]
        parts.append(f"**Error ({error.get('type', 'Error')}):**")
        parts.append(f"```\n{error.get('message', 'Unknown error')}\n```")

    if result.get("figures"):
        parts.append(f"**Generated {len(result['figures'])} figure(s)**")

    return "\n".join(parts) if parts else "No output"
