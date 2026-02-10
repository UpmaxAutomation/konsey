/**
 * Embed block extension for Tiptap.
 *
 * Supports YouTube, Figma, and generic URL embeds.
 * YouTube and Figma URLs render as responsive iframes.
 * Other URLs render as a styled link card.
 *
 * Usage: editor.chain().focus().setEmbed({ url: 'https://...' }).run()
 *
 * @module canvas/editor/extensions/embed
 */
import { Node, mergeAttributes } from '@tiptap/core';

/**
 * Detect embed type from URL.
 * @param {string} url
 * @returns {'youtube'|'figma'|'generic'}
 */
function detectType(url) {
  if (!url) return 'generic';
  if (/youtube\.com\/watch|youtu\.be\/|youtube\.com\/embed/i.test(url)) return 'youtube';
  if (/figma\.com/i.test(url)) return 'figma';
  return 'generic';
}

/**
 * Convert a YouTube watch URL to an embed URL.
 * @param {string} url
 * @returns {string}
 */
function toYouTubeEmbed(url) {
  const match = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\s]+)/);
  if (match) return `https://www.youtube.com/embed/${match[1]}`;
  return url;
}

const Embed = Node.create({
  name: 'embed',
  group: 'block',
  atom: true,

  addAttributes() {
    return {
      url: {
        default: '',
        parseHTML: (element) => element.getAttribute('data-embed-url') || '',
        renderHTML: (attributes) => ({
          'data-embed-url': attributes.url,
        }),
      },
      type: {
        default: 'generic',
        parseHTML: (element) => element.getAttribute('data-embed-type') || 'generic',
        renderHTML: (attributes) => ({
          'data-embed-type': attributes.type,
        }),
      },
    };
  },

  parseHTML() {
    return [{ tag: 'div[data-embed-url]' }];
  },

  renderHTML({ HTMLAttributes }) {
    const url = HTMLAttributes['data-embed-url'] || '';
    const type = detectType(url);

    if (type === 'youtube') {
      return [
        'div',
        mergeAttributes(HTMLAttributes, {
          class: 'tiptap-embed tiptap-embed--youtube',
          'data-embed-type': 'youtube',
        }),
        [
          'iframe',
          {
            src: toYouTubeEmbed(url),
            frameborder: '0',
            allowfullscreen: 'true',
            allow: 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture',
            class: 'tiptap-embed__iframe',
          },
        ],
      ];
    }

    if (type === 'figma') {
      return [
        'div',
        mergeAttributes(HTMLAttributes, {
          class: 'tiptap-embed tiptap-embed--figma',
          'data-embed-type': 'figma',
        }),
        [
          'iframe',
          {
            src: `https://www.figma.com/embed?embed_host=tiptap&url=${encodeURIComponent(url)}`,
            frameborder: '0',
            allowfullscreen: 'true',
            class: 'tiptap-embed__iframe',
          },
        ],
      ];
    }

    // Generic: render as a link card
    return [
      'div',
      mergeAttributes(HTMLAttributes, {
        class: 'tiptap-embed tiptap-embed--generic',
        'data-embed-type': 'generic',
      }),
      [
        'a',
        {
          href: url,
          target: '_blank',
          rel: 'noopener noreferrer',
          class: 'tiptap-embed__link',
        },
        url,
      ],
    ];
  },

  addCommands() {
    return {
      setEmbed:
        (attributes) =>
        ({ commands }) => {
          const url = attributes?.url || '';
          return commands.insertContent({
            type: this.name,
            attrs: { url, type: detectType(url) },
          });
        },
    };
  },
});

export default Embed;
