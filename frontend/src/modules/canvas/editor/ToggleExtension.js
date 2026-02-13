/**
 * Toggle / Collapsible block extension for Tiptap.
 *
 * Renders as <details><summary> HTML elements so content can
 * be collapsed and expanded natively.
 *
 * Usage: editor.chain().focus().setToggle().run()
 *
 * @module canvas/editor/ToggleExtension
 */
import { Node, mergeAttributes } from '@tiptap/core';

const ToggleBlock = Node.create({
  name: 'toggleBlock',
  group: 'block',
  content: 'block+',
  defining: true,

  addAttributes() {
    return {
      open: {
        default: true,
        parseHTML: (element) => element.hasAttribute('open'),
        renderHTML: (attributes) => (attributes.open ? { open: '' } : {}),
      },
    };
  },

  parseHTML() {
    return [{ tag: 'details' }];
  },

  renderHTML({ HTMLAttributes }) {
    return [
      'details',
      mergeAttributes(HTMLAttributes, { class: 'tiptap-toggle' }),
      ['summary', { class: 'tiptap-toggle__summary' }, 'Toggle'],
      ['div', { class: 'tiptap-toggle__content' }, 0],
    ];
  },

  addCommands() {
    return {
      setToggle:
        () =>
        ({ commands }) => {
          return commands.wrapIn(this.name);
        },
      toggleToggle:
        () =>
        ({ commands }) => {
          return commands.toggleWrap(this.name);
        },
    };
  },
});

export default ToggleBlock;
