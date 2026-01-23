"""Tests for AI Agents module."""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

from backend.agents import (
    AgentStatus,
    ToolType,
    AgentStep,
    AgentTask,
    create_agent_task,
    execute_tool,
    parse_agent_response,
    build_agent_context,
    get_task,
    list_tasks,
    cancel_task,
    delete_task,
    task_to_dict,
    _active_tasks,
)


class TestAgentStatus:
    """Tests for AgentStatus enum."""

    def test_status_values(self):
        assert AgentStatus.PENDING.value == "pending"
        assert AgentStatus.PLANNING.value == "planning"
        assert AgentStatus.EXECUTING.value == "executing"
        assert AgentStatus.COMPLETED.value == "completed"
        assert AgentStatus.FAILED.value == "failed"
        assert AgentStatus.CANCELLED.value == "cancelled"


class TestToolType:
    """Tests for ToolType enum."""

    def test_tool_values(self):
        assert ToolType.WEB_SEARCH.value == "web_search"
        assert ToolType.FETCH_URL.value == "fetch_url"
        assert ToolType.EXECUTE_PYTHON.value == "execute_python"
        assert ToolType.THINK.value == "think"
        assert ToolType.ANSWER.value == "answer"


class TestAgentStep:
    """Tests for AgentStep dataclass."""

    def test_step_creation(self):
        step = AgentStep(
            id="step-1",
            tool=ToolType.THINK,
            input={"thought": "Analyzing the problem"}
        )

        assert step.id == "step-1"
        assert step.tool == ToolType.THINK
        assert step.status == "pending"
        assert step.output is None
        assert step.error is None


class TestAgentTask:
    """Tests for AgentTask dataclass."""

    def test_task_creation(self):
        task = AgentTask(
            id="task-1",
            user_query="What is Python?"
        )

        assert task.id == "task-1"
        assert task.user_query == "What is Python?"
        assert task.status == AgentStatus.PENDING
        assert task.plan == []
        assert task.steps == []
        assert task.final_answer is None
        assert task.model == "anthropic/claude-sonnet-4"


class TestCreateAgentTask:
    """Tests for create_agent_task function."""

    @pytest.mark.asyncio
    async def test_create_task(self):
        # Clear storage
        _active_tasks.clear()

        task = await create_agent_task("Test query", model="test-model")

        assert task.user_query == "Test query"
        assert task.model == "test-model"
        assert task.status == AgentStatus.PENDING
        assert task.id in _active_tasks


class TestExecuteTool:
    """Tests for execute_tool function."""

    @pytest.mark.asyncio
    async def test_think_tool(self):
        result = await execute_tool(
            ToolType.THINK,
            {"thought": "Processing..."}
        )

        assert result["success"] is True
        assert result["thought"] == "Processing..."

    @pytest.mark.asyncio
    async def test_answer_tool(self):
        result = await execute_tool(
            ToolType.ANSWER,
            {"response": "Here is the answer."}
        )

        assert result["success"] is True
        assert result["response"] == "Here is the answer."


class TestParseAgentResponse:
    """Tests for parse_agent_response function."""

    def test_parse_json_response(self):
        response = '{"tool": "think", "input": {"thought": "test"}, "reasoning": "because"}'
        result = parse_agent_response(response)

        assert result["tool"] == "think"
        assert result["input"]["thought"] == "test"

    def test_parse_code_block_response(self):
        response = '''```json
        {"tool": "answer", "input": {"response": "done"}}
        ```'''
        result = parse_agent_response(response)

        assert result["tool"] == "answer"
        assert result["input"]["response"] == "done"

    def test_parse_invalid_response(self):
        result = parse_agent_response("Invalid response")
        assert result is None


class TestBuildAgentContext:
    """Tests for build_agent_context function."""

    def test_build_context_basic(self):
        task = AgentTask(
            id="task-1",
            user_query="Test query"
        )

        context = build_agent_context(task)

        assert "Test query" in context
        assert "User Request:" in context

    def test_build_context_with_steps(self):
        task = AgentTask(
            id="task-1",
            user_query="Test query",
            steps=[
                AgentStep(
                    id="step-1",
                    tool=ToolType.THINK,
                    input={"thought": "First thought"},
                    output={"success": True}
                )
            ]
        )

        context = build_agent_context(task)

        assert "Previous Steps:" in context
        assert "think" in context


class TestTaskManagement:
    """Tests for task management functions."""

    def test_get_task(self):
        _active_tasks.clear()
        task = AgentTask(id="test-id", user_query="test")
        _active_tasks["test-id"] = task

        result = get_task("test-id")
        assert result == task

        result = get_task("nonexistent")
        assert result is None

    def test_list_tasks(self):
        _active_tasks.clear()
        _active_tasks["task-1"] = AgentTask(id="task-1", user_query="q1")
        _active_tasks["task-2"] = AgentTask(id="task-2", user_query="q2")

        tasks = list_tasks()
        assert len(tasks) == 2

    def test_cancel_task(self):
        _active_tasks.clear()
        task = AgentTask(id="task-1", user_query="test", status=AgentStatus.EXECUTING)
        _active_tasks["task-1"] = task

        result = cancel_task("task-1")
        assert result is True
        assert task.status == AgentStatus.CANCELLED

    def test_delete_task(self):
        _active_tasks.clear()
        _active_tasks["task-1"] = AgentTask(id="task-1", user_query="test")

        result = delete_task("task-1")
        assert result is True
        assert "task-1" not in _active_tasks


class TestTaskToDict:
    """Tests for task_to_dict function."""

    def test_task_to_dict(self):
        task = AgentTask(
            id="task-1",
            user_query="What is AI?",
            steps=[
                AgentStep(
                    id="step-1",
                    tool=ToolType.THINK,
                    input={"thought": "test"}
                )
            ]
        )

        result = task_to_dict(task)

        assert result["id"] == "task-1"
        assert result["user_query"] == "What is AI?"
        assert len(result["steps"]) == 1
        assert result["steps"][0]["tool"] == "think"
