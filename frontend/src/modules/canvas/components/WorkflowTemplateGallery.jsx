import { useState, useEffect } from 'react';
import { listTemplates } from '../../../api/workflows.js';
import { useUserTemplates } from '../../../api/queries/flowTemplateQueries.js';
import '../styles/WorkflowTemplateGallery.css';

const TEMPLATE_ICONS = {
  research_pipeline: '\uD83D\uDD2C',
  decision_matrix: '\u2696\uFE0F',
  content_pipeline: '\u270D\uFE0F',
  swot_analysis: '\uD83D\uDCCA',
  brainstorm_to_action: '\uD83D\uDCA1',
};

const CATEGORY_ICONS = {
  custom: '\u2699',
  research: '\uD83D\uDD2C',
  creative: '\u270D\uFE0F',
  analysis: '\uD83D\uDCCA',
};

export default function WorkflowTemplateGallery({ onSelect, onClose }) {
  const [systemTemplates, setSystemTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState('system');

  const { data: userTemplatesData, isLoading: userLoading } = useUserTemplates();
  const userTemplates = userTemplatesData?.templates || [];

  useEffect(() => {
    listTemplates()
      .then(setSystemTemplates)
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

        {/* Tabs */}
        <div className="wf-gallery__tabs">
          <button
            className={`wf-gallery__tab${tab === 'system' ? ' wf-gallery__tab--active' : ''}`}
            onClick={() => setTab('system')}
          >
            System
          </button>
          <button
            className={`wf-gallery__tab${tab === 'my' ? ' wf-gallery__tab--active' : ''}`}
            onClick={() => setTab('my')}
          >
            My Templates
          </button>
        </div>

        {/* System templates tab */}
        {tab === 'system' && (
          loading ? (
            <div className="wf-gallery__loading">Loading templates...</div>
          ) : (
            <div className="wf-gallery__grid">
              {systemTemplates.length === 0 ? (
                <div className="wf-gallery__empty">No system templates available.</div>
              ) : (
                systemTemplates.map((t) => (
                  <button key={t.id} className="wf-gallery__card" onClick={() => onSelect(t)}>
                    <span className="wf-gallery__icon">{TEMPLATE_ICONS[t.id] || '\u2699'}</span>
                    <h4>{t.name}</h4>
                    <p>{t.description}</p>
                    <span className="wf-gallery__steps">{t.steps.length} steps</span>
                  </button>
                ))
              )}
            </div>
          )
        )}

        {/* User templates tab */}
        {tab === 'my' && (
          userLoading ? (
            <div className="wf-gallery__loading">Loading your templates...</div>
          ) : (
            <div className="wf-gallery__grid">
              {userTemplates.length === 0 ? (
                <div className="wf-gallery__empty">
                  No saved templates yet. Build a workflow and save it as a template.
                </div>
              ) : (
                userTemplates.map((t) => (
                  <button key={t.id} className="wf-gallery__card" onClick={() => onSelect(t)}>
                    <span className="wf-gallery__icon">
                      {CATEGORY_ICONS[t.category] || CATEGORY_ICONS.custom}
                    </span>
                    <h4>{t.name}</h4>
                    {t.description && <p>{t.description}</p>}
                    <span className="wf-gallery__steps">
                      {(t.steps || []).length} steps
                    </span>
                  </button>
                ))
              )}
            </div>
          )
        )}
      </div>
    </div>
  );
}
