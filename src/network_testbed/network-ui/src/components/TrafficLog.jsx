import { useState, useMemo } from 'react';
import { Activity, ArrowRight, ChevronDown, ChevronUp } from 'lucide-react';

export default function TrafficLog({ traffic }) {
  const [isCollapsed, setIsCollapsed] = useState(false);

  // Extract extra columns from traffic data (excluding standard fields)
  const { parsedTraffic, extraColumns } = useMemo(() => {
    const columnSet = new Set();
    const standardFields = new Set(['id', 'sender', 'data', 'timestamp', 'receivers']);

    traffic.forEach((packet) => {
      // Collect all keys that are not standard fields
      Object.keys(packet).forEach(key => {
        if (!standardFields.has(key)) {
          columnSet.add(key);
        }
      });
    });

    return {
      parsedTraffic: traffic,
      extraColumns: Array.from(columnSet)
    };
  }, [traffic]);

  return (
    <div className="border-t border-slate-800 bg-slate-900 flex flex-col">
      {/* Header - Always Visible */}
      <button
        onClick={() => setIsCollapsed(!isCollapsed)}
        className="flex items-center justify-between p-3 hover:bg-slate-800/50 transition-colors"
      >
        <div className="flex items-center gap-2 text-sm font-bold text-slate-400 uppercase tracking-wider">
          <Activity size={14} />
          <span>Traffic Log</span>
          <span className="text-xs text-slate-600 normal-case">({traffic.length})</span>
        </div>
        {isCollapsed ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
      </button>

      {/* Content - Collapsible */}
      {!isCollapsed && (
        <div className="flex-1 overflow-hidden flex flex-col" style={{ maxHeight: '300px' }}>
          <div className="overflow-y-auto overflow-x-auto">
            {traffic.length === 0 ? (
              <div className="text-slate-600 text-xs italic p-3">No traffic yet</div>
            ) : (
              <table className="w-full text-xs">
                <thead className="sticky top-0 bg-slate-800 text-slate-400 border-b border-slate-700">
                  <tr>
                    <th className="text-left p-2 font-semibold">#</th>
                    <th className="text-left p-2 font-semibold">Direction</th>
                    <th className="text-left p-2 font-semibold">Recipients</th>
                    <th className="text-left p-2 font-semibold">Raw Data</th>
                    {extraColumns.map(col => (
                      <th key={col} className="text-left p-2 font-semibold capitalize">
                        {col.replace(/_/g, ' ')}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {parsedTraffic.slice().reverse().map((packet, idx) => (
                    <tr
                      key={`${packet.id}-${packet.timestamp || idx}`}
                      className="border-b border-slate-800/50 hover:bg-slate-800/30"
                    >
                      <td className="p-2 text-slate-500">#{packet.id}</td>
                      <td className="p-2">
                        <div className="flex items-center gap-1">
                          <span className="font-bold text-blue-400">{packet.sender}</span>
                          <ArrowRight size={10} className="text-slate-600" />
                        </div>
                      </td>
                      <td className="p-2 text-green-400">
                        {packet.receivers && packet.receivers.length > 0
                          ? packet.receivers.join(', ')
                          : 'none'}
                      </td>
                      <td className="p-2 text-slate-300 max-w-xs truncate" title={packet.data}>
                        {packet.data}
                      </td>
                      {extraColumns.map(col => (
                        <td key={col} className="p-2 text-slate-300">
                          {packet[col] !== undefined
                            ? String(packet[col])
                            : '-'}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
