/**
 * Callout block extension for Tiptap.
 *
 * Renders colored callout boxes with type variants:
 * info, warning, success, error.
 *
 * Usage: editor.chain().focus().setCallout({ type: 'info' }).run()
 *
 * @module canvas/editor/extensions/callout
 */
import { Node, mergeAttributes } from '@tiptap/core';

const Callout = Node.create({
  name: 'callout',
  group: 'block',
  content: 'block+',
  defining: true,

  addAttributes() {
    return {
      type: {
        default: 'info',
        parseHTML: (element) => element.getAttribute('data-callout') || 'info',
        renderHTML: (attributes) => ({
          'data-callout': attributes.type,
        }),
      },
    };
  },

  parseHTML() {
    return [{ tag: 'div[data-callout]' }];
  },

  renderHTML({ HTMLAttributes }) {
    const type = HTMLAttributes['data-callout'] || 'info';
    return [
      'div',
      mergeAttributes(HTMLAttributes, {
        class: `tiptap-callout tiptap-callout--${type}`,
        'data-callout': type,
      }),
      0,
    ];
  },

  addCommands() {
    return {
      setCallout:
        (attributes) =>
        ({ commands }) => {
          return commands.wrapIn(this.name, attributes);
        },
      toggleCallout:
        (attributes) =>
        ({ commands }) => {
          return commands.toggleWrap(this.name, attributes);
        },
    };
  },

  addKeyboardShortcuts() {
    return {
      'Mod-Shift-c': () => this.editor.commands.toggleCallout({ type: 'info' }),
    };
  },
});

export default Callout;
