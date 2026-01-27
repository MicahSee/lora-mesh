import React, { useMemo, useRef, useState, useEffect } from 'react';
import ForceGraph2D from 'react-force-graph-2d';

export default function NetworkMap({ nodes, topology, selectedId, onNodeClick, onToggleLink }) {
  const graphRef = useRef();
  const [hoveredNode, setHoveredNode] = useState(null);
  const nodePositions = useRef({});
  const lastDataHash = useRef('');
  const lastGraphData = useRef(null);

  const data = useMemo(() => {
    // Create a hash of the current state
    const nodeIds = nodes.map(n => n.id).sort().join(',');
    const topologyHash = JSON.stringify(topology);
    const currentHash = `${nodeIds}|${topologyHash}`;

    // If nothing changed, return existing data to prevent graph update
    if (currentHash === lastDataHash.current && lastGraphData.current) {
      return lastGraphData.current;
    }

    lastDataHash.current = currentHash;

    const links = [];
    Object.entries(topology).forEach(([sender, receivers]) => {
      receivers.forEach(receiver => {
        links.push({
          source: sender,
          target: receiver,
          id: `${sender}->${receiver}`
        });
      });
    });

    // Preserve existing positions and fixed state
    const graphNodes = nodes.map(n => {
      const existing = nodePositions.current[n.id];
      if (existing) {
        return {
          ...n,
          x: existing.x,
          y: existing.y,
          fx: existing.fx,
          fy: existing.fy,
          vx: 0,
          vy: 0
        };
      }
      return { ...n };
    });

    const newData = { nodes: graphNodes, links };
    lastGraphData.current = newData;
    return newData;
  }, [nodes, topology]);

  const handleNodeClick = (node) => {
    if (selectedId && selectedId !== node.id) {
      onToggleLink(selectedId, node.id);
    } else {
      onNodeClick(node.id);
    }
  };

  const handleNodeDrag = (node) => {
    // Update position cache while dragging
    nodePositions.current[node.id] = {
      x: node.x,
      y: node.y,
      fx: node.x,
      fy: node.y
    };
  };

  const handleNodeDragEnd = (node) => {
    // Fix the node in place permanently
    node.fx = node.x;
    node.fy = node.y;
    nodePositions.current[node.id] = {
      x: node.x,
      y: node.y,
      fx: node.x,
      fy: node.y
    };
  };

  const isConnected = (nodeId) => {
    if (!selectedId) return false;
    const hasOutgoing = topology[selectedId]?.includes(nodeId);
    const hasIncoming = topology[nodeId]?.includes(selectedId);
    return hasOutgoing || hasIncoming;
  };

  return (
    <div className="relative w-full h-full">
      <ForceGraph2D
        ref={graphRef}
        graphData={data}
        onNodeClick={handleNodeClick}
        onNodeHover={setHoveredNode}
        onNodeDrag={handleNodeDrag}
        onNodeDragEnd={handleNodeDragEnd}
        nodeLabel={(node) => `${node.id} (Click to ${selectedId ? 'toggle link' : 'select'})`}
        backgroundColor="rgba(0,0,0,0)"
        enableNodeDrag={true}
        nodeColor={(n) => {
          if (n.id === selectedId) return '#3b82f6';
          if (selectedId && isConnected(n.id)) return '#10b981';
          return '#64748b';
        }}
        linkColor={(link) => {
          if (selectedId === link.source.id || selectedId === link.target.id) {
            return '#3b82f6';
          }
          return '#334155';
        }}
        linkWidth={(link) => {
          if (selectedId === link.source.id || selectedId === link.target.id) {
            return 2;
          }
          return 1;
        }}
        linkDirectionalArrowLength={6}
        linkDirectionalArrowRelPos={1}
        linkDirectionalParticles={2}
        linkDirectionalParticleWidth={(link) => {
          if (selectedId === link.source.id || selectedId === link.target.id) {
            return 2;
          }
          return 0;
        }}
        linkCurvature={0.2}
        nodeCanvasObject={(node, ctx, globalScale) => {
          const label = node.id;
          const fontSize = 13 / globalScale;
          const nodeRadius = 6;
          const isSelected = node.id === selectedId;
          const isHovered = node.id === hoveredNode?.id;
          const isLinked = selectedId && isConnected(node.id);

          // Draw glow effect for selected/hovered nodes
          if (isSelected || isHovered) {
            const gradient = ctx.createRadialGradient(node.x, node.y, 0, node.x, node.y, nodeRadius * 3);
            gradient.addColorStop(0, isSelected ? 'rgba(59, 130, 246, 0.4)' : 'rgba(100, 116, 139, 0.3)');
            gradient.addColorStop(1, 'rgba(0, 0, 0, 0)');
            ctx.fillStyle = gradient;
            ctx.beginPath();
            ctx.arc(node.x, node.y, nodeRadius * 3, 0, 2 * Math.PI, false);
            ctx.fill();
          }

          // Draw node circle
          ctx.fillStyle = isSelected ? '#3b82f6' : isLinked ? '#10b981' : '#64748b';
          ctx.beginPath();
          ctx.arc(node.x, node.y, nodeRadius, 0, 2 * Math.PI, false);
          ctx.fill();

          // Draw border
          if (isSelected || isHovered) {
            ctx.strokeStyle = isSelected ? '#60a5fa' : '#94a3b8';
            ctx.lineWidth = 2.5 / globalScale;
            ctx.stroke();
          }

          // Draw label
          ctx.font = `bold ${fontSize}px Inter, sans-serif`;
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';

          // Label background
          const textWidth = ctx.measureText(label).width;
          ctx.fillStyle = 'rgba(15, 23, 42, 0.9)';
          ctx.fillRect(node.x - textWidth / 2 - 4, node.y + 12, textWidth + 8, fontSize + 4);

          // Label text
          ctx.fillStyle = isSelected ? '#60a5fa' : isLinked ? '#34d399' : '#e2e8f0';
          ctx.fillText(label, node.x, node.y + 14 + fontSize / 2);
        }}
        d3AlphaDecay={0.0228}
        d3VelocityDecay={0.4}
        cooldownTicks={200}
        onEngineStop={() => {
          // Fix all nodes in place when simulation stops
          if (graphRef.current) {
            const graphData = graphRef.current.graphData();
            graphData.nodes.forEach(node => {
              node.fx = node.x;
              node.fy = node.y;
              nodePositions.current[node.id] = {
                x: node.x,
                y: node.y,
                fx: node.x,
                fy: node.y
              };
            });
            graphRef.current.zoomToFit(400, 100);
          }
        }}
        linkDistance={150}
        chargeStrength={-400}
        warmupTicks={100}
      />

      {/* Legend */}
      <div className="absolute top-4 right-4 bg-slate-900/90 backdrop-blur-md border border-slate-700 rounded-lg p-4 text-xs space-y-2">
        <div className="font-bold text-slate-300 mb-3">Network Legend</div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-blue-500"></div>
          <span className="text-slate-400">Selected Node</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-green-500"></div>
          <span className="text-slate-400">Connected Node</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-slate-500"></div>
          <span className="text-slate-400">Inactive Node</span>
        </div>
        <div className="border-t border-slate-700 pt-2 mt-3 text-slate-500 text-[10px]">
          Click node to select<br/>
          Click another to toggle link
        </div>
      </div>
    </div>
  );
}