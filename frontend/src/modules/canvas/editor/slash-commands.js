/**
 * Slash command registry.
 * Each command: { title, icon, description, category, aliases, command(editor) }
 * To add a new slash command, append one object to this array.
 */
const commands = [
  {
    title: 'Heading 1',
    icon: 'H1',
    description: 'Large section heading',
    category: 'Text',
    aliases: ['h1', 'heading1'],
    command: (editor) => editor.chain().focus().toggleHeading({ level: 1 }).run(),
  },
  {
    title: 'Heading 2',
    icon: 'H2',
    description: 'Medium section heading',
    category: 'Text',
    aliases: ['h2', 'heading2'],
    command: (editor) => editor.chain().focus().toggleHeading({ level: 2 }).run(),
  },
  {
    title: 'Heading 3',
    icon: 'H3',
    description: 'Small section heading',
    category: 'Text',
    aliases: ['h3', 'heading3'],
    command: (editor) => editor.chain().focus().toggleHeading({ level: 3 }).run(),
  },
  {
    title: 'Bullet List',
    icon: '\u2022',
    description: 'Unordered list',
    category: 'Lists',
    aliases: ['ul', 'unordered', 'bullets'],
    command: (editor) => editor.chain().focus().toggleBulletList().run(),
  },
  {
    title: 'Numbered List',
    icon: '1.',
    description: 'Ordered list',
    category: 'Lists',
    aliases: ['ol', 'ordered', 'numbered'],
    command: (editor) => editor.chain().focus().toggleOrderedList().run(),
  },
  {
    title: 'Task List',
    icon: '\u2610',
    description: 'Checklist with checkboxes',
    category: 'Lists',
    aliases: ['todo', 'checklist', 'checkbox', 'task'],
    command: (editor) => editor.chain().focus().toggleTaskList().run(),
  },
  {
    title: 'Code Block',
    icon: '<>',
    description: 'Fenced code block',
    category: 'Advanced',
    aliases: ['code', 'pre', 'fenced'],
    command: (editor) => editor.chain().focus().toggleCodeBlock().run(),
  },
  {
    title: 'Blockquote',
    icon: '\u201C',
    description: 'Quote block',
    category: 'Advanced',
    aliases: ['quote', 'bq'],
    command: (editor) => editor.chain().focus().toggleBlockquote().run(),
  },
  {
    title: 'Horizontal Rule',
    icon: '\u2014',
    description: 'Divider line',
    category: 'Advanced',
    aliases: ['hr', 'divider', 'line'],
    command: (editor) => editor.chain().focus().setHorizontalRule().run(),
  },
  {
    title: 'Highlight',
    icon: 'Hi',
    description: 'Highlight text',
    category: 'Text',
    aliases: ['mark', 'yellow'],
    command: (editor) => editor.chain().focus().toggleHighlight().run(),
  },
  {
    title: 'Image',
    icon: '\u{1F5BC}',
    description: 'Insert image from URL',
    category: 'Advanced',
    aliases: ['img', 'picture', 'photo'],
    command: (editor) => {
      const url = window.prompt('Enter image URL:');
      if (url) {
        editor.chain().focus().setImage({ src: url }).run();
      }
    },
  },
  {
    title: 'Callout',
    icon: '\u2139',
    description: 'Colored callout box (info, warning, success, error)',
    category: 'Advanced',
    aliases: ['callout', 'admonition', 'alert', 'notice'],
    command: (editor) => editor.chain().focus().setCallout({ type: 'info' }).run(),
  },
  {
    title: 'Math',
    icon: '\u2211',
    description: 'Math formula block',
    category: 'Advanced',
    aliases: ['math', 'formula', 'equation', 'latex', 'katex'],
    command: (editor) => editor.chain().focus().insertContent({ type: 'mathBlock', attrs: { content: 'E = mc^2' } }).run(),
  },
  {
    title: 'Embed',
    icon: '\u29C9',
    description: 'Embed YouTube, Figma, or URL',
    category: 'Advanced',
    aliases: ['embed', 'iframe', 'youtube', 'video'],
    command: (editor) => {
      const url = window.prompt('Enter URL to embed:');
      if (url) editor.chain().focus().insertContent({ type: 'embed', attrs: { url } }).run();
    },
  },
];

/**
 * Filter commands by query string (fuzzy match on title and aliases).
 * @param {string} query
 * @returns {Array}
 */
export function filterCommands(query) {
  if (!query) return commands;
  const q = query.toLowerCase();
  return commands.filter((cmd) => {
    if (cmd.title.toLowerCase().includes(q)) return true;
    return cmd.aliases.some((a) => a.includes(q));
  });
}

/**
 * Group commands by category.
 * @param {Array} cmds
 * @returns {Object} { category: [commands] }
 */
export function groupByCategory(cmds) {
  const groups = {};
  for (const cmd of cmds) {
    if (!groups[cmd.category]) groups[cmd.category] = [];
    groups[cmd.category].push(cmd);
  }
  return groups;
}

export default commands;
