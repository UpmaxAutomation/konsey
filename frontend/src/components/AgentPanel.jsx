/**
 * AgentPanel - AI Agent Interface for autonomous task execution.
 *
 * Provides a DeepAgent-like experience where AI can:
 * - Execute multi-step tasks autonomously
 * - Use tools (web search, code execution, URL fetching)
 * - Show step-by-step progress with live streaming
 */

import React, { useState, useEffect, useRef } from 'react';
import { api } from '../api';
import './AgentPanel.css';

// Tool icons mapping
const TOOL_ICONS = {
  web_search: '🔍',
  fetch_url: '🌐',
  execute_python: '🐍',
  execute_javascript: '📜',
  think: '💭',
  answer: '✅',
};

const TOOL_LABELS = {
  web_search: 'Web Search',
  fetch_url: 'Fetch URL',
  execute_python: 'Python',
  execute_javascript: 'JavaScript',
  think: 'Thinking',
  answer: 'Answer',
};

const STATUS_COLORS = {
  pending: '#6b7280',
  planning: '#3b82f6',
  executing: '#f59e0b',
  completed: '#10b981',
  failed: '#ef4444',
  cancelled: '#6b7280',
};

export default function AgentPanel({ onClose }) {
  const [query, setQuery] = useState('');
  const [selectedModel, setSelectedModel] = useState('anthropic/claude-sonnet-4');
  const [currentTask, setCurrentTask] = useState(null);
  const [taskHistory, setTaskHistory] = useState([]);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState(null);
  const [models, setModels] = useState([]);
  const stepsContainerRef = useRef(null);

  // Load available models
  useEffect(() => {
    const loadModels = async () => {
      try {
        const config = await api.getConfig();
        const modelList = Object.entries(config.available_models || {}).map(([id, info]) => ({
          id,
          name: info.name || id,
        }));
        setModels(modelList.sort((a, b) => a.name.localeCompare(b.name)));
      } catch (err) {
        console.error('Failed to load models:', err);
      }
    };
    loadModels();
  }, []);

  // Load task history
  useEffect(() => {
    const loadHistory = async () => {
      try {
        const result = await api.listAgents();
        setTaskHistory(result.tasks || []);
      } catch (err) {
        console.error('Failed to load agent history:', err);
      }
    };
    loadHistory();
  }, []);

  // Auto-scroll to latest step
  useEffect(() => {
    if (stepsContainerRef.current) {
      stepsContainerRef.current.scrollTop = stepsContainerRef.current.scrollHeight;
    }
  }, [currentTask?.steps]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!query.trim() || isRunning) return;

    setError(null);
    setIsRunning(true);

    try {
      // Create the agent task
      const task = await api.createAgent({
        query: query.trim(),
        model: selectedModel,
      });

      setCurrentTask(task);
      setQuery('');

      // Run with streaming
      await api.runAgentStream(task.id, 10, (type, event) => {
        if (type === 'step') {
          setCurrentTask(prev => ({
            ...prev,
            steps: [...(prev?.steps || []), event.step],
            status: 'executing',
          }));
        } else if (type === 'complete') {
          setCurrentTask(event.task);
          setTaskHistory(prev => [event.task, ...prev.filter(t => t.id !== event.task.id)]);
        } else if (type === 'error') {
          setError(event.message);
        }
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setIsRunning(false);
    }
  };

  const handleCancel = async () => {
    if (!currentTask || !isRunning) return;

    try {
      await api.cancelAgent(currentTask.id);
      setIsRunning(false);
      setCurrentTask(prev => ({ ...prev, status: 'cancelled' }));
    } catch (err) {
      setError(err.message);
    }
  };

  const handleLoadTask = async (taskId) => {
    try {
      const task = await api.getAgent(taskId);
      setCurrentTask(task);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDeleteTask = async (taskId, e) => {
    e.stopPropagation();
    try {
      await api.deleteAgent(taskId);
      setTaskHistory(prev => prev.filter(t => t.id !== taskId));
      if (currentTask?.id === taskId) {
        setCurrentTask(null);
      }
    } catch (err) {
      setError(err.message);
    }
  };

  const renderStep = (step, index) => {
    const icon = TOOL_ICONS[step.tool] || '🔧';
    const label = TOOL_LABELS[step.tool] || step.tool;
    const isCompleted = step.status === 'completed';
    const isFailed = step.status === 'failed';

    return (
      <div key={step.id} className={`agent-step ${step.status}`}>
        <div className="step-header">
          <span className="step-number">{index + 1}</span>
          <span className="step-icon">{icon}</span>
          <span className="step-label">{label}</span>
          <span className={`step-status ${step.status}`}>
            {step.status === 'completed' ? '✓' : step.status === 'failed' ? '✗' : '...'}
          </span>
        </div>

        {step.input && (
          <div className="step-input">
            <strong>Input:</strong>
            <pre>{JSON.stringify(step.input, null, 2)}</pre>
          </div>
        )}

        {step.output && (
          <div className="step-output">
            <strong>Output:</strong>
            <pre>{typeof step.output === 'string'
              ? step.output
              : JSON.stringify(step.output, null, 2)
            }</pre>
          </div>
        )}

        {step.error && (
          <div className="step-error">
            <strong>Error:</strong> {step.error}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="agent-panel">
      <div className="agent-header">
        <h2>
          <span className="agent-icon">🤖</span>
          AI Agent
        </h2>
        <p className="agent-description">
          Autonomous task execution with web search, code execution, and more.
        </p>
        {onClose && (
          <button className="close-btn" onClick={onClose}>×</button>
        )}
      </div>

      <div className="agent-content">
        {/* Task Input */}
        <form className="agent-form" onSubmit={handleSubmit}>
          <div className="form-row">
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              disabled={isRunning}
            >
              {models.map(model => (
                <option key={model.id} value={model.id}>
                  {model.name}
                </option>
              ))}
            </select>
          </div>

          <div className="form-row">
            <textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Describe the task for the AI agent..."
              rows={3}
              disabled={isRunning}
            />
          </div>

          <div className="form-actions">
            <button
              type="submit"
              className="run-btn"
              disabled={!query.trim() || isRunning}
            >
              {isRunning ? 'Running...' : 'Run Agent'}
            </button>

            {isRunning && (
              <button
                type="button"
                className="cancel-btn"
                onClick={handleCancel}
              >
                Cancel
              </button>
            )}
          </div>
        </form>

        {error && (
          <div className="agent-error">
            <strong>Error:</strong> {error}
            <button onClick={() => setError(null)}>×</button>
          </div>
        )}

        {/* Current Task Progress */}
        {currentTask && (
          <div className="current-task">
            <div className="task-header">
              <h3>Current Task</h3>
              <span
                className="task-status"
                style={{ backgroundColor: STATUS_COLORS[currentTask.status] }}
              >
                {currentTask.status}
              </span>
            </div>

            <div className="task-query">
              <strong>Query:</strong> {currentTask.user_query}
            </div>

            <div className="steps-container" ref={stepsContainerRef}>
              {currentTask.steps?.map((step, index) => renderStep(step, index))}

              {isRunning && (
                <div className="step-loading">
                  <div className="loading-spinner"></div>
                  <span>Executing next step...</span>
                </div>
              )}
            </div>

            {currentTask.final_answer && (
              <div className="final-answer">
                <h4>Final Answer</h4>
                <div className="answer-content">
                  {currentTask.final_answer}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Task History */}
        {taskHistory.length > 0 && (
          <div className="task-history">
            <h3>History</h3>
            <div className="history-list">
              {taskHistory.slice(0, 10).map(task => (
                <div
                  key={task.id}
                  className={`history-item ${currentTask?.id === task.id ? 'active' : ''}`}
                  onClick={() => handleLoadTask(task.id)}
                >
                  <span
                    className="history-status"
                    style={{ backgroundColor: STATUS_COLORS[task.status] }}
                  />
                  <span className="history-query">
                    {task.user_query.slice(0, 50)}
                    {task.user_query.length > 50 ? '...' : ''}
                  </span>
                  <span className="history-steps">
                    {task.steps?.length || 0} steps
                  </span>
                  <button
                    className="delete-btn"
                    onClick={(e) => handleDeleteTask(task.id, e)}
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
