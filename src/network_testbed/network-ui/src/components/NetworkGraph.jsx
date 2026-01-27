import { useCallback, useMemo, useEffect, useRef } from 'react';
import ReactFlow, {
  Background,
  Controls,
  useNodesState,
  useEdgesState,
  useReactFlow,
} from 'reactflow';
import 'reactflow/dist/style.css';
import CustomNode from './CustomNode';

const nodeTypes = {
  custom: CustomNode,
};

export default function NetworkGraph({ nodes, topology, onSelectNode, onToggleLink }) {
  const [rfNodes, setRfNodes, onNodesChange] = useNodesState([]);
  const [rfEdges, setRfEdges, onEdgesChange] = useEdgesState([]);
  const nodePositionsRef = useRef({});
  const edgeHandlesRef = useRef({}); // Store handle info: "source-target" -> { source, target }
  const reactFlowInstance = useReactFlow();

  // Load persisted handles on mount
  useEffect(() => {
    const persistedHandles = JSON.parse(localStorage.getItem('edgeHandles') || '{}');
    edgeHandlesRef.current = persistedHandles;
  }, []);

  // Update nodes only when the node list changes
  useEffect(() => {
    const currentNodeIds = new Set(nodes);
    const existingNodeIds = new Set(rfNodes.map(n => n.id));

    // Check if nodes have actually changed
    const nodesChanged =
      currentNodeIds.size !== existingNodeIds.size ||
      [...currentNodeIds].some(id => !existingNodeIds.has(id));

    if (!nodesChanged) {
      return; // No change in nodes, keep existing positions
    }

    // Generate positions for new nodes
    const newNodes = nodes.map((node, index) => {
      // If we already have a position for this node, use it
      if (nodePositionsRef.current[node]) {
        return {
          id: node,
          type: 'custom',
          data: { label: `Node: ${node}` },
          position: nodePositionsRef.current[node],
        };
      }

      // Otherwise, calculate circular layout position
      const angle = (index / nodes.length) * 2 * Math.PI;
      const radius = 300;
      const position = {
        x: 500 + radius * Math.cos(angle),
        y: 400 + radius * Math.sin(angle),
      };

      // Save the position
      nodePositionsRef.current[node] = position;

      return {
        id: node,
        type: 'custom',
        data: { label: `Node: ${node}` },
        position,
      };
    });

    setRfNodes(newNodes);

    // Fit view to show all nodes after a short delay
    setTimeout(() => {
      reactFlowInstance.fitView({ padding: 0.2, duration: 800 });
    }, 100);
  }, [nodes, rfNodes, setRfNodes, reactFlowInstance]);

  // Update positions in ref when nodes are dragged
  useEffect(() => {
    rfNodes.forEach(node => {
      nodePositionsRef.current[node.id] = node.position;
    });
  }, [rfNodes]);

  // Smart handle assignment based on node positions
  const assignHandles = useCallback((sourcePos, targetPos, pairIndex) => {
    // Calculate angle from source to target
    const dx = targetPos.x - sourcePos.x;
    const dy = targetPos.y - sourcePos.y;
    const angle = Math.atan2(dy, dx);

    // Available handle pairs (source, target) based on direction
    const handlePairs = [
      { source: 'right-source', target: 'left-target' },    // →
      { source: 'bottom-source', target: 'top-target' },    // ↓
      { source: 'left-source', target: 'right-target' },    // ←
      { source: 'top-source', target: 'bottom-target' },    // ↑
    ];

    // Pick base handle pair based on angle
    let baseIndex;
    if (angle > -Math.PI/4 && angle <= Math.PI/4) baseIndex = 0;        // right
    else if (angle > Math.PI/4 && angle <= 3*Math.PI/4) baseIndex = 1;  // bottom
    else if (angle > 3*Math.PI/4 || angle <= -3*Math.PI/4) baseIndex = 2; // left
    else baseIndex = 3;                                                  // top

    // Rotate through handles if multiple connections
    const selectedIndex = (baseIndex + pairIndex) % handlePairs.length;
    return handlePairs[selectedIndex];
  }, []);

  // Convert topology to React Flow edges with smart handle assignment
  const flowEdges = useMemo(() => {
    const edges = [];

    // Check if we have node positions yet
    const hasPositions = Object.keys(nodePositionsRef.current).length > 0;

    // Count connections between each pair for smart distribution
    const pairCounts = {};
    Object.entries(topology).forEach(([source, targets]) => {
      targets.forEach(target => {
        const pairKey = [source, target].sort().join('-');
        pairCounts[pairKey] = (pairCounts[pairKey] || 0) + 1;
      });
    });

    // Track how many edges we've seen for each pair
    const pairIndices = {};

    Object.entries(topology).forEach(([source, targets]) => {
      targets.forEach(target => {
        const edgeKey = `${source}-${target}`;
        const pairKey = [source, target].sort().join('-');

        // Get current index for this pair
        const pairIndex = pairIndices[pairKey] || 0;
        pairIndices[pairKey] = pairIndex + 1;

        let handleInfo = edgeHandlesRef.current[edgeKey];

        // If no handle info exists and we have positions, assign smart handles
        if (!handleInfo && hasPositions && nodePositionsRef.current[source] && nodePositionsRef.current[target]) {
          handleInfo = assignHandles(
            nodePositionsRef.current[source],
            nodePositionsRef.current[target],
            pairIndex
          );
          edgeHandlesRef.current[edgeKey] = handleInfo;
          // Persist immediately
          localStorage.setItem('edgeHandles', JSON.stringify(edgeHandlesRef.current));
        }

        edges.push({
          id: edgeKey,
          source,
          target,
          sourceHandle: handleInfo?.source,
          targetHandle: handleInfo?.target,
          animated: true,
        });
      });
    });

    return edges;
  }, [topology, assignHandles, rfNodes]); // Add rfNodes to dependencies

  // Update edges when topology changes
  useEffect(() => {
    setRfEdges(flowEdges);
  }, [flowEdges, setRfEdges]);

  const onNodeClick = useCallback((_event, node) => {
    onSelectNode(node.id);
  }, [onSelectNode]);

  const onConnect = useCallback((params) => {
    // Store handle information for this connection
    const edgeKey = `${params.source}-${params.target}`;
    edgeHandlesRef.current[edgeKey] = {
      source: params.sourceHandle,
      target: params.targetHandle,
    };

    // Persist to localStorage
    localStorage.setItem('edgeHandles', JSON.stringify(edgeHandlesRef.current));

    onToggleLink(params.source, params.target);
  }, [onToggleLink]);

  const onEdgeClick = useCallback((_event, edge) => {
    // Remove handle information when edge is deleted
    const edgeKey = `${edge.source}-${edge.target}`;
    delete edgeHandlesRef.current[edgeKey];

    // Persist to localStorage
    localStorage.setItem('edgeHandles', JSON.stringify(edgeHandlesRef.current));

    onToggleLink(edge.source, edge.target);
  }, [onToggleLink]);

  return (
    <div className="w-full h-full">
      <ReactFlow
        nodes={rfNodes}
        edges={rfEdges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        onConnect={onConnect}
        onEdgeClick={onEdgeClick}
        nodeTypes={nodeTypes}
        fitView
      >
        <Background />
        <Controls />
      </ReactFlow>
    </div>
  );
}
