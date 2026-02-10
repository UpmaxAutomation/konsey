/**
 * Card template definitions.
 * Each template is a pre-filled markdown content string with a title.
 */

export const CARD_TEMPLATES = [
  {
    id: 'blank',
    name: 'Blank Note',
    icon: '\u270E',
    title: 'New Note',
    content: '',
  },
  {
    id: 'meeting',
    name: 'Meeting Notes',
    icon: '\u{1F4C5}',
    title: 'Meeting Notes',
    content: `## Date\n\n## Attendees\n- \n\n## Agenda\n1. \n\n## Discussion\n\n## Action Items\n- [ ] \n- [ ] \n`,
  },
  {
    id: 'decision',
    name: 'Decision',
    icon: '\u2696',
    title: 'Decision',
    content: `## Context\n\n## Options\n1. **Option A** — \n2. **Option B** — \n\n## Decision\n\n## Rationale\n`,
  },
  {
    id: 'research',
    name: 'Research',
    icon: '\u{1F50D}',
    title: 'Research',
    content: `## Topic\n\n## Sources\n- \n\n## Key Findings\n1. \n\n## Questions\n- \n`,
  },
  {
    id: 'task',
    name: 'Task List',
    icon: '\u2611',
    title: 'Tasks',
    content: `- [ ] \n- [ ] \n- [ ] \n`,
  },
  {
    id: 'pros_cons',
    name: 'Pros & Cons',
    icon: '\u2696',
    title: 'Pros & Cons',
    content: `## Pros\n- \n\n## Cons\n- \n\n## Verdict\n`,
  },
];

export default CARD_TEMPLATES;
