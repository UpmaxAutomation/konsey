import TableView from './TableView.jsx';
import KanbanView from './KanbanView.jsx';

/**
 * Switches between Canvas (ReactFlow), Table, and Kanban views.
 * When activeView is 'canvas', this component returns null and the parent
 * renders the ReactFlow canvas directly.
 */
export default function ViewContainer({
  activeView,
  cards,
  propertyDefinitions,
  propertyValuesByCard,
  onCardSelect,
  onPropertyChange,
  boardId,
}) {
  if (activeView === 'table') {
    return (
      <TableView
        cards={cards}
        propertyDefinitions={propertyDefinitions}
        propertyValuesByCard={propertyValuesByCard}
        onCardSelect={onCardSelect}
        onPropertyChange={onPropertyChange}
        boardId={boardId}
      />
    );
  }

  if (activeView === 'kanban') {
    return (
      <KanbanView
        cards={cards}
        propertyDefinitions={propertyDefinitions}
        propertyValuesByCard={propertyValuesByCard}
        onCardSelect={onCardSelect}
        onPropertyChange={onPropertyChange}
        boardId={boardId}
      />
    );
  }

  // activeView === 'canvas' -> parent handles ReactFlow
  return null;
}
