import { useMutation } from '@tanstack/react-query';
import { exportBoard, shareBoard } from '../export';

export function useExportBoard() {
  return useMutation({
    mutationFn: ({ boardId, format }) => exportBoard(boardId, format),
    onSuccess: (blob, { boardId, format }) => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `board-export.${format === 'md' ? 'md' : format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    },
  });
}

export function useShareBoard() {
  return useMutation({
    mutationFn: (boardId) => shareBoard(boardId),
  });
}
