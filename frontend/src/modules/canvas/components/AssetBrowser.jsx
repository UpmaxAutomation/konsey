import { useState } from 'react';
import { useProjectAssets, useDeleteAsset } from '../../../api/queries/assetQueries';
import './styles/AssetBrowser.css';

const ASSET_TYPES = [
  { value: '', label: 'All' },
  { value: 'image', label: 'Images' },
  { value: 'document', label: 'Documents' },
  { value: 'other', label: 'Other' },
];

export default function AssetBrowser({ projectId, onClose, onPlaceOnBoard }) {
  const [typeFilter, setTypeFilter] = useState('');
  const [search, setSearch] = useState('');
  const [selectedAsset, setSelectedAsset] = useState(null);

  const { data: assets = [], isLoading } = useProjectAssets(projectId, {
    type: typeFilter || undefined,
    search: search || undefined,
  });
  const deleteMutation = useDeleteAsset();

  const handleDelete = async (id, e) => {
    e.stopPropagation();
    if (confirm('Delete this asset?')) {
      deleteMutation.mutate(id);
    }
  };

  const handlePlaceOnBoard = (asset) => {
    if (onPlaceOnBoard) {
      onPlaceOnBoard(asset);
    }
    onClose?.();
  };

  return (
    <div className="asset-browser-overlay" onClick={onClose}>
      <div className="asset-browser" onClick={e => e.stopPropagation()}>
        <div className="asset-browser-header">
          <h2>Asset Library</h2>
          <button className="asset-browser-close" onClick={onClose}>x</button>
        </div>

        <div className="asset-browser-filters">
          <input
            type="text"
            placeholder="Search assets..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="asset-search-input"
          />
          <div className="asset-type-filters">
            {ASSET_TYPES.map(t => (
              <button
                key={t.value}
                className={`asset-type-btn ${typeFilter === t.value ? 'active' : ''}`}
                onClick={() => setTypeFilter(t.value)}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>

        <div className="asset-browser-grid">
          {isLoading ? (
            <div className="asset-loading">Loading assets...</div>
          ) : assets.length === 0 ? (
            <div className="asset-empty">No assets found. Generate images or export content to build your library.</div>
          ) : (
            assets.map(asset => (
              <div
                key={asset.id}
                className={`asset-card ${selectedAsset?.id === asset.id ? 'selected' : ''}`}
                onClick={() => setSelectedAsset(asset)}
              >
                <div className="asset-thumbnail">
                  {asset.asset_type === 'image' && asset.url ? (
                    <img src={asset.url} alt={asset.name} />
                  ) : (
                    <div className="asset-icon">
                      {asset.asset_type === 'document' ? 'DOC' : asset.asset_type === 'video' ? 'VID' : 'FILE'}
                    </div>
                  )}
                </div>
                <div className="asset-info">
                  <span className="asset-name" title={asset.name}>{asset.name}</span>
                  <span className="asset-meta">{asset.asset_type} - {asset.source}</span>
                </div>
                <div className="asset-actions">
                  {onPlaceOnBoard && asset.asset_type === 'image' && (
                    <button
                      className="asset-action-btn place"
                      onClick={(e) => { e.stopPropagation(); handlePlaceOnBoard(asset); }}
                      title="Place on Board"
                    >
                      +
                    </button>
                  )}
                  <button
                    className="asset-action-btn delete"
                    onClick={(e) => handleDelete(asset.id, e)}
                    title="Delete"
                  >
                    x
                  </button>
                </div>
              </div>
            ))
          )}
        </div>

        {selectedAsset && (
          <div className="asset-preview-panel">
            <h3>{selectedAsset.name}</h3>
            {selectedAsset.asset_type === 'image' && selectedAsset.url && (
              <img src={selectedAsset.url} alt={selectedAsset.name} className="asset-preview-img" />
            )}
            <div className="asset-preview-details">
              <p><strong>Type:</strong> {selectedAsset.asset_type}</p>
              <p><strong>Source:</strong> {selectedAsset.source}</p>
              {selectedAsset.file_size && <p><strong>Size:</strong> {(selectedAsset.file_size / 1024).toFixed(1)} KB</p>}
              {selectedAsset.tags?.length > 0 && (
                <p><strong>Tags:</strong> {selectedAsset.tags.join(', ')}</p>
              )}
            </div>
            {onPlaceOnBoard && selectedAsset.asset_type === 'image' && (
              <button className="asset-place-btn" onClick={() => handlePlaceOnBoard(selectedAsset)}>
                Place on Board
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
