import { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { api } from '../api';
import './BatchProcessor.css';

export default function BatchProcessor({ isOpen, onClose }) {
  const [questions, setQuestions] = useState('');
  const [batchJobs, setBatchJobs] = useState([]);
  const [selectedJob, setSelectedJob] = useState(null);
  const [loading, setLoading] = useState(false);
  const [view, setView] = useState('create'); // 'create' or 'jobs'
  const [expandedResults, setExpandedResults] = useState({});
  const fileInputRef = useRef(null);

  // Fetch batch jobs when view changes to 'jobs'
  useEffect(() => {
    if (view === 'jobs') {
      fetchBatchJobs();
    }
  }, [view]);

  // Poll for job updates when a job is selected
  useEffect(() => {
    if (selectedJob && selectedJob.status === 'running') {
      const interval = setInterval(() => {
        fetchJobDetails(selectedJob.job_id);
      }, 2000); // Poll every 2 seconds

      return () => clearInterval(interval);
    }
  }, [selectedJob]);

  const fetchBatchJobs = async () => {
    try {
      const data = await api.listBatchJobs();
      setBatchJobs(data.jobs || []);
    } catch (error) {
      console.error('Failed to fetch batch jobs:', error);
    }
  };

  const fetchJobDetails = async (jobId) => {
    try {
      const data = await api.getBatchJob(jobId);

      // Update in batchJobs list
      setBatchJobs(prev => prev.map(job =>
        job.job_id === jobId ? data : job
      ));

      // Update selected job if it's the one being viewed
      if (selectedJob && selectedJob.job_id === jobId) {
        setSelectedJob(data);
      }
    } catch (error) {
      console.error('Failed to fetch job details:', error);
    }
  };

  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const text = event.target.result;

      // Parse CSV or text file
      let questionsList = [];
      if (file.name.endsWith('.csv')) {
        // Simple CSV parsing (assumes questions in first column)
        const lines = text.split('\n');
        questionsList = lines
          .map(line => line.split(',')[0].trim())
          .filter(q => q && q.length > 0);
      } else {
        // Text file - one question per line
        questionsList = text.split('\n')
          .map(q => q.trim())
          .filter(q => q && q.length > 0);
      }

      setQuestions(questionsList.join('\n'));
    };

    reader.readAsText(file);
  };

  const handleCreateBatch = async () => {
    const questionsList = questions.split('\n')
      .map(q => q.trim())
      .filter(q => q && q.length > 0);

    if (questionsList.length === 0) {
      alert('Please enter at least one question');
      return;
    }

    if (questionsList.length > 100) {
      alert('Maximum 100 questions per batch');
      return;
    }

    setLoading(true);

    try {
      const data = await api.createBatchJob(questionsList);
      alert(`Batch job created with ${questionsList.length} questions!`);
      setQuestions('');
      setView('jobs');
      setSelectedJob(data);
      fetchBatchJobs();
    } catch (error) {
      console.error('Failed to create batch:', error);
      alert(error.message || 'Failed to create batch job');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteJob = async (jobId) => {
    if (!confirm('Are you sure you want to delete this batch job?')) {
      return;
    }

    try {
      await api.deleteBatchJob(jobId);
      setBatchJobs(prev => prev.filter(job => job.job_id !== jobId));
      if (selectedJob && selectedJob.job_id === jobId) {
        setSelectedJob(null);
      }
    } catch (error) {
      console.error('Failed to delete batch:', error);
      alert(error.message || 'Failed to delete batch job');
    }
  };

  const toggleResultExpansion = (index) => {
    setExpandedResults(prev => ({
      ...prev,
      [index]: !prev[index]
    }));
  };

  const exportToCSV = (job) => {
    if (!job.results || job.results.length === 0) {
      alert('No results to export yet');
      return;
    }

    // Create CSV content
    const headers = ['Question', 'Status', 'Final Answer', 'Error', 'Timestamp'];
    const rows = job.results.map(result => {
      const answer = result.stage3?.final_answer || '';
      const cleanAnswer = answer.replace(/"/g, '""').replace(/\n/g, ' '); // Escape quotes and newlines
      return [
        `"${result.question.replace(/"/g, '""')}"`,
        result.success ? 'Success' : 'Failed',
        `"${cleanAnswer}"`,
        result.error ? `"${result.error.replace(/"/g, '""')}"` : '',
        result.processed_at || ''
      ].join(',');
    });

    const csv = [headers.join(','), ...rows].join('\n');

    // Download
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `batch-results-${job.job_id}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  const exportToJSON = (job) => {
    const blob = new Blob([JSON.stringify(job, null, 2)], { type: 'application/json' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `batch-results-${job.job_id}.json`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  if (!isOpen) return null;

  return (
    <div className="batch-processor-overlay">
      <div className="batch-processor-modal">
        <div className="batch-processor-header">
          <h2>Batch Processor</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>

        <div className="batch-processor-tabs">
          <button
            className={view === 'create' ? 'active' : ''}
            onClick={() => setView('create')}
          >
            Create Batch
          </button>
          <button
            className={view === 'jobs' ? 'active' : ''}
            onClick={() => setView('jobs')}
          >
            Batch Jobs ({batchJobs.length})
          </button>
        </div>

        <div className="batch-processor-content">
          {view === 'create' ? (
            <div className="batch-create">
              <div className="batch-input-section">
                <h3>Enter Questions</h3>
                <p className="help-text">Enter one question per line, or upload a CSV/text file</p>

                <textarea
                  className="batch-questions-input"
                  placeholder="Enter your questions here, one per line...&#10;&#10;Example:&#10;What is machine learning?&#10;Explain quantum computing&#10;How does blockchain work?"
                  value={questions}
                  onChange={(e) => setQuestions(e.target.value)}
                  rows={12}
                />

                <div className="batch-upload-section">
                  <label className="upload-btn">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                      <polyline points="17 8 12 3 7 8"></polyline>
                      <line x1="12" y1="3" x2="12" y2="15"></line>
                    </svg>
                    Upload CSV/TXT
                    <input
                      type="file"
                      accept=".csv,.txt"
                      onChange={handleFileUpload}
                      style={{ display: 'none' }}
                    />
                  </label>
                </div>

                <div className="batch-stats">
                  <span>Questions: {questions.split('\n').filter(q => q.trim()).length}</span>
                  <span className="max-limit">(Max: 100)</span>
                </div>
              </div>

              <button
                className="create-batch-btn"
                onClick={handleCreateBatch}
                disabled={loading || !questions.trim()}
              >
                {loading ? 'Creating...' : 'Create Batch Job'}
              </button>
            </div>
          ) : (
            <div className="batch-jobs-list">
              {batchJobs.length === 0 ? (
                <div className="no-jobs">
                  <p>No batch jobs yet</p>
                  <button onClick={() => setView('create')}>Create Your First Batch</button>
                </div>
              ) : (
                <>
                  <div className="jobs-grid">
                    {batchJobs.map((job) => (
                      <div
                        key={job.job_id}
                        className={`job-card ${selectedJob?.job_id === job.job_id ? 'selected' : ''}`}
                        onClick={() => setSelectedJob(job)}
                      >
                        <div className="job-header">
                          <span className={`job-status status-${job.status}`}>
                            {job.status}
                          </span>
                          <button
                            className="delete-job-btn"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDeleteJob(job.job_id);
                            }}
                          >
                            ×
                          </button>
                        </div>

                        <div className="job-progress">
                          <div className="progress-bar">
                            <div
                              className="progress-fill"
                              style={{ width: `${job.progress_percentage}%` }}
                            />
                          </div>
                          <span className="progress-text">
                            {job.completed} / {job.total} questions
                          </span>
                        </div>

                        <div className="job-meta">
                          <small>Created: {new Date(job.created_at).toLocaleString()}</small>
                        </div>
                      </div>
                    ))}
                  </div>

                  {selectedJob && (
                    <div className="job-details">
                      <div className="job-details-header">
                        <h3>Job Details</h3>
                      </div>

                      <div className="job-info">
                        <div className="info-row">
                          <strong>Status:</strong>
                          <span className={`status-badge status-${selectedJob.status}`}>
                            {selectedJob.status}
                          </span>
                        </div>
                        <div className="info-row">
                          <strong>Progress:</strong>
                          <span>{selectedJob.completed} / {selectedJob.total} ({selectedJob.progress_percentage.toFixed(1)}%)</span>
                        </div>
                        <div className="info-row">
                          <strong>Created:</strong>
                          <span>{new Date(selectedJob.created_at).toLocaleString()}</span>
                        </div>
                        {selectedJob.completed_at && (
                          <div className="info-row">
                            <strong>Completed:</strong>
                            <span>{new Date(selectedJob.completed_at).toLocaleString()}</span>
                          </div>
                        )}
                      </div>

                      {selectedJob.results && selectedJob.results.length > 0 && (
                        <div className="results-section">
                          <div className="results-header">
                            <h4>Results ({selectedJob.results.length})</h4>
                            <div className="export-buttons">
                              <button className="export-btn" onClick={() => exportToCSV(selectedJob)}>
                                Export CSV
                              </button>
                              <button className="export-btn secondary" onClick={() => exportToJSON(selectedJob)}>
                                Export JSON
                              </button>
                            </div>
                          </div>

                          <div className="results-list">
                            {selectedJob.results.map((result, idx) => (
                              <div key={idx} className={`result-item ${result.success ? 'success' : 'failed'}`}>
                                <div
                                  className="result-header"
                                  onClick={() => toggleResultExpansion(idx)}
                                >
                                  <span className="result-index">#{idx + 1}</span>
                                  <span className="result-status-icon">
                                    {result.success ? '✓' : '✗'}
                                  </span>
                                  <div className="result-question">{result.question}</div>
                                  <span className="expand-icon">
                                    {expandedResults[idx] ? '▼' : '▶'}
                                  </span>
                                </div>

                                {expandedResults[idx] && (
                                  <div className="result-details">
                                    {result.success ? (
                                      <>
                                        <div className="result-section">
                                          <h5>Final Answer</h5>
                                          <div className="markdown-content">
                                            <ReactMarkdown>{result.stage3?.final_answer || 'No answer'}</ReactMarkdown>
                                          </div>
                                        </div>

                                        {result.stage1 && result.stage1.length > 0 && (
                                          <div className="result-section">
                                            <h5>Stage 1 Responses ({result.stage1.length})</h5>
                                            <div className="stage1-responses">
                                              {result.stage1.map((response, i) => (
                                                <div key={i} className="stage1-response">
                                                  <strong>{response.model}:</strong>
                                                  <div className="markdown-content">
                                                    <ReactMarkdown>{response.content}</ReactMarkdown>
                                                  </div>
                                                </div>
                                              ))}
                                            </div>
                                          </div>
                                        )}

                                        {result.stage2 && result.stage2.length > 0 && (
                                          <div className="result-section">
                                            <h5>Stage 2 Rankings ({result.stage2.length})</h5>
                                            <div className="stage2-rankings">
                                              {result.stage2.map((ranking, i) => (
                                                <div key={i} className="stage2-ranking">
                                                  <strong>{ranking.model}:</strong>
                                                  <div className="ranking-list">
                                                    {ranking.parsed_ranking?.map((label, j) => (
                                                      <div key={j} className="ranking-item">
                                                        {j + 1}. {label}
                                                      </div>
                                                    ))}
                                                  </div>
                                                </div>
                                              ))}
                                            </div>
                                          </div>
                                        )}
                                      </>
                                    ) : (
                                      <div className="result-error">
                                        Error: {result.error}
                                      </div>
                                    )}
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
