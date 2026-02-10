import { useState } from 'react';
import { useTags, useCreateTag, useAddCardTag, useRemoveCardTag } from '../../api/queries/tagQueries.js';
import './TagSelector.css';

export default function TagSelector({ boardId, cardId, cardTags = [] }) {
  const [showPicker, setShowPicker] = useState(false);
  const [newTagName, setNewTagName] = useState('');
  const { data: tagsData } = useTags();
  const createTag = useCreateTag();
  const addCardTag = useAddCardTag(boardId);
  const removeCardTag = useRemoveCardTag(boardId);

  const allTags = tagsData?.tags || [];
  const cardTagIds = new Set(cardTags.map((t) => t.id));

  const handleAddTag = (tagId) => {
    addCardTag.mutate({ cardId, tagId });
  };

  const handleRemoveTag = (tagId) => {
    removeCardTag.mutate({ cardId, tagId });
  };

  const handleCreateAndAdd = async () => {
    if (!newTagName.trim()) return;
    const result = await createTag.mutateAsync({ name: newTagName.trim() });
    if (result?.id) {
      addCardTag.mutate({ cardId, tagId: result.id });
    }
    setNewTagName('');
  };

  return (
    <div className="tag-selector">
      <div className="tag-selector__current">
        {cardTags.map((tag) => (
          <span
            key={tag.id}
            className="tag-selector__pill"
            style={{ borderLeftColor: tag.color }}
          >
            {tag.name}
            <button
              className="tag-selector__remove"
              onClick={() => handleRemoveTag(tag.id)}
              type="button"
            >
              &times;
            </button>
          </span>
        ))}
        <button
          className="tag-selector__add-btn"
          onClick={() => setShowPicker(!showPicker)}
          type="button"
        >
          + Tag
        </button>
      </div>

      {showPicker && (
        <div className="tag-selector__picker">
          <div className="tag-selector__list">
            {allTags
              .filter((t) => !cardTagIds.has(t.id))
              .map((tag) => (
                <button
                  key={tag.id}
                  className="tag-selector__option"
                  onClick={() => handleAddTag(tag.id)}
                  type="button"
                >
                  <span
                    className="tag-selector__dot"
                    style={{ backgroundColor: tag.color }}
                  />
                  {tag.name}
                </button>
              ))}
          </div>
          <div className="tag-selector__create">
            <input
              className="tag-selector__input"
              value={newTagName}
              onChange={(e) => setNewTagName(e.target.value)}
              placeholder="New tag name"
              onKeyDown={(e) => e.key === 'Enter' && handleCreateAndAdd()}
            />
            <button
              className="tag-selector__create-btn"
              onClick={handleCreateAndAdd}
              disabled={!newTagName.trim()}
              type="button"
            >
              Create
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
