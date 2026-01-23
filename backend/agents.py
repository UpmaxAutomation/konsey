"""
AI Agents - Autonomous Task Execution System for LLM Council.

Provides DeepAgent-like capabilities for complex multi-step tasks:
- Task planning and decomposition
- Tool usage (web search, code execution, file operations)
- Memory and context management
- Iterative refinement
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

from .openrouter import query_model
from .tools import web_search, fetch_url, execute_python, execute_javascript
from .config import AVAILABLE_MODELS


class AgentStatus(str, Enum):
    PENDING = "pending"
    PLANNING = "planning"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ToolType(str, Enum):
    WEB_SEARCH = "web_search"
    FETCH_URL = "fetch_url"
    EXECUTE_PYTHON = "execute_python"
    EXECUTE_JAVASCRIPT = "execute_javascript"
    THINK = "think"
    ANSWER = "answer"


@dataclass
class AgentStep:
    """Represents a single step in the agent's execution."""
    id: str
    tool: ToolType
    input: Dict[str, Any]
    output: Optional[Dict[str, Any]] = None
    status: str = "pending"
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None


@dataclass
class AgentTask:
    """Represents an agent task with its full execution state."""
    id: str
    user_query: str
    status: AgentStatus = AgentStatus.PENDING
    plan: List[str] = field(default_factory=list)
    steps: List[AgentStep] = field(default_factory=list)
    final_answer: Optional[str] = None
    model: str = "anthropic/claude-sonnet-4"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    error: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)


# In-memory storage for active tasks
_active_tasks: Dict[str, AgentTask] = {}


AGENT_SYSTEM_PROMPT = """You are an autonomous AI agent that can complete complex tasks by breaking them down into steps and using tools.

## Available Tools

1. **web_search(query)** - Search the web for information
   Example: {"tool": "web_search", "input": {"query": "latest Python 3.12 features"}}

2. **fetch_url(url)** - Fetch and read content from a URL
   Example: {"tool": "fetch_url", "input": {"url": "https://example.com/article"}}

3. **execute_python(code)** - Execute Python code and get results
   Example: {"tool": "execute_python", "input": {"code": "print(2 + 2)"}}

4. **execute_javascript(code)** - Execute JavaScript code
   Example: {"tool": "execute_javascript", "input": {"code": "console.log('hello')"}}

5. **think(thought)** - Record your reasoning process
   Example: {"tool": "think", "input": {"thought": "I need to first search for..."}}

6. **answer(response)** - Provide the final answer to the user
   Example: {"tool": "answer", "input": {"response": "Based on my research..."}}

## Instructions

1. Analyze the user's request carefully
2. Break it down into logical steps
3. Execute tools one at a time
4. Use the results to inform next steps
5. Provide a comprehensive final answer

## Response Format

Always respond with a valid JSON object:
```json
{
  "tool": "tool_name",
  "input": {...},
  "reasoning": "Why I'm taking this action"
}
```

When you have completed the task, use the "answer" tool with your final response.
"""


async def create_agent_task(
    user_query: str,
    model: str = "anthropic/claude-sonnet-4",
    context: Optional[Dict[str, Any]] = None
) -> AgentTask:
    """Create a new agent task."""
    task = AgentTask(
        id=str(uuid.uuid4()),
        user_query=user_query,
        model=model,
        context=context or {}
    )
    _active_tasks[task.id] = task
    return task


