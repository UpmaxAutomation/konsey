/**
 * Markdown bridge utilities.
 * Converts between markdown strings and Tiptap editor content.
 * Content stored in DB is always markdown — Tiptap reads/writes it transparently
 * via the tiptap-markdown extension.
 */

/**
 * Get markdown string from a Tiptap editor instance.
 * @param {import('@tiptap/react').Editor} editor
 * @returns {string} Markdown content
 */
export function toMarkdown(editor) {
  if (!editor) return '';
  return editor.storage.markdown?.getMarkdown?.() ?? editor.getText();
}

/**
 * Check if editor content is effectively empty.
 * @param {import('@tiptap/react').Editor} editor
 * @returns {boolean}
 */
export function isEditorEmpty(editor) {
  if (!editor) return true;
  return editor.isEmpty;
}
