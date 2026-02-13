import { Node, mergeAttributes } from '@tiptap/core';
import { ReactNodeViewRenderer } from '@tiptap/react';
import CardEmbedView from './CardEmbedView';

const CardEmbedExtension = Node.create({
  name: 'cardEmbed',
  group: 'block',
  atom: true,
  draggable: true,

  addAttributes() {
    return {
      cardId: { default: null },
      cardTitle: { default: 'Untitled' },
      cardType: { default: 'note' },
      cardContent: { default: '' },
    };
  },

  parseHTML() {
    return [{ tag: 'div[data-card-embed]' }];
  },

  renderHTML({ HTMLAttributes }) {
    return ['div', mergeAttributes({ 'data-card-embed': '' }, HTMLAttributes)];
  },

  addNodeView() {
    return ReactNodeViewRenderer(CardEmbedView);
  },

  addCommands() {
    return {
      insertCardEmbed: (attrs) => ({ commands }) => {
        return commands.insertContent({
          type: this.name,
          attrs,
        });
      },
    };
  },
});

export default CardEmbedExtension;