async def execute_tool(tool: ToolType, input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a specific tool and return the result."""
    try:
        if tool == ToolType.WEB_SEARCH:
            results = await web_search(input_data.get("query", ""), num_results=5)
            return {"success": True, "results": results}

        elif tool == ToolType.FETCH_URL:
            content = await fetch_url(input_data.get("url", ""))
            return {"success": True, "content": content[:5000]}

        elif tool == ToolType.EXECUTE_PYTHON:
            result = execute_python(input_data.get("code", ""), timeout=30)
            return result

        elif tool == ToolType.EXECUTE_JAVASCRIPT:
            result = execute_javascript(input_data.get("code", ""), timeout=30)
            return result

        elif tool == ToolType.THINK:
            return {"success": True, "thought": input_data.get("thought", "")}

        elif tool == ToolType.ANSWER:
            return {"success": True, "response": input_data.get("response", "")}

        else:
            return {"success": False, "error": f"Unknown tool: {tool}"}

    except Exception as e:
        return {"success": False, "error": str(e)}


def build_agent_context(task: AgentTask) -> str:
    """Build the conversation context for the agent."""
    context_parts = [f"User Request: {task.user_query}\n"]

    if task.context:
        context_parts.append(f"Additional Context: {json.dumps(task.context)}\n")

    if task.steps:
        context_parts.append("\n## Previous Steps:\n")
        for i, step in enumerate(task.steps, 1):
            context_parts.append(f"\n### Step {i}: {step.tool.value}")
            context_parts.append(f"Input: {json.dumps(step.input)}")
            if step.output:
                output_str = json.dumps(step.output)
                if len(output_str) > 1000:
                    output_str = output_str[:1000] + "... (truncated)"
                context_parts.append(f"Output: {output_str}")
            if step.error:
                context_parts.append(f"Error: {step.error}")

    context_parts.append("\n\nBased on the above, determine the next action or provide the final answer.")

    return "\n".join(context_parts)


def parse_agent_response(response: str) -> Optional[Dict[str, Any]]:
    """Parse the agent's JSON response."""
    try:
        # Try to find JSON in the response
        response = response.strip()

        # Handle code blocks
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            response = response[start:end].strip()
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            response = response[start:end].strip()

        # Find JSON object
        if "{" in response:
            start = response.find("{")
            # Find matching closing brace
            depth = 0
            end = start
            for i, char in enumerate(response[start:], start):
                if char == "{":
                    depth += 1
                elif char == "}":
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
            response = response[start:end]

        return json.loads(response)

    except (json.JSONDecodeError, ValueError):
        return None


async def run_agent_step(task: AgentTask, max_retries: int = 2) -> bool:
    """Execute a single step of the agent."""
    context = build_agent_context(task)

    for attempt in range(max_retries):
        try:
            # Query the model
            result = await query_model(
                task.model,
                context,
                system_prompt=AGENT_SYSTEM_PROMPT
            )

            if not result or not result.get("content"):
                continue

            # Parse the response
            parsed = parse_agent_response(result["content"])

            if not parsed or "tool" not in parsed:
                # Try to extract answer if the model didn't follow format
                if "answer" in result["content"].lower() or attempt == max_retries - 1:
                    parsed = {
                        "tool": "answer",
                        "input": {"response": result["content"]},
                        "reasoning": "Direct response"
                    }
                else:
                    continue

            # Create step
            tool_name = parsed.get("tool", "think")
            try:
                tool = ToolType(tool_name)
            except ValueError:
                tool = ToolType.THINK

            step = AgentStep(
                id=str(uuid.uuid4()),
                tool=tool,
                input=parsed.get("input", {}),
                started_at=datetime.now().isoformat()
            )

            # Execute the tool
            step.output = await execute_tool(tool, step.input)
            step.completed_at = datetime.now().isoformat()
            step.status = "completed" if step.output.get("success", True) else "failed"

            task.steps.append(step)

            # Check if this is the final answer
            if tool == ToolType.ANSWER:
                task.final_answer = step.input.get("response", "")
                task.status = AgentStatus.COMPLETED
                task.completed_at = datetime.now().isoformat()
                return True

            return True

        except Exception as e:
            if attempt == max_retries - 1:
                task.error = str(e)
                return False

    return False


async def run_agent(
    task: AgentTask,
    max_steps: int = 10,
    on_step: Optional[Callable[[AgentStep], None]] = None
) -> AgentTask:
    """Run the agent to completion."""
    task.status = AgentStatus.EXECUTING

    for step_num in range(max_steps):
        success = await run_agent_step(task)

        if on_step and task.steps:
            on_step(task.steps[-1])

        if task.status == AgentStatus.COMPLETED:
            break

        if not success:
            task.status = AgentStatus.FAILED
            break

        # Small delay between steps
        await asyncio.sleep(0.5)

    if task.status == AgentStatus.EXECUTING:
        # Max steps reached without completion
        task.status = AgentStatus.COMPLETED
        if task.steps:
            # Use last step output as answer
            last_output = task.steps[-1].output
            if last_output:
                task.final_answer = json.dumps(last_output)

    return task


def get_task(task_id: str) -> Optional[AgentTask]:
    """Get a task by ID."""
    return _active_tasks.get(task_id)


def list_tasks() -> List[AgentTask]:
    """List all tasks."""
    return list(_active_tasks.values())


def cancel_task(task_id: str) -> bool:
    """Cancel a running task."""
    task = _active_tasks.get(task_id)
    if task and task.status in [AgentStatus.PENDING, AgentStatus.PLANNING, AgentStatus.EXECUTING]:
        task.status = AgentStatus.CANCELLED
        return True
    return False


def delete_task(task_id: str) -> bool:
    """Delete a task."""
    if task_id in _active_tasks:
        del _active_tasks[task_id]
        return True
    return False


def task_to_dict(task: AgentTask) -> Dict[str, Any]:
    """Convert a task to a dictionary."""
    return {
        "id": task.id,
        "user_query": task.user_query,
        "status": task.status.value,
        "plan": task.plan,
        "steps": [
            {
                "id": s.id,
                "tool": s.tool.value,
                "input": s.input,
                "output": s.output,
                "status": s.status,
                "started_at": s.started_at,
                "completed_at": s.completed_at,
                "error": s.error
            }
            for s in task.steps
        ],
        "final_answer": task.final_answer,
        "model": task.model,
        "created_at": task.created_at,
        "completed_at": task.completed_at,
        "error": task.error
    }
