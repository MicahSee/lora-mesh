import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { ReactFlowProvider } from 'reactflow';
import NetworkGraph from './components/NetworkGraph';
import NodeList from './components/NodeList';
import TrafficLog from './components/TrafficLog';

// Use relative URLs when served from FastAPI, or localhost for dev
const API_BASE = import.meta.env.DEV ? 'http://localhost:8000' : '';
const WS_URL = import.meta.env.DEV ? 'ws://localhost:8000/ws' : `ws://${window.location.host}/ws`;

export default function App() {
  const [nodes, setNodes] = useState([]);
  const [topology, setTopology] = useState({});
  const [traffic, setTraffic] = useState([]);
  const [selectedNode, setSelectedNode] = useState(null);
  const seenMessageIds = useRef(new Set());

  useEffect(() => {
    let isCleanedUp = false;
    const ws = new WebSocket(WS_URL);

    ws.onopen = () => {
      console.log('WebSocket connected');
    };

    ws.onmessage = (event) => {
      // Ignore messages if component has been cleaned up
      if (isCleanedUp) return;

      const message = JSON.parse(event.data);

      switch (message.type) {
        case 'initial_state':
          console.log('Received initial_state. Traffic count:', message.data.traffic.length);
          setNodes(message.data.nodes);
          setTopology(message.data.topology);
          setTraffic(message.data.traffic);

          // Populate seenMessageIds with IDs from initial state
          seenMessageIds.current.clear();
          message.data.traffic.forEach(packet => {
            seenMessageIds.current.add(packet.id);
          });
          break;

        case 'nodes_update':
          setNodes(message.data.nodes);
          setTopology(message.data.topology);
          break;

        case 'topology_update':
          setTopology(message.data.topology);
          break;

        case 'traffic_update':
          // Synchronously check if we've seen this message ID before
          if (seenMessageIds.current.has(message.data.id)) {
            console.warn('Duplicate traffic_update detected! Message ID:', message.data.id, 'Data:', message.data.data);
            break;
          }

          // Mark this message ID as seen
          seenMessageIds.current.add(message.data.id);

          console.log('Adding traffic message:', message.data.id, message.data.sender, '->', message.data.receivers, ':', message.data.data);

          setTraffic(prev => {
            const newTraffic = [...prev, message.data];
            return newTraffic.slice(-100); // Keep last 100
          });
          break;

        default:
          console.warn('Unknown message type:', message.type);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
    };

    return () => {
      console.log('Cleaning up WebSocket connection');
      isCleanedUp = true;
      ws.close();
    };
  }, []);

  const toggleLink = async (from, to) => {
    try {
      await axios.post(`${API_BASE}/toggle-link`, { sender: from, receiver: to });
      // WebSocket will automatically receive the topology update
    } catch (err) {
      console.error("Error toggling link:", err);
    }
  };

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100">
      {/* Left Sidebar */}
      <div className="w-80 border-r border-slate-800 bg-slate-900 flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-slate-800 flex-shrink-0">
          <h1 className="text-xl text-white">Mesh Network Testbed</h1>
          <p className="text-xs text-slate-500 mt-1">{nodes.length} nodes online</p>
        </div>

        {/* Node List */}
        <div className="flex-1 overflow-y-auto min-h-0">
          <NodeList
            nodes={nodes}
            topology={topology}
            selectedNode={selectedNode}
            onSelectNode={setSelectedNode}
            onToggleLink={toggleLink}
          />
        </div>
      </div>

      {/* Right Side: Graph + Traffic Log */}
      <div className="flex-1 flex flex-col">
        {/* Graph Area */}
        <div className="flex-1 relative">
          <ReactFlowProvider>
            <NetworkGraph
              nodes={nodes}
              topology={topology}
              selectedNode={selectedNode}
              onSelectNode={setSelectedNode}
              onToggleLink={toggleLink}
            />
          </ReactFlowProvider>
        </div>

        {/* Traffic Log at Bottom */}
        <TrafficLog traffic={traffic} />
      </div>
    </div>
  );
}
