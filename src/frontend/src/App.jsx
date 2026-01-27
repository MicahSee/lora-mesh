import React, { useState, useEffect, useRef } from 'react';
import { Send, Radio, Signal, Settings } from 'lucide-react';

// Use relative URLs when served from FastAPI, or env variable for dev
const API_URL = import.meta.env.DEV
  ? `http://${import.meta.env.VITE_SERVER_ADDR || 'localhost:8000'}`
  : '';
const WS_URL = import.meta.env.DEV
  ? `ws://${import.meta.env.VITE_SERVER_ADDR || 'localhost:8000'}/ws`
  : `ws://${window.location.host}/ws`;

function App() {
  const [view, setView] = useState('chat');
  const [nodes, setNodes] = useState([]);
  const [messages, setMessages] = useState([]);
  const [selectedContact, setSelectedContact] = useState(null);
  const [newMessage, setNewMessage] = useState('');

  const [currentNodeId, setCurrentNodeId] = useState('');
  const [nodeName, setNodeName] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [originalNodeName, setOriginalNodeName] = useState('');


  const wsRef = useRef(null);
  const messagesEndRef = useRef(null);

  /* -------------------- LOAD CONFIG FROM BACKEND -------------------- */

  useEffect(() => {
    const loadConfig = async () => {
      const res = await fetch(`${API_URL}/api/config`);
      const data = await res.json();
      setCurrentNodeId(data.node_id);
      setNodeName(data.node_name);
      setOriginalNodeName(data.node_name);
    };

    loadConfig();
  }, []);

  /* -------------------- UPDATE NODE NAME -------------------- */

  const saveNodeNameIfChanged = async () => {
    if (nodeName === originalNodeName) return;

    setOriginalNodeName(nodeName);

    await fetch(`${API_URL}/api/config`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ node_name: nodeName }),
    });
  };

  /* -------------------- WEBSOCKET -------------------- */

  useEffect(() => {
    const connect = () => {
      if (wsRef.current) return;

      const ws = new WebSocket(WS_URL);

      ws.onopen = () => setIsConnected(true);

      ws.onmessage = (e) => {
        const data = JSON.parse(e.data);

        if (data.type === 'new_message') {
          setMessages((prev) =>
            prev.some((m) => m.id === data.data.id)
              ? prev
              : [...prev, data.data]
          );
        }

        if (data.type === 'nodes_updated') {
          setNodes(data.data);
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        wsRef.current = null;
        setTimeout(connect, 3000);
      };

      wsRef.current = ws;
    };

    connect();
    return () => wsRef.current?.close();
  }, []);

  /* -------------------- FETCH DATA -------------------- */

  useEffect(() => {
    fetch(`${API_URL}/api/nodes`)
      .then((r) => r.json())
      .then(setNodes);

    fetch(`${API_URL}/api/messages`)
      .then((r) => r.json())
      .then(setMessages)
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, selectedContact]);

  /* -------------------- HELPERS -------------------- */

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!newMessage.trim() || !selectedContact) return;

    const res = await fetch(`${API_URL}/api/messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        sender: currentNodeId,
        sender_name: nodeName,
        recipient: selectedContact.id,
        content: newMessage,
      }),
    });

    const sent = await res.json();
    setMessages((prev) => [...prev, sent]);
    setNewMessage('');
  };

  const getContactMessages = () =>
    messages
      .filter(
        (m) =>
          (m.sender === selectedContact?.id &&
            m.recipient === currentNodeId) ||
          (m.sender === currentNodeId &&
            m.recipient === selectedContact?.id)
      )
      .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

  const formatTime = (t) =>
    new Date(t).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  /* -------------------- UI -------------------- */

  return (
    <div className="flex h-screen bg-gray-900 text-white font-mono">
      {/* SIDEBAR */}
      <div className="w-80 bg-gray-800 border-r border-gray-700 flex flex-col">
        <div className="p-4 border-b border-gray-700">
          <div className="flex justify-between items-center mb-2">
            <h1 className="flex items-center gap-2 font-bold">
              <Radio /> Tactical Mesh
            </h1>
            <div
              className={`w-2 h-2 rounded-full ${
                isConnected ? 'bg-green-500' : 'bg-red-500'
              }`}
            />
          </div>

          <p className="text-xs text-gray-400">
            {nodeName} ({currentNodeId})
          </p>

          <button
            onClick={() => setView(view === 'settings' ? 'chat' : 'settings')}
            className="mt-2 w-full text-xs bg-gray-700 hover:bg-gray-600 px-2 py-1 rounded flex items-center justify-center gap-2"
          >
            <Settings className="w-4 h-4" />
            {view === 'settings' ? 'Back to Chat' : 'Configuration'}
          </button>
        </div>

        <div className="flex-1 overflow-y-auto">
          {nodes.map((n) => (
            <button
              key={n.id}
              onClick={() => {
                setSelectedContact(n);
                setView('chat');
              }}
              className={`w-full p-4 border-b border-gray-700 text-left hover:bg-gray-700 ${
                selectedContact?.id === n.id ? 'bg-gray-700' : ''
              }`}
            >
              <p className="font-semibold">{n.name}</p>
              <p className="text-xs text-gray-400">{n.id}</p>
            </button>
          ))}
        </div>
      </div>

      {/* MAIN */}
      <div className="flex-1 flex flex-col">
        {view === 'settings' ? (
          <div className="p-6 max-w-xl">
            <h2 className="text-xl font-bold mb-4">Node Configuration</h2>

            <label className="block text-xs mb-1">Node ID</label>
            <input
              value={currentNodeId}
              disabled
              className="w-full mb-4 bg-gray-800 border border-gray-700 px-3 py-2 rounded opacity-60 cursor-not-allowed"
            />

            <label className="block text-xs mb-1">Display Name</label>
            <input
              value={nodeName}
              onChange={(e) => setNodeName(e.target.value)}
              onBlur={saveNodeNameIfChanged}
              className="w-full bg-gray-800 border border-gray-700 px-3 py-2 rounded"
            />

            <p className="text-xs text-gray-500 mt-2">
              Changes are saved immediately.
            </p>
          </div>
        ) : selectedContact ? (
          <>
            <div className="p-4 border-b border-gray-700 bg-gray-800">
              <h2 className="font-bold">{selectedContact.name}</h2>
              <p className="text-xs text-gray-400">{selectedContact.id}</p>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {getContactMessages().map((m, i) => {
                const own = m.sender === currentNodeId;
                return (
                  <div key={i} className={`flex ${own ? 'justify-end' : ''}`}>
                    <div
                      className={`max-w-md p-3 rounded border ${
                        own
                          ? 'bg-green-900 border-green-700'
                          : 'bg-gray-800 border-gray-700'
                      }`}
                    >
                      <p className="text-xs text-gray-400 mb-1">
                        {m.sender_name || m.sender}
                      </p>
                      <p>{m.content}</p>
                      <p className="text-xs text-right text-gray-400">
                        {formatTime(m.timestamp)}
                      </p>
                    </div>
                  </div>
                );
              })}
              <div ref={messagesEndRef} />
            </div>

            <form
              onSubmit={handleSendMessage}
              className="p-4 border-t border-gray-700 bg-gray-800 flex gap-2"
            >
              <input
                value={newMessage}
                onChange={(e) => setNewMessage(e.target.value)}
                className="flex-1 bg-gray-900 px-3 py-2 rounded"
                placeholder="Enter message..."
              />
              <button className="bg-green-700 px-4 py-2 rounded flex gap-2">
                <Send className="w-4 h-4" /> Send
              </button>
            </form>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-gray-500">
            Select a contact
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
