import { useState, useEffect } from 'react';
import { api } from '../api';
import './Templates.css';

export default function Templates({ isOpen, onClose, onSelectTemplate }) {
  const [templates, setTemplates] = useState([]);
  const [categories, setCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [variableValues, setVariableValues] = useState({});
  const [isCreating, setIsCreating] = useState(false);
  const [newTemplate, setNewTemplate] = useState({
    name: '',
    category: '',
    prompt_text: '',
    variables: []
  });
  const [extractedVariables, setExtractedVariables] = useState([]);

  useEffect(() => {
    if (isOpen) {
      loadTemplates();
      loadCategories();
    }
  }, [isOpen]);

  useEffect(() => {
    if (isOpen && selectedCategory) {
      loadTemplates(selectedCategory);
    }
  }, [selectedCategory]);

  const loadTemplates = async (category = null) => {
    try {
      const result = await api.listTemplates(category);
      setTemplates(result.templates);
    } catch (error) {
      console.error('Failed to load templates:', error);
      alert('Failed to load templates');
    }
  };

  const loadCategories = async () => {
    try {
      const result = await api.getTemplateCategories();
      setCategories(result.categories);
    } catch (error) {
      console.error('Failed to load categories:', error);
    }
  };

  const handleTemplateClick = (template) => {
    setSelectedTemplate(template);
    // Reset variable values
    const initialValues = {};
    template.variables.forEach(varName => {
      initialValues[varName] = '';
    });
    setVariableValues(initialValues);
  };

  const handleVariableChange = (varName, value) => {
    setVariableValues(prev => ({
      ...prev,
      [varName]: value
    }));
  };

  const handleUseTemplate = async () => {
    if (!selectedTemplate) return;

    // Check if all variables are filled
    const allFilled = selectedTemplate.variables.every(
      varName => variableValues[varName]?.trim()
    );

    if (!allFilled) {
      alert('Please fill in all variables');
      return;
    }

    try {
      const result = await api.fillTemplate(selectedTemplate.id, variableValues);
      onSelectTemplate(result.prompt_text);
      onClose();
    } catch (error) {
      console.error('Failed to fill template:', error);
      alert('Failed to fill template');
    }
  };

  const extractVariablesFromText = (text) => {
    const regex = /\{\{(\w+)\}\}/g;
    const vars = new Set();
    let match;
    while ((match = regex.exec(text)) !== null) {
      vars.add(match[1]);
    }
    return Array.from(vars);
  };

  const handleNewTemplateTextChange = (text) => {
    setNewTemplate(prev => ({ ...prev, prompt_text: text }));
    const extracted = extractVariablesFromText(text);
    setExtractedVariables(extracted);
  };

  const handleCreateTemplate = async () => {
    if (!newTemplate.name || !newTemplate.category || !newTemplate.prompt_text) {
      alert('Please fill in all required fields');
      return;
    }

    try {
      const templateData = {
        ...newTemplate,
        variables: extractedVariables
      };
      await api.createTemplate(templateData);
      alert('Template created successfully!');
      setIsCreating(false);
      setNewTemplate({
        name: '',
        category: '',
        prompt_text: '',
        variables: []
      });
      setExtractedVariables([]);
      loadTemplates();
    } catch (error) {
      console.error('Failed to create template:', error);
      alert('Failed to create template');
    }
  };

  const handleDeleteTemplate = async (templateId, isDefault) => {
    if (isDefault) {
      alert('Cannot delete default templates');
      return;
    }

    if (!confirm('Are you sure you want to delete this template?')) {
      return;
    }

    try {
      await api.deleteTemplate(templateId);
      alert('Template deleted successfully');
      loadTemplates();
      if (selectedTemplate?.id === templateId) {
        setSelectedTemplate(null);
      }
    } catch (error) {
      console.error('Failed to delete template:', error);
      alert('Failed to delete template');
    }
  };

  const filteredTemplates = templates.filter(template =>
    template.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    template.category.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="templates-modal" role="dialog" aria-modal="true" aria-label="Prompt templates" onClick={(e) => e.stopPropagation()}>
        <div className="templates-header">
          <h2>Prompt Templates</h2>
          <button className="close-button" onClick={onClose}>×</button>
        </div>

        <div className="templates-actions">
          <button
            className="create-template-button"
            onClick={() => setIsCreating(!isCreating)}
          >
            {isCreating ? 'Cancel' : '+ Create Template'}
          </button>
        </div>

        {isCreating ? (
          <div className="create-template-form">
            <h3>Create Custom Template</h3>
            <div className="form-group">
              <label>Template Name *</label>
              <input
                type="text"
                value={newTemplate.name}
                onChange={(e) => setNewTemplate({ ...newTemplate, name: e.target.value })}
                placeholder="e.g., Product Launch Email"
              />
            </div>
            <div className="form-group">
              <label>Category *</label>
              <input
                type="text"
                value={newTemplate.category}
                onChange={(e) => setNewTemplate({ ...newTemplate, category: e.target.value })}
                placeholder="e.g., marketing"
                list="category-suggestions"
              />
              <datalist id="category-suggestions">
                {categories.map(cat => (
                  <option key={cat} value={cat} />
                ))}
              </datalist>
            </div>
            <div className="form-group">
              <label>Prompt Text *</label>
              <textarea
                value={newTemplate.prompt_text}
                onChange={(e) => handleNewTemplateTextChange(e.target.value)}
                placeholder="Write your prompt here. Use {{variable_name}} for placeholders."
                rows={6}
              />
              {extractedVariables.length > 0 && (
                <div className="extracted-variables">
                  <strong>Detected variables:</strong> {extractedVariables.join(', ')}
                </div>
              )}
            </div>
            <button className="create-button" onClick={handleCreateTemplate}>
              Create Template
            </button>
          </div>
        ) : (
          <>
            <div className="templates-filters">
              <input
                type="text"
                className="search-input"
                placeholder="Search templates..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
              <div className="category-filters">
                <button
                  className={selectedCategory === null ? 'category-chip active' : 'category-chip'}
                  onClick={() => setSelectedCategory(null)}
                >
                  All
                </button>
                {categories.map(category => (
                  <button
                    key={category}
                    className={selectedCategory === category ? 'category-chip active' : 'category-chip'}
                    onClick={() => setSelectedCategory(category)}
                  >
                    {category}
                  </button>
                ))}
              </div>
            </div>

            <div className="templates-content">
              <div className="templates-list">
                {filteredTemplates.length === 0 ? (
                  <div className="empty-state">
                    <p>No templates found</p>
                  </div>
                ) : (
                  filteredTemplates.map(template => (
                    <div
                      key={template.id}
                      className={`template-item ${selectedTemplate?.id === template.id ? 'active' : ''}`}
                      onClick={() => handleTemplateClick(template)}
                    >
                      <div className="template-item-header">
                        <h4>{template.name}</h4>
                        {!template.is_default && (
                          <button
                            className="delete-template-button"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDeleteTemplate(template.id, template.is_default);
                            }}
                            title="Delete template"
                          >
                            🗑️
                          </button>
                        )}
                      </div>
                      <span className="template-category">{template.category}</span>
                      {template.is_default && (
                        <span className="default-badge">Default</span>
                      )}
                    </div>
                  ))
                )}
              </div>

              <div className="template-preview">
                {selectedTemplate ? (
                  <>
                    <h3>{selectedTemplate.name}</h3>
                    <div className="template-prompt">
                      {selectedTemplate.prompt_text}
                    </div>

                    {selectedTemplate.variables.length > 0 && (
                      <>
                        <h4>Fill in the variables:</h4>
                        <div className="variables-form">
                          {selectedTemplate.variables.map(varName => (
                            <div key={varName} className="variable-input-group">
                              <label>{varName}</label>
                              <input
                                type="text"
                                value={variableValues[varName] || ''}
                                onChange={(e) => handleVariableChange(varName, e.target.value)}
                                placeholder={`Enter ${varName}`}
                              />
                            </div>
                          ))}
                        </div>
                        <button
                          className="use-template-button"
                          onClick={handleUseTemplate}
                        >
                          Use Template
                        </button>
                      </>
                    )}
                  </>
                ) : (
                  <div className="empty-state">
                    <p>Select a template to preview</p>
                  </div>
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
