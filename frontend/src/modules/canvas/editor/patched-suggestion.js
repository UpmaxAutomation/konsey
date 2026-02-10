/**
 * Patched wrapper around @tiptap/suggestion.
 *
 * Fixes a bug in @tiptap/suggestion@3.19.0 where the plugin's `view().update()`
 * arrow function captures `this.key` expecting a PluginKey instance, but
 * ProseMirror's Plugin sets `this.key` to a plain string. This causes
 * `this.key.getState()` to crash with "getState is not a function".
 *
 * Also ensures the pluginKey is always a proper PluginKey instance
 * (card-mention was passing a bare string).
 *
 * @module canvas/editor/patched-suggestion
 */
import Suggestion from '@tiptap/suggestion';
import { PluginKey } from '@tiptap/pm/state';

export default function PatchedSuggestion(options) {
  // Coerce string pluginKey to a proper PluginKey instance
  if (options.pluginKey && typeof options.pluginKey === 'string') {
    options = { ...options, pluginKey: new PluginKey(options.pluginKey) };
  }

  const plugin = Suggestion(options);
  const pluginKey = options.pluginKey || plugin.spec.key;

  // Patch view() so the arrow functions inside capture this.key = pluginKey
  // (a PluginKey with .getState) instead of the plain string ProseMirror assigns.
  const originalView = plugin.spec.view;
  if (originalView) {
    plugin.spec.view = function (editorView) {
      return originalView.call({ key: pluginKey }, editorView);
    };
  }

  return plugin;
}
