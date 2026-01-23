/**
 * ImageGenerator - AI Image Generation Interface.
 *
 * Features:
 * - Multiple providers (DALL-E 3, SDXL, FLUX)
 * - Size and quality options
 * - Image history gallery
 * - Download and copy functionality
 */

import React, { useState, useEffect } from 'react';
import { api } from '../api';
import './ImageGenerator.css';

const SIZE_OPTIONS = [
  { value: '1024x1024', label: 'Square (1024×1024)' },
  { value: '1792x1024', label: 'Landscape (1792×1024)' },
  { value: '1024x1792', label: 'Portrait (1024×1792)' },
];

const QUALITY_OPTIONS = [
  { value: 'standard', label: 'Standard' },
  { value: 'hd', label: 'HD' },
];

const STYLE_OPTIONS = [
  { value: 'vivid', label: 'Vivid' },
  { value: 'natural', label: 'Natural' },
];

export default function ImageGenerator({ onClose }) {
  const [prompt, setPrompt] = useState('');
  const [provider, setProvider] = useState('dalle-3');
  const [size, setSize] = useState('1024x1024');
  const [quality, setQuality] = useState('standard');
  const [style, setStyle] = useState('vivid');
  const [isGenerating, setIsGenerating] = useState(false);
  const [currentImage, setCurrentImage] = useState(null);
  const [imageHistory, setImageHistory] = useState([]);
  const [providers, setProviders] = useState([]);
  const [error, setError] = useState(null);

  // Load providers
  useEffect(() => {
    const loadProviders = async () => {
      try {
        const result = await api.getImageProviders();
        setProviders(result.providers || []);
      } catch (err) {
        console.error('Failed to load providers:', err);
      }
    };
    loadProviders();
  }, []);

  // Load history
  useEffect(() => {
    const loadHistory = async () => {
      try {
        const result = await api.listImages(20);
        setImageHistory(result.images || []);
      } catch (err) {
        console.error('Failed to load history:', err);
      }
    };
    loadHistory();
  }, []);

  const handleGenerate = async (e) => {
    e.preventDefault();
    if (!prompt.trim() || isGenerating) return;

    setError(null);
    setIsGenerating(true);

    try {
      const result = await api.generateImage({
        prompt: prompt.trim(),
        provider,
        size,
        quality,
        style,
      });

      setCurrentImage(result);
      setImageHistory(prev => [result, ...prev]);
      setPrompt('');
    } catch (err) {
      setError(err.message);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleDownload = (image) => {
    if (image.url) {
      window.open(image.url, '_blank');
    } else if (image.base64_data) {
      const link = document.createElement('a');
      link.href = `data:image/png;base64,${image.base64_data}`;
      link.download = `image-${image.id}.png`;
      link.click();
    }
  };

  const handleCopyPrompt = (promptText) => {
    navigator.clipboard.writeText(promptText);
  };

  const handleDelete = async (imageId) => {
    try {
      await api.deleteImage(imageId);
      setImageHistory(prev => prev.filter(img => img.id !== imageId));
      if (currentImage?.id === imageId) {
        setCurrentImage(null);
      }
    } catch (err) {
      setError(err.message);
    }
  };

  const getImageSrc = (image) => {
    if (image.url) return image.url;
    if (image.base64_data) return `data:image/png;base64,${image.base64_data}`;
    return null;
  };

  const selectedProvider = providers.find(p => p.id === provider);

  return (
    <div className="image-generator">
      <div className="ig-header">
        <h2>
          <span className="ig-icon">🎨</span>
          Image Generator
        </h2>
        <p className="ig-description">
          Create stunning images with AI using DALL-E, Stable Diffusion, or FLUX.
        </p>
        {onClose && (
          <button className="close-btn" onClick={onClose}>×</button>
        )}
      </div>

      <div className="ig-content">
        <form className="ig-form" onSubmit={handleGenerate}>
          <div className="ig-prompt-row">
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Describe the image you want to create..."
              rows={3}
              disabled={isGenerating}
            />
          </div>

          <div className="ig-options">
            <div className="ig-option">
              <label>Provider</label>
              <select
                value={provider}
                onChange={(e) => setProvider(e.target.value)}
                disabled={isGenerating}
              >
                {providers.map(p => (
                  <option key={p.id} value={p.id} disabled={!p.available}>
                    {p.name} {!p.available && '(Not configured)'}
                  </option>
                ))}
              </select>
            </div>

            <div className="ig-option">
              <label>Size</label>
              <select
                value={size}
                onChange={(e) => setSize(e.target.value)}
                disabled={isGenerating}
              >
                {SIZE_OPTIONS.map(opt => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>

            {provider.includes('dalle') && (
              <>
                <div className="ig-option">
                  <label>Quality</label>
                  <select
                    value={quality}
                    onChange={(e) => setQuality(e.target.value)}
                    disabled={isGenerating}
                  >
                    {QUALITY_OPTIONS.map(opt => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                </div>

                <div className="ig-option">
                  <label>Style</label>
                  <select
                    value={style}
                    onChange={(e) => setStyle(e.target.value)}
                    disabled={isGenerating}
                  >
                    {STYLE_OPTIONS.map(opt => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                </div>
              </>
            )}
          </div>

          <button
            type="submit"
            className="ig-generate-btn"
            disabled={!prompt.trim() || isGenerating}
          >
            {isGenerating ? (
              <>
                <span className="spinner"></span>
                Generating...
              </>
            ) : (
              <>
                <span>✨</span>
                Generate Image
              </>
            )}
          </button>
        </form>

        {error && (
          <div className="ig-error">
            <strong>Error:</strong> {error}
            <button onClick={() => setError(null)}>×</button>
          </div>
        )}

        {/* Current Image */}
        {currentImage && !currentImage.error && (
          <div className="ig-current">
            <div className="ig-image-container">
              <img
                src={getImageSrc(currentImage)}
                alt={currentImage.prompt}
              />
              <div className="ig-image-overlay">
                <button onClick={() => handleDownload(currentImage)} title="Download">
                  ⬇️
                </button>
                <button onClick={() => handleCopyPrompt(currentImage.prompt)} title="Copy prompt">
                  📋
                </button>
              </div>
            </div>
            {currentImage.revised_prompt && (
              <div className="ig-revised-prompt">
                <strong>Revised prompt:</strong> {currentImage.revised_prompt}
              </div>
            )}
          </div>
        )}

        {/* History Gallery */}
        {imageHistory.length > 0 && (
          <div className="ig-history">
            <h3>Recent Generations</h3>
            <div className="ig-gallery">
              {imageHistory.filter(img => !img.error).map(image => (
                <div
                  key={image.id}
                  className={`ig-thumbnail ${currentImage?.id === image.id ? 'active' : ''}`}
                  onClick={() => setCurrentImage(image)}
                >
                  {image.has_base64 || image.base64_data ? (
                    <img
                      src={getImageSrc(image)}
                      alt={image.prompt}
                    />
                  ) : image.url ? (
                    <img src={image.url} alt={image.prompt} />
                  ) : (
                    <div className="ig-placeholder">🖼️</div>
                  )}
                  <button
                    className="ig-delete-btn"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDelete(image.id);
                    }}
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
