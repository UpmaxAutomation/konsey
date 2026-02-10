import { memo, useState } from 'react';
import SafeMarkdown from '../../../shared/components/SafeMarkdown';
import CopyButton from '../../../shared/components/CopyButton';
import BoardPicker from '../../canvas/components/BoardPicker';
import { createCardFromMessage } from '../../../api/boards';
import '../styles/Stage3.css';

const Stage3 = memo(function Stage3({ finalResponse, conversationId }) {
  const [showBoardPicker, setShowBoardPicker] = useState(false);

  if (!finalResponse) {
    return null;
  }

  const handlePinToBoard = async (boardId) => {
    try {
      await createCardFromMessage(boardId, {
        conversation_id: conversationId,
        card_type: 'council_synthesis',
        title: 'Council Synthesis',
        content: finalResponse.response,
        extra: { model: finalResponse.model },
      });
      setShowBoardPicker(false);
    } catch (err) {
      console.error('Failed to pin to board:', err);
    }
  };

  return (
    <div className="stage stage3">
      <div className="stage-header">
        <h3 className="stage-title">Stage 3: Final Council Answer</h3>
        <div className="stage-header-actions">
          <div className="pin-to-board-wrapper">
            <button
              className="pin-to-board-btn"
              onClick={() => setShowBoardPicker(!showBoardPicker)}
              title="Pin to board"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="3" y="3" width="18" height="18" rx="2" />
                <path d="M3 9h18M9 21V9" />
              </svg>
            </button>
            {showBoardPicker && (
              <BoardPicker
                onSelect={(boardId) => handlePinToBoard(boardId)}
                onClose={() => setShowBoardPicker(false)}
              />
            )}
          </div>
          <CopyButton text={finalResponse.response} />
        </div>
      </div>
      <div className="final-response">
        <div className="chairman-label">
          Chairman: {finalResponse.model.split('/')[1] || finalResponse.model}
        </div>
        <div className="final-text markdown-content">
          <SafeMarkdown>{finalResponse.response}</SafeMarkdown>
        </div>
      </div>
    </div>
  );
});

export default Stage3;
