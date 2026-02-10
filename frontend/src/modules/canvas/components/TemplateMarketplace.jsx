import { useState } from 'react';
import { useMarketplace, useApplyBoardTemplate, useRateTemplate, useDeleteBoardTemplate } from '../../../api/queries/boardTemplateQueries';
import '../styles/TemplateMarketplace.css';

const CATEGORIES = ['general', 'project-management', 'research', 'creative', 'engineering', 'education'];
const TABS = [
  { key: 'board', label: 'Board Templates' },
  { key: 'workflow', label: 'Workflow Templates' },
  { key: 'prompt', label: 'Prompt Templates' },
];

function StarRating({ rating, onRate, interactive = false }) {
  const [hover, setHover] = useState(0);
  return (
    <div className="star-rating">
      {[1, 2, 3, 4, 5].map(star => (
        <span
          key={star}
          className={`star ${star <= (hover || rating) ? 'filled' : ''} ${interactive ? 'interactive' : ''}`}
          onClick={() => interactive && onRate?.(star)}
          onMouseEnter={() => interactive && setHover(star)}
          onMouseLeave={() => interactive && setHover(0)}
        >
          ★
        </span>
      ))}
    </div>
  );
}

function TemplateCard({ template, type, onUse, onRate, onDelete }) {
  const [showRating, setShowRating] = useState(false);

  return (
    <div className="template-card">
      <div className="template-card-header">
        <span className="template-icon">{template.icon === 'layout' ? '\u{1F4CB}' : template.icon === 'zap' ? '\u26A1' : '\u{1F4C4}'}</span>
        <span className="template-category">{template.category}</span>
      </div>
      <h3 className="template-name">{template.name}</h3>
      <p className="template-desc">{template.description || 'No description'}</p>
      <div className="template-stats">
        <StarRating rating={Math.round(template.avg_rating || 0)} />
        <span className="template-use-count">{template.use_count || 0} uses</span>
        {template.rating_count > 0 && (
          <span className="template-rating-count">({template.rating_count})</span>
        )}
      </div>
      <div className="template-actions">
        {onUse && (
          <button className="template-use-btn" onClick={() => onUse(template)}>
            Use Template
          </button>
        )}
        <button className="template-rate-btn" onClick={() => setShowRating(!showRating)}>
          Rate
        </button>
        {onDelete && (
          <button className="template-delete-btn" onClick={() => onDelete(template.id)}>
            Delete
          </button>
        )}
      </div>
      {showRating && (
        <div className="template-rating-form">
          <StarRating rating={0} interactive onRate={(r) => { onRate?.(template.id, r); setShowRating(false); }} />
        </div>
      )}
    </div>
  );
}

export default function TemplateMarketplace({ boardId, onClose, onApplyTemplate }) {
  const [activeTab, setActiveTab] = useState('board');
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');

  const { data: marketplace = {}, isLoading } = useMarketplace({
    search: search || undefined,
    category: category || undefined,
    type: activeTab,
  });

  const applyMutation = useApplyBoardTemplate();
  const rateMutation = useRateTemplate();
  const deleteMutation = useDeleteBoardTemplate();

  const handleUse = async (template) => {
    if (activeTab === 'board' && boardId) {
      try {
        await applyMutation.mutateAsync({ templateId: template.id, boardId });
        onApplyTemplate?.();
        onClose?.();
      } catch (err) {
        console.error('Failed to apply template:', err);
      }
    }
  };

  const handleRate = (templateId, rating) => {
    rateMutation.mutate({ type: activeTab, id: templateId, rating });
  };

  const handleDelete = (templateId) => {
    if (confirm('Delete this template?')) {
      deleteMutation.mutate(templateId);
    }
  };

  const templates = activeTab === 'board'
    ? (marketplace.board_templates || [])
    : activeTab === 'workflow'
    ? (marketplace.workflow_templates || [])
    : [];

  return (
    <div className="marketplace-overlay" onClick={onClose}>
      <div className="marketplace" onClick={e => e.stopPropagation()}>
        <div className="marketplace-header">
          <h2>Template Marketplace</h2>
          <button className="marketplace-close" onClick={onClose}>&times;</button>
        </div>

        <div className="marketplace-tabs">
          {TABS.map(tab => (
            <button
              key={tab.key}
              className={`marketplace-tab ${activeTab === tab.key ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.key)}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="marketplace-filters">
          <input
            type="text"
            placeholder="Search templates..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="marketplace-search"
          />
          <select
            value={category}
            onChange={e => setCategory(e.target.value)}
            className="marketplace-category-select"
          >
            <option value="">All Categories</option>
            {CATEGORIES.map(c => (
              <option key={c} value={c}>{c.replace('-', ' ')}</option>
            ))}
          </select>
        </div>

        <div className="marketplace-grid">
          {isLoading ? (
            <div className="marketplace-loading">Loading templates...</div>
          ) : templates.length === 0 ? (
            <div className="marketplace-empty">No templates found. Save a board as template to get started.</div>
          ) : (
            templates.map(t => (
              <TemplateCard
                key={t.id}
                template={t}
                type={activeTab}
                onUse={activeTab === 'board' && boardId ? handleUse : undefined}
                onRate={handleRate}
                onDelete={handleDelete}
              />
            ))
          )}
        </div>
      </div>
    </div>
  );
}
