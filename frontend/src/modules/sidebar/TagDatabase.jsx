import { useState, useCallback } from 'react';
import { useTags, useCreateTag, useDeleteTag } from '../../api/queries/tagQueries';
import './styles/TagDatabase.css';

const TAG_COLORS = [
  '#ef4444', '#f59e0b', '#22c55e', '#3b82f6', '#8b5cf6',
  '#ec4899', '#06b6d4', '#64748b', '#f97316', '#14b8a6',
];

export default function TagDatabase() {
  const { data: tagsData, isLoading } = useTags();
  const createTag = useCreateTag();
  const deleteTag = useDeleteTag();
  const [newTagName, setNewTagName] = useState('');
  const [newTagColor, setNewTagColor] = useState(TAG_COLORS[0]);
  const [search, setSearch] = useState('');
  const [expandedTag, setExpandedTag] = useState(null);

  const tags = tagsData?.tags || [];

  const filteredTags = search
    ? tags.filter(t => t.name.toLowerCase().includes(search.toLowerCase()))
    : tags;

  // Group by collection
  const grouped = {};
  for (const tag of filteredTags) {
    const group = tag.collection || 'General';
    if (!grouped[group]) grouped[group] = [];
    grouped[group].push(tag);
  }

  const handleCreate = useCallback(async () => {
    const name = newTagName.trim();
    if (!name) return;
    try {
      await createTag.mutateAsync({ name, color: newTagColor });
      setNewTagName('');
    } catch (err) {
      console.error('Failed to create tag:', err);
    }
  }, [newTagName, newTagColor, createTag]);

  const handleDelete = useCallback(async (tagId) => {
    try {
      await deleteTag.mutateAsync(tagId);
    } catch (err) {
      console.error('Failed to delete tag:', err);
    }
  }, [deleteTag]);

  return (
    <div className="tag-database">
      <div className="tag-database__header">
        <h4 className="tag-database__title">Tags</h4>
        <span className="tag-database__count">{tags.length}</span>
      </div>

      <div className="tag-database__search">
        <input
          className="tag-database__search-input"
          placeholder="Search tags..."
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
      </div>

      <div className="tag-database__create">
        <input
          className="tag-database__new-input"
          placeholder="New tag name..."
          value={newTagName}
          onChange={e => setNewTagName(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleCreate()}
        />
        <div className="tag-database__colors">
          {TAG_COLORS.map(c => (
            <button
              key={c}
              className={`tag-database__color-btn${newTagColor === c ? ' tag-database__color-btn--active' : ''}`}
              style={{ background: c }}
              onClick={() => setNewTagColor(c)}
              aria-label={`Select color ${c}`}
            />
          ))}
        </div>
        <button
          className="tag-database__create-btn"
          onClick={handleCreate}
          disabled={!newTagName.trim() || createTag.isPending}
        >
          Add
        </button>
      </div>

      <div className="tag-database__list">
        {isLoading && <div className="tag-database__loading">Loading tags...</div>}
        {!isLoading && Object.entries(grouped).map(([group, groupTags]) => (
          <div key={group} className="tag-database__group">
            <div className="tag-database__group-name">{group}</div>
            {groupTags.map(tag => (
              <div key={tag.id} className="tag-database__item" onClick={() => setExpandedTag(expandedTag === tag.id ? null : tag.id)}>
                <span className="tag-database__dot" style={{ background: tag.color }} />
                <span className="tag-database__name">{tag.name}</span>
                <span className="tag-database__card-count">{tag.card_count || 0}</span>
                <button
                  className="tag-database__delete-btn"
                  onClick={(e) => { e.stopPropagation(); handleDelete(tag.id); }}
                  title="Delete tag"
                >
                  x
                </button>
              </div>
            ))}
          </div>
        ))}
        {!isLoading && filteredTags.length === 0 && (
          <div className="tag-database__empty">No tags yet. Create one above.</div>
        )}
      </div>
    </div>
  );
}
