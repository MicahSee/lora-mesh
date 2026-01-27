import React from 'react';
import { Radio, ArrowRight, X } from 'lucide-react';

export default function NodeList({ nodes, topology, selectedNode, onSelectNode, onToggleLink }) {
  const getOutgoingLinks = (nodeId) => topology[nodeId] || [];
  const getIncomingLinks = (nodeId) => {
    return Object.entries(topology)
      .filter(([_, targets]) => targets.includes(nodeId))
      .map(([source]) => source);
  };

  return (
    <div className="flex-1 overflow-y-auto p-4">
      <h2 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-3">Nodes</h2>

      {nodes.length === 0 && (
        <div className="text-slate-600 text-sm italic">No nodes connected</div>
      )}

      {nodes.map(node => {
        const isSelected = selectedNode === node;
        const outgoing = getOutgoingLinks(node);
        const incoming = getIncomingLinks(node);

        return (
          <div key={node} className="mb-3">
            <div
              onClick={() => onSelectNode(node)}
              className={`p-3 rounded-lg cursor-pointer transition-all ${
                isSelected
                  ? 'bg-blue-600/20 border-2 border-blue-500'
                  : 'bg-slate-800 border-2 border-transparent hover:border-slate-600'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Radio size={16} className="text-green-400" />
                  <span className="font-bold">{node}</span>
                </div>
                <div className="flex gap-2 text-xs">
                  <span className="text-green-400">→{outgoing.length}</span>
                  <span className="text-blue-400">←{incoming.length}</span>
                </div>
              </div>
            </div>

            {isSelected && (outgoing.length > 0 || incoming.length > 0) && (
              <div className="mt-2 ml-4 space-y-2">
                {outgoing.length > 0 && (
                  <div>
                    <div className="text-xs text-slate-500 mb-1">Outgoing:</div>
                    {outgoing.map(target => (
                      <div
                        key={target}
                        className="flex items-center justify-between bg-slate-800/50 px-2 py-1 rounded text-xs mb-1"
                      >
                        <div className="flex items-center gap-1">
                          <ArrowRight size={12} className="text-green-400" />
                          <span>{target}</span>
                        </div>
                        <button
                          onClick={() => onToggleLink(node, target)}
                          className="text-red-400 hover:text-red-300"
                        >
                          <X size={14} />
                        </button>
                      </div>
                    ))}
                  </div>
                )}

                {incoming.length > 0 && (
                  <div>
                    <div className="text-xs text-slate-500 mb-1">Incoming:</div>
                    {incoming.map(source => (
                      <div
                        key={source}
                        className="flex items-center justify-between bg-slate-800/50 px-2 py-1 rounded text-xs mb-1"
                      >
                        <div className="flex items-center gap-1">
                          <ArrowRight size={12} className="text-blue-400 rotate-180" />
                          <span>{source}</span>
                        </div>
                        <button
                          onClick={() => onToggleLink(source, node)}
                          className="text-red-400 hover:text-red-300"
                        >
                          <X size={14} />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
