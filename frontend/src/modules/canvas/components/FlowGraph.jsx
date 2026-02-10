import { useMemo } from 'react';
import {
  ReactFlow,
  Background,
  useNodesState,
  useEdgesState,
  ReactFlowProvider,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import '../styles/FlowGraph.css';

const STEP_TYPE_COLORS = {
  council_query: '#3498db',
  ai_transform: '#9b59b6',
  combine: '#2ecc71',
  human_review: '#f39c12',
  conditional: '#e74c3c',
};

const STEP_TYPE_LABELS = {
  council_query: 'Council',
  ai_transform: 'AI Transform',
  combine: 'Combine',
  human_review: 'Review',
  conditional: 'Condition',
};

function StepNode({ data }) {
  const color = STEP_TYPE_COLORS[data.stepType] || '#95a5a6';
  return (
    <div className="flow-graph-node" style={{ borderLeftColor: color }}>
      <div className="flow-graph-node__header">
        <span className="flow-graph-node__index">{data.index + 1}</span>
        <span className="flow-graph-node__name">{data.label}</span>
      </div>
      <div className="flow-graph-node__meta">
        <span className="flow-graph-node__type" style={{ backgroundColor: color }}>
          {STEP_TYPE_LABELS[data.stepType] || data.stepType}
        </span>
        {data.model && (
          <span className="flow-graph-node__model">{data.model.split('/').pop()}</span>
        )}
      </div>
      {data.status && data.status !== 'pending' && (
        <div className={`flow-graph-node__status flow-graph-node__status--${data.status}`}>
          {data.status}
        </div>
      )}
    </div>
  );
}

const nodeTypes = { stepNode: StepNode };

function FlowGraphInner({ steps = [], onStepClick }) {
  const { nodes, edges } = useMemo(() => {
    const n = steps.map((step, i) => ({
      id: `step-${i}`,
      type: 'stepNode',
      position: { x: 100, y: i * 120 },
      data: {
        label: step.name,
        stepType: step.step_type,
        model: step.model || (step.config || {}).model,
        status: step.status,
        index: i,
      },
    }));

    const e = [];
    for (let i = 0; i < steps.length - 1; i++) {
      const step = steps[i];
      if (step.step_type === 'conditional') {
        const config = step.config || {};
        const trueIdx = config.true_step_index;
        const falseIdx = config.false_step_index;
        if (trueIdx != null) {
          e.push({
            id: `e-${i}-true`,
            source: `step-${i}`,
            target: `step-${trueIdx}`,
            label: 'True',
            style: { stroke: '#2ecc71' },
            labelStyle: { fill: '#2ecc71', fontWeight: 600 },
          });
        }
        if (falseIdx != null) {
          e.push({
            id: `e-${i}-false`,
            source: `step-${i}`,
            target: `step-${falseIdx}`,
            label: 'False',
            style: { stroke: '#e74c3c' },
            labelStyle: { fill: '#e74c3c', fontWeight: 600 },
          });
        }
      } else {
        e.push({
          id: `e-${i}-${i + 1}`,
          source: `step-${i}`,
          target: `step-${i + 1}`,
        });
      }
    }

    return { nodes: n, edges: e };
  }, [steps]);

  const [flowNodes, , onNodesChange] = useNodesState(nodes);
  const [flowEdges, , onEdgesChange] = useEdgesState(edges);

  return (
    <div className="flow-graph" style={{ height: Math.max(300, steps.length * 120 + 60) }}>
      <ReactFlow
        nodes={flowNodes}
        edges={flowEdges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        onNodeClick={(_, node) => onStepClick?.(parseInt(node.id.replace('step-', '')))}
        fitView
        proOptions={{ hideAttribution: true }}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        panOnDrag={false}
        zoomOnScroll={false}
        zoomOnPinch={false}
        zoomOnDoubleClick={false}
      >
        <Background gap={20} size={1} color="#f0f0f0" />
      </ReactFlow>
    </div>
  );
}

export default function FlowGraph(props) {
  return (
    <ReactFlowProvider>
      <FlowGraphInner {...props} />
    </ReactFlowProvider>
  );
}
