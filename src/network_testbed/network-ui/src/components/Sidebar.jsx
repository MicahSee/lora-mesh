import { Cpu, Activity, Shield, Link2, X } from 'lucide-react';

export default function Sidebar({ nodes, selectedId, onSelect, stats, topology, onToggleLink }) {
  const selectedNode = nodes.find(n => n.id === selectedId);
  const outgoingLinks = topology[selectedId] || [];
  const incomingLinks = Object.entries(topology)
    .filter(([sender, receivers]) => receivers.includes(selectedId))
    .map(([sender]) => sender);

  return (
    <aside className="w-72 border-r border-slate-800 bg-slate-900/30 flex flex-col">
      <div className="p-6">
        <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-4">System Stats</h3>
        <div className="grid grid-cols-1 gap-3">
          <StatCard icon={<Activity size={14}/>} label="Throughput" value={`${stats.throughput} kb/s`} />
          <StatCard icon={<Cpu size={14}/>} label="Nodes" value={stats.activeNodes} />
        </div>
      </div>

      {/* Link Management Panel - Shows when node is selected */}
      {selectedId && (
        <div className="px-4 pb-4">
          <div className="bg-blue-950/30 border border-blue-700/30 rounded-lg p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-xs font-bold text-blue-400 uppercase tracking-widest flex items-center gap-2">
                <Link2 size={12} /> Link Manager
              </h3>
              <button
                onClick={() => onSelect(null)}
                className="text-slate-500 hover:text-slate-300 transition-colors"
              >
                <X size={14} />
              </button>
            </div>

            <div className="text-sm font-bold text-white mb-3">{selectedId}</div>

            <div className="space-y-3">
              <div>
                <div className="text-[10px] text-slate-500 uppercase font-semibold mb-2">
                  Outgoing Links ({outgoingLinks.length})
                </div>
                <div className="space-y-1 max-h-24 overflow-y-auto">
                  {outgoingLinks.length > 0 ? (
                    outgoingLinks.map(target => (
                      <div
                        key={target}
                        className="flex items-center justify-between bg-slate-800/50 px-2 py-1.5 rounded text-xs"
                      >
                        <span className="text-green-400">→ {target}</span>
                        <button
                          onClick={() => onToggleLink(selectedId, target)}
                          className="text-red-400 hover:text-red-300 text-[10px]"
                        >
                          Remove
                        </button>
                      </div>
                    ))
                  ) : (
                    <div className="text-slate-600 text-[10px] italic">No outgoing links</div>
                  )}
                </div>
              </div>

              <div>
                <div className="text-[10px] text-slate-500 uppercase font-semibold mb-2">
                  Incoming Links ({incomingLinks.length})
                </div>
                <div className="space-y-1 max-h-24 overflow-y-auto">
                  {incomingLinks.length > 0 ? (
                    incomingLinks.map(source => (
                      <div
                        key={source}
                        className="flex items-center justify-between bg-slate-800/50 px-2 py-1.5 rounded text-xs"
                      >
                        <span className="text-blue-400">← {source}</span>
                        <button
                          onClick={() => onToggleLink(source, selectedId)}
                          className="text-red-400 hover:text-red-300 text-[10px]"
                        >
                          Remove
                        </button>
                      </div>
                    ))
                  ) : (
                    <div className="text-slate-600 text-[10px] italic">No incoming links</div>
                  )}
                </div>
              </div>
            </div>

            <div className="mt-3 pt-3 border-t border-slate-700/50 text-[10px] text-slate-500">
              Click another node to toggle link
            </div>
          </div>
        </div>
      )}

      <div className="flex-1 px-4 overflow-y-auto">
        <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-4 px-2">Active Transceivers</h3>
        {nodes.map(node => {
          const nodeOutgoing = (topology[node.id] || []).length;
          const nodeIncoming = Object.values(topology).filter(receivers => receivers.includes(node.id)).length;

          return (
            <div
              key={node.id}
              onClick={() => onSelect(node.id)}
              className={`p-3 rounded-lg mb-2 cursor-pointer transition-all border ${
                selectedId === node.id ? 'bg-blue-600/20 border-blue-500' : 'bg-slate-800/40 border-transparent hover:border-slate-700'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-bold text-sm">{node.id}</span>
                <div className="w-2 h-2 rounded-full bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]" />
              </div>
              <div className="flex items-center gap-3 mt-2">
                <div className="text-[9px] text-slate-500">
                  <span className="text-green-400">→{nodeOutgoing}</span>
                  {' '}
                  <span className="text-blue-400">←{nodeIncoming}</span>
                </div>
                <div className="text-[10px] text-slate-600 uppercase font-semibold">{node.config.encryption}</div>
              </div>
            </div>
          );
        })}
      </div>
    </aside>
  );
}

function StatCard({ icon, label, value }) {
  return (
    <div className="bg-slate-800/50 p-3 rounded-lg border border-slate-700/50">
      <div className="flex items-center gap-2 text-slate-400 text-[10px] uppercase font-bold mb-1">
        {icon} {label}
      </div>
      <div className="text-xl font-bold text-blue-400">{value}</div>
    </div>
  );
}