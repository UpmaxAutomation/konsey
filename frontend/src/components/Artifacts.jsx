import { useState, useEffect, useRef, useMemo } from 'react';
import './Artifacts.css';

/**
 * Artifacts component - renders HTML/CSS/JS code live in an iframe sandbox.
 * Similar to Claude's Artifacts feature.
 */
export default function Artifacts({ code, type = 'html', title = 'Preview' }) {
  const iframeRef = useRef(null);
  const [isExpanded, setIsExpanded] = useState(false);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('preview');

  // Parse code blocks from markdown
  const parsedCode = useMemo(() => {
    if (typeof code === 'object') {
      return code;
    }

    // Extract HTML, CSS, and JS from code blocks
    const htmlMatch = code.match(/```html\n([\s\S]*?)```/);
    const cssMatch = code.match(/```css\n([\s\S]*?)```/);
    const jsMatch = code.match(/```(?:javascript|js)\n([\s\S]*?)```/);

    return {
      html: htmlMatch ? htmlMatch[1] : code,
      css: cssMatch ? cssMatch[1] : '',
      js: jsMatch ? jsMatch[1] : ''
    };
  }, [code]);

  // Generate full HTML document
  const fullHtml = useMemo(() => {
    const { html, css, js } = parsedCode;

    return `
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      padding: 16px;
      line-height: 1.5;
    }
    ${css}
  </style>
</head>
<body>
  ${html}
  <script>
    try {
      ${js}
    } catch (e) {
      console.error('Artifact error:', e);
      document.body.innerHTML = '<pre style="color: red;">' + e.message + '</pre>';
    }
  </script>
</body>
</html>`;
  }, [parsedCode]);

  // Update iframe content
  useEffect(() => {
    if (iframeRef.current && activeTab === 'preview') {
      try {
        const doc = iframeRef.current.contentDocument;
        doc.open();
        doc.write(fullHtml);
        doc.close();
        setError(null);
      } catch (e) {
        setError(e.message);
      }
    }
  }, [fullHtml, activeTab]);

  return (
    <div className={`artifact ${isExpanded ? 'expanded' : ''}`}>
      <div className="artifact-header">
        <div className="artifact-title">
          <span className="artifact-icon">🎨</span>
          <span>{title}</span>
        </div>
        <div className="artifact-tabs">
          <button
            className={`artifact-tab ${activeTab === 'preview' ? 'active' : ''}`}
            onClick={() => setActiveTab('preview')}
          >
            Preview
          </button>
          <button
            className={`artifact-tab ${activeTab === 'code' ? 'active' : ''}`}
            onClick={() => setActiveTab('code')}
          >
            Code
          </button>
        </div>
        <div className="artifact-actions">
          <button
            className="artifact-btn"
            onClick={() => setIsExpanded(!isExpanded)}
            title={isExpanded ? 'Minimize' : 'Expand'}
          >
            {isExpanded ? '⊖' : '⊕'}
          </button>
          <button
            className="artifact-btn"
            onClick={() => {
              const blob = new Blob([fullHtml], { type: 'text/html' });
              const url = URL.createObjectURL(blob);
              window.open(url, '_blank');
            }}
            title="Open in new tab"
          >
            ↗
          </button>
        </div>
      </div>

      <div className="artifact-content">
        {activeTab === 'preview' ? (
          <>
            {error && (
              <div className="artifact-error">
                Error: {error}
              </div>
            )}
            <iframe
              ref={iframeRef}
              className="artifact-iframe"
              sandbox="allow-scripts allow-same-origin"
              title={title}
            />
          </>
        ) : (
          <div className="artifact-code">
            {parsedCode.html && (
              <div className="code-section">
                <div className="code-label">HTML</div>
                <pre><code>{parsedCode.html}</code></pre>
              </div>
            )}
            {parsedCode.css && (
              <div className="code-section">
                <div className="code-label">CSS</div>
                <pre><code>{parsedCode.css}</code></pre>
              </div>
            )}
            {parsedCode.js && (
              <div className="code-section">
                <div className="code-label">JavaScript</div>
                <pre><code>{parsedCode.js}</code></pre>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Detect if content contains renderable artifacts
 */
export function hasArtifact(content) {
  if (!content) return false;

  // Check for HTML code blocks
  if (content.includes('```html')) return true;

  // Check for artifact markers
  if (content.includes('<artifact>') || content.includes('<!-- artifact -->')) return true;

  // Check for common HTML patterns that suggest a full component
  const htmlPatterns = [
    /<div[^>]*class=/i,
    /<button[^>]*>/i,
    /<form[^>]*>/i,
    /<style>/i
  ];

  return htmlPatterns.some(pattern => pattern.test(content));
}

/**
 * Extract artifact code from content
 */
export function extractArtifact(content) {
  // Try to find artifact block
  const artifactMatch = content.match(/<artifact>([\s\S]*?)<\/artifact>/);
  if (artifactMatch) {
    return artifactMatch[1].trim();
  }

  // Try to find HTML code block
  const htmlMatch = content.match(/```html\n([\s\S]*?)```/);
  if (htmlMatch) {
    return content; // Return full content to extract CSS/JS too
  }

  return null;
}
