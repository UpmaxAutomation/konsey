import { createContext, useContext } from 'react';

const BoardContext = createContext(null);

export function useBoardActions() {
  return useContext(BoardContext);
}

export default BoardContext;
