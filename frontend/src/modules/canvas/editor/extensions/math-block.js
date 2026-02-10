/**
 * Math block extension for Tiptap.
 *
 * Renders LaTeX content as a styled code block.
 * KaTeX rendering can be added later when the package is installed.
 *
 * Usage: editor.chain().focus().insertContent({ type: 'mathBlock', attrs: { content: 'E=mc^2' } }).run()
 *
 * @module canvas/editor/extensions/math-block
 */
import { Node, mergeAttributes } from '@tiptap/core';

const MathBlock = Node.create({
  name: 'mathBlock',
  group: 'block',
  atom: true,

  addAttributes() {
    return {
      content: {
        default: '',
        parseHTML: (element) => element.getAttribute('data-math-content') || element.textContent || '',
        renderHTML: (attributes) => ({
          'data-math-content': attributes.content,
        }),
      },
    };
  },

  parseHTML() {
    return [{ tag: 'div[data-math-content]' }];
  },

  renderHTML({ HTMLAttributes }) {
    return [
      'div',
      mergeAttributes(HTMLAttributes, {
        class: 'tiptap-math',
      }),
      ['code', { class: 'tiptap-math__content' }, HTMLAttributes['data-math-content'] || ''],
    ];
  },

  addCommands() {
    return {
      setMathBlock:
        (attributes) =>
        ({ commands }) => {
          return commands.insertContent({
            type: this.name,
            attrs: attributes,
          });
        },
    };
  },
});

export default MathBlock;
