import ReactMarkdown from 'react-markdown';

// Allowed HTML elements for safe markdown rendering
// This prevents XSS by blocking dangerous elements like script, iframe, object, etc.
const ALLOWED_ELEMENTS = [
  'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
  'p', 'br', 'hr',
  'ul', 'ol', 'li',
  'blockquote', 'pre', 'code',
  'strong', 'em', 'del', 's',
  'a', 'img',
  'table', 'thead', 'tbody', 'tr', 'th', 'td',
  'div', 'span',
  'sup', 'sub',
  'details', 'summary',
];

// URLs must start with safe protocols only
const isSafeUrl = (url) => {
  if (!url) return true;
  const trimmed = url.trim().toLowerCase();
  return (
    trimmed.startsWith('http://') ||
    trimmed.startsWith('https://') ||
    trimmed.startsWith('mailto:') ||
    trimmed.startsWith('#') ||
    trimmed.startsWith('/')
  );
};

// Transform links to ensure they're safe
const transformLinkUri = (uri) => {
  if (!isSafeUrl(uri)) {
    console.warn('Blocked unsafe URL in markdown:', uri);
    return '';
  }
  return uri;
};

// Transform image sources to ensure they're safe
const transformImageUri = (uri) => {
  if (!uri) return '';
  const trimmed = uri.trim().toLowerCase();
  // Only allow http(s) and data: (for base64 images)
  if (
    trimmed.startsWith('http://') ||
    trimmed.startsWith('https://') ||
    trimmed.startsWith('data:image/')
  ) {
    return uri;
  }
  console.warn('Blocked unsafe image URL in markdown:', uri);
  return '';
};

export default function SafeMarkdown({ children, className, components: customComponents, ...props }) {
  // Default safe components
  const safeComponents = {
    a: ({ node, href, children, ...linkProps }) => (
      <a
        href={href}
        target={href?.startsWith('http') ? '_blank' : undefined}
        rel={href?.startsWith('http') ? 'noopener noreferrer' : undefined}
        {...linkProps}
      >
        {children}
      </a>
    ),
    img: ({ node, src, alt, ...imgProps }) => (
      <img
        src={transformImageUri(src)}
        alt={alt || ''}
        {...imgProps}
      />
    ),
  };

  // Merge custom components with safe defaults (custom takes precedence except for security-critical ones)
  const mergedComponents = {
    ...customComponents,
    // Always use safe link and image components
    a: safeComponents.a,
    img: safeComponents.img,
    // Allow custom code blocks (common use case for syntax highlighting)
    ...(customComponents?.code && { code: customComponents.code }),
  };

  return (
    <ReactMarkdown
      allowedElements={ALLOWED_ELEMENTS}
      unwrapDisallowed={true}
      urlTransform={transformLinkUri}
      components={mergedComponents}
      {...props}
    >
      {children}
    </ReactMarkdown>
  );
}
