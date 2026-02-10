export { default as TextEditor } from './TextEditor.jsx';
export { default as NumberEditor } from './NumberEditor.jsx';
export { default as SelectEditor } from './SelectEditor.jsx';
export { default as MultiSelectEditor } from './MultiSelectEditor.jsx';
export { default as DateEditor } from './DateEditor.jsx';
export { default as CheckboxEditor } from './CheckboxEditor.jsx';
export { default as UrlEditor } from './UrlEditor.jsx';
export { default as EmailEditor } from './EmailEditor.jsx';
export { default as RelationEditor } from './RelationEditor.jsx';

const EDITOR_MAP = {
  text: 'TextEditor',
  number: 'NumberEditor',
  select: 'SelectEditor',
  multi_select: 'MultiSelectEditor',
  date: 'DateEditor',
  checkbox: 'CheckboxEditor',
  url: 'UrlEditor',
  email: 'EmailEditor',
  relation: 'RelationEditor',
};

export { EDITOR_MAP };
