import { useState } from 'react';
import { Filter, ArrowRight } from 'lucide-react';

export default function PacketMonitor({ traffic, topology }) {
  const [filter, setFilter] = useState('');

  const getPacketDestinations = (packet) => {
    const destinations = topology[packet.sender] || [];
    return destinations;
  };

  const filteredTraffic = traffic.filter(packet => {
    if (!filter) return true;
    return packet.sender.toLowerCase().includes(filter.toLowerCase()) ||
           packet.data.toLowerCase().includes(filter.toLowerCase());
  });

  return (
    <div className="h-full flex flex-col">
      {/* Filter Bar */}
      <div className="flex items-center gap-3 mb-3">
        <div className="flex-1 relative">
          <Filter size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder="Filter by sender or data..."
            className="w-full bg-slate-800/50 border border-slate-700 rounded-lg pl-9 pr-3 py-2 text-xs text-slate-300 placeholder-slate-600 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
          />
        </div>
        <div className="text-xs text-slate-500">
          {filteredTraffic.length} / {traffic.length} packets
        </div>
      </div>

      {/* Packet List */}
      <div className="flex-1 font-mono text-[11px] overflow-y-auto space-y-1">
        {filteredTraffic.length === 0 ? (
          <div className="text-slate-600 text-center py-8 text-xs">
            {traffic.length === 0 ? 'No traffic yet...' : 'No packets match filter'}
          </div>
        ) : (
          filteredTraffic.slice().reverse().map((packet) => {
            const destinations = getPacketDestinations(packet);
            return (
              <div
                key={`${packet.id}-${packet.timestamp}`}
                className="flex flex-col gap-1 border-l-2 border-blue-500/30 pl-3 py-2 hover:bg-white/5 transition-colors rounded-r"
              >
                <div className="flex items-center gap-4">
                  <span className="text-slate-500 text-[10px]">
                    [{new Date(packet.timestamp * 1000).toLocaleTimeString()}]
                  </span>
                  <span className="text-blue-400 font-bold uppercase">
                    {packet.sender}
                  </span>
                  {destinations.length > 0 && (
                    <div className="flex items-center gap-1 text-slate-500">
                      <ArrowRight size={12} />
                      <span className="text-green-400 text-[10px]">
                        [{destinations.join(', ')}]
                      </span>
                    </div>
                  )}
                  <span className="text-slate-600 ml-auto text-[9px]">#{packet.id}</span>
                </div>
                <div className="text-slate-300 pl-20">
                  <span className="text-slate-600">DATA:</span>{' '}
                  <span className="text-green-400">{packet.data}</span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}