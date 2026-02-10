import {
  TextEditor,
  NumberEditor,
  SelectEditor,
  MultiSelectEditor,
  DateEditor,
  CheckboxEditor,
  UrlEditor,
  EmailEditor,
  RelationEditor,
} from './editors/index.js';

const EDITORS = {
  text: TextEditor,
  number: NumberEditor,
  select: SelectEditor,
  multi_select: MultiSelectEditor,
  date: DateEditor,
  checkbox: CheckboxEditor,
  url: UrlEditor,
  email: EmailEditor,
  relation: RelationEditor,
};

const TYPE_LABELS = {
  text: 'Text',
  number: 'Number',
  select: 'Select',
  multi_select: 'Multi-select',
  date: 'Date',
  checkbox: 'Checkbox',
  url: 'URL',
  email: 'Email',
  relation: 'Relation',
};

export default function PropertyRow({ definition, value, onChange }) {
  const Editor = EDITORS[definition.property_type];

  if (!Editor) return null;

  return (
    <div className="property-panel__row">
      <div className="property-panel__row-label">
        <span className="property-panel__row-name">{definition.name}</span>
        <span className="property-panel__row-type">{TYPE_LABELS[definition.property_type]}</span>
      </div>
      <div className="property-panel__row-value">
        <Editor
          value={value}
          onChange={onChange}
          options={definition.options}
        />
      </div>
    </div>
  );
}
