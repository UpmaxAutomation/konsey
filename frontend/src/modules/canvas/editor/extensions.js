/**
 * Tiptap extension registry.
 * All editor extensions configured in one place.
 */
import StarterKit from '@tiptap/starter-kit';
import Placeholder from '@tiptap/extension-placeholder';
import TaskList from '@tiptap/extension-task-list';
import TaskItem from '@tiptap/extension-task-item';
import Highlight from '@tiptap/extension-highlight';
import Typography from '@tiptap/extension-typography';
import Image from '@tiptap/extension-image';
import CharacterCount from '@tiptap/extension-character-count';
import { Markdown } from 'tiptap-markdown';

/**
 * Build the extension array for the card editor.
 *
 * SlashCommands and CardMention are disabled until the upstream
 * @tiptap/suggestion plugin is fixed (getState crash in v3.19).
 *
 * @param {Object} opts
 * @param {string} [opts.placeholder] - Placeholder text for empty editor
 * @returns {Array} Tiptap extensions
 */
export function buildExtensions({ placeholder = 'Start writing...' } = {}) {
  return [
    StarterKit.configure({
      heading: { levels: [1, 2, 3] },
      codeBlock: { HTMLAttributes: { class: 'tiptap-code-block' } },
      blockquote: { HTMLAttributes: { class: 'tiptap-blockquote' } },
      link: false,
    }),
    Placeholder.configure({
      placeholder,
      emptyEditorClass: 'tiptap-empty',
    }),
    Markdown.configure({
      html: false,
      transformPastedText: true,
      transformCopiedText: true,
    }),
    TaskList,
    TaskItem.configure({ nested: true }),
    Highlight.configure({ multicolor: false }),
    Typography,
    Image.configure({
      inline: false,
      allowBase64: true,
      HTMLAttributes: { class: 'tiptap-image' },
    }),
    CharacterCount,
  ];
}
