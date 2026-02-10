/**
 * Card mention Tiptap extension.
 *
 * Triggers on [[ to show a card search popup.
 * Renders as an inline pill: [[Title]]
 * Serialises to text as [[Title|id]] for markdown round-tripping.
 *
 * Board cards are injected via `editor.storage.cardMention.cards`
 * which TiptapEditor keeps in sync via a useEffect.
 *
 * @module canvas/editor/card-mention
 */
import { Node, mergeAttributes } from '@tiptap/react';
import { ReactRenderer } from '@tiptap/react';
import { PluginKey } from '@tiptap/pm/state';
import Suggestion from './patched-suggestion';
import tippy from 'tippy.js';
import CardMention from './CardMention';

const CardMentionPluginKey = new PluginKey('cardMention');

const CardMentionNode = Node.create({
  name: 'cardMention',
  group: 'inline',
  inline: true,
  selectable: false,
  atom: true,

  addAttributes() {
    return {
      id: { default: null },
      label: { default: null },
      cardType: { default: 'note' },
    };
  },

  parseHTML() {
    return [{ tag: 'span[data-card-mention]' }];
  },

  renderHTML({ node, HTMLAttributes }) {
    return [
      'span',
      mergeAttributes(HTMLAttributes, {
        'data-card-mention': node.attrs.id,
        'data-card-type': node.attrs.cardType,
        class: 'card-mention-inline',
        style: 'cursor: pointer;',
      }),
      `[[${node.attrs.label}]]`,
    ];
  },

  renderText({ node }) {
    return `[[${node.attrs.label}|${node.attrs.id}]]`;
  },

  addKeyboardShortcuts() {
    return {};
  },

  addProseMirrorPlugins() {
    const editor = this.editor;

    return [
      Suggestion({
        editor,
        char: '[[',
        pluginKey: CardMentionPluginKey,

        /**
         * Insert a cardMention node when the user picks a card.
         */
        command: ({ editor: ed, range, props }) => {
          ed.chain()
            .focus()
            .deleteRange(range)
            .insertContent({
              type: 'cardMention',
              attrs: {
                id: props.id,
                label: props.title || 'Untitled',
                cardType: props.extra?.is_knowledge ? 'knowledge' : props.card_type,
              },
            })
            .run();
        },

        /**
         * Filter the board cards list by the user's query.
         * Returns at most 10 results.
         */
        items: ({ query }) => {
          const cards = editor.storage.cardMention?.cards || [];
          if (!query) return cards.slice(0, 10);
          const q = query.toLowerCase();
          return cards
            .filter((c) => (c.title || '').toLowerCase().includes(q))
            .slice(0, 10);
        },

        /**
         * Render lifecycle using tippy.js + ReactRenderer.
         */
        render: () => {
          let component;
          let popup;

          return {
            onStart(props) {
              component = new ReactRenderer(CardMention, {
                props,
                editor: props.editor,
              });

              popup = tippy('body', {
                getReferenceClientRect: props.clientRect,
                appendTo: () => document.body,
                content: component.element,
                showOnCreate: true,
                interactive: true,
                trigger: 'manual',
                placement: 'bottom-start',
                offset: [0, 4],
              });
            },

            onUpdate(props) {
              component?.updateProps(props);
              if (popup?.[0]) {
                popup[0].setProps({ getReferenceClientRect: props.clientRect });
              }
            },

            onKeyDown(props) {
              if (props.event.key === 'Escape') {
                popup?.[0]?.hide();
                return true;
              }
              return component?.ref?.onKeyDown(props) ?? false;
            },

            onExit() {
              popup?.[0]?.destroy();
              component?.destroy();
            },
          };
        },
      }),
    ];
  },

  addStorage() {
    return { cards: [] };
  },
});

export default CardMentionNode;
