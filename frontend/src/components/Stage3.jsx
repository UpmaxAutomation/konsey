import { memo } from 'react';
import SafeMarkdown from './SafeMarkdown';
import CopyButton from './CopyButton';
import './Stage3.css';

const Stage3 = memo(function Stage3({ finalResponse }) {
  if (!finalResponse) {
    return null;
  }

  return (
    <div className="stage stage3">
      <div className="stage-header">
        <h3 className="stage-title">Stage 3: Final Council Answer</h3>
        <CopyButton text={finalResponse.response} />
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
