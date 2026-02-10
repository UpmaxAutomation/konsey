/**
 * Slash command Tiptap extension.
 * Wires @tiptap/suggestion to trigger SlashMenu on "/" input.
 *
 * @module canvas/editor/slash-extension
 */
import { Extension } from '@tiptap/react';
import { PluginKey } from '@tiptap/pm/state';
import Suggestion from './patched-suggestion';
import { ReactRenderer } from '@tiptap/react';
import tippy from 'tippy.js';
import SlashMenu from './SlashMenu';

const SlashCommandsPluginKey = new PluginKey('slashCommands');

const SlashCommands = Extension.create({
  name: 'slashCommands',

  addOptions() {
    return { suggestion: {} };
  },

  addProseMirrorPlugins() {
    return [
      Suggestion({
        editor: this.editor,
        char: '/',
        pluginKey: SlashCommandsPluginKey,
        startOfLine: false,
        command: ({ editor, range }) => {
          // Delete the "/" trigger character and query text
          editor.chain().focus().deleteRange(range).run();
        },
        items: ({ query }) => {
          // Return query as a single-element array; filtering happens in SlashMenu
          return [query];
        },
        render: () => {
          let component;
          let popup;

          return {
            onStart(props) {
              component = new ReactRenderer(SlashMenu, {
                props: { ...props, query: '', editor: props.editor },
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
              const query = props.query || '';
              component?.updateProps({ ...props, query, editor: props.editor });

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
});

export default SlashCommands;
