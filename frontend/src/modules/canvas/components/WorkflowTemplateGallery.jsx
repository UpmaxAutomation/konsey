import { useState, useEffect } from 'react';
import { listTemplates } from '../../../api/workflows.js';
import '../styles/WorkflowTemplateGallery.css';

const TEMPLATE_ICONS = {
  research_pipeline: '\uD83D\uDD2C',
  decision_matrix: '\u2696\uFE0F',
  content_pipeline: '\u270D\uFE0F',
  swot_analysis: '\uD83D\uDCCA',
  brainstorm_to_action: '\uD83D\uDCA1',
};

export default function WorkflowTemplateGallery({ onSelect, onClose }) {
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listTemplates()
      .then(setTemplates)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="wf-gallery-overlay" onClick={onClose}>
      <div className="wf-gallery" onClick={(e) => e.stopPropagation()}>
        <div className="wf-gallery__header">
          <h3>Workflow Templates</h3>
          <button className="wf-gallery__close" onClick={onClose}>&times;</button>
        </div>
        {loading ? (
          <div className="wf-gallery__loading">Loading templates...</div>
        ) : (
          <div className="wf-gallery__grid">
            {templates.map((t) => (
              <button key={t.id} className="wf-gallery__card" onClick={() => onSelect(t)}>
                <span className="wf-gallery__icon">{TEMPLATE_ICONS[t.id] || '\u2699'}</span>
                <h4>{t.name}</h4>
                <p>{t.description}</p>
                <span className="wf-gallery__steps">{t.steps.length} steps</span>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
