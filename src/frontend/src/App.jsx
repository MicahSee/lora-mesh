import React, { useState, useEffect, useRef } from 'react';
import { Send, Radio, Signal, Settings, Sliders } from 'lucide-react';

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

  const [radioParams, setRadioParams] = useState([]);
  const [radioValues, setRadioValues] = useState({});


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

  /* -------------------- LOAD RADIO PARAMETERS -------------------- */

  const loadRadioParams = async () => {
    try {
      const [paramsRes, valuesRes] = await Promise.all([
        fetch(`${API_URL}/api/radio/parameters`),
        fetch(`${API_URL}/api/radio/values`),
      ]);
      const params = await paramsRes.json();
      const values = await valuesRes.json();
      setRadioParams(params);
      setRadioValues(values);
    } catch (err) {
      console.error('Failed to load radio parameters:', err);
    }
  };

  useEffect(() => {
    loadRadioParams();
  }, []);

  const updateRadioParam = async (name, value) => {
    // Optimistic update
    setRadioValues((prev) => ({ ...prev, [name]: value }));

    try {
      const res = await fetch(`${API_URL}/api/radio/values`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, value }),
      });
      const result = await res.json();
      if (!result.success) {
        console.error('Failed to update radio param:', result.error);
        loadRadioParams(); // Revert on failure
      }
    } catch (err) {
      console.error('Failed to update radio param:', err);
      loadRadioParams();
    }
  };

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
          if (data.data.sender_name) {
            setNodes((prev) => {
              const exists = prev.some((n) => n.id === data.data.sender);

              if (exists) {
                return prev.map((n) =>
                  n.id === data.data.sender 
                    ? { ...n, name: data.data.sender_name } 
                    : n
                );
              } else {
                return [...prev, { id: data.data.sender, name: data.data.sender_name }];
              }
            });
          }

          setMessages((prev) =>
            prev.some((m) => m.id === data.data.id)
              ? prev
              : [...prev, data.data]
          );
        }

        if (data.type === 'nodes_update') {
          console.log('Nodes updated via websocket:', data.data);
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

    const messageContent = newMessage.trim();
    const tempId = `temp-${Date.now()}`;

    const tempMessage = {
      id: tempId,
      sender: currentNodeId,
      recipient: selectedContact.id,
      content: newMessage,
      timestamp: new Date().toISOString(),
      status: 'sending',
    }

    setMessages((prev) => [...prev, tempMessage]);
    setNewMessage('');

    fetch(`${API_URL}/api/messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        sender: currentNodeId,
        sender_name: nodeName,
        recipient: selectedContact.id,
        content: messageContent,
      }),
    })
    .then(async (res) => {
      if (!res.ok) throw new Error();
      const sentData = await res.json();
      
      setMessages((prev) =>
        prev.map((msg) => (msg.id === tempId ? { ...sentData, status: sentData.status, id: sentData.id } : msg))
      );
    })
    .catch(() => {
      setMessages((prev) =>
        prev.map((msg) => (msg.id === tempId ? { ...msg, status: 'failed'} : msg))
      );
    });
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

  const formatParamName = (name) =>
    name.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

  /* -------------------- UI -------------------- */

  return (
    <div className="flex h-screen bg-gray-900 text-white font-sans">
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

        <div className="flex-1 overflow-y-auto [&::-webkit-scrollbar]:w-2 [&::-webkit-scrollbar-track]:bg-gray-800 [&::-webkit-scrollbar-thumb]:bg-gray-600 [&::-webkit-scrollbar-thumb]:rounded-full hover:[&::-webkit-scrollbar-thumb]:bg-gray-500">
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
          <div className="p-6 max-w-xl overflow-y-auto flex-1 [&::-webkit-scrollbar]:w-2 [&::-webkit-scrollbar-track]:bg-gray-800 [&::-webkit-scrollbar-thumb]:bg-gray-600 [&::-webkit-scrollbar-thumb]:rounded-full hover:[&::-webkit-scrollbar-thumb]:bg-gray-500">
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

            {/* Radio Parameters */}
            <h2 className="text-xl font-bold mt-8 mb-4 flex items-center gap-2">
              <Sliders className="w-5 h-5" /> Radio Settings
            </h2>

            {radioParams.length === 0 ? (
              <p className="text-gray-500 text-sm">Loading radio parameters...</p>
            ) : (
              <div className="space-y-4">
                {radioParams.map((param) => (
                  <div key={param.name} className="border border-gray-700 rounded p-3">
                    <div className="flex justify-between items-center mb-1">
                      <label className="text-sm font-medium">
                        {formatParamName(param.name)}
                        {param.unit && <span className="text-gray-400 ml-1">({param.unit})</span>}
                      </label>
                      {param.readonly && (
                        <span className="text-xs bg-gray-700 px-2 py-0.5 rounded">Read-only</span>
                      )}
                    </div>
                    <p className="text-xs text-gray-400 mb-2">{param.description}</p>

                    {/* Boolean toggle */}
                    {param.param_type === 'bool' && (
                      <button
                        onClick={() => !param.readonly && updateRadioParam(param.name, !radioValues[param.name])}
                        disabled={param.readonly}
                        className={`px-3 py-1 rounded text-sm ${
                          radioValues[param.name]
                            ? 'bg-green-700 hover:bg-green-600'
                            : 'bg-gray-700 hover:bg-gray-600'
                        } ${param.readonly ? 'opacity-50 cursor-not-allowed' : ''}`}
                      >
                        {radioValues[param.name] ? 'Enabled' : 'Disabled'}
                      </button>
                    )}

                    {/* Enum select */}
                    {param.param_type === 'enum' && (
                      <select
                        value={radioValues[param.name] ?? ''}
                        onChange={(e) => {
                          const val = isNaN(Number(e.target.value))
                            ? e.target.value
                            : Number(e.target.value);
                          updateRadioParam(param.name, val);
                        }}
                        disabled={param.readonly}
                        className={`w-full bg-gray-800 border border-gray-700 px-3 py-2 rounded ${
                          param.readonly ? 'opacity-50 cursor-not-allowed' : ''
                        }`}
                      >
                        {param.valid_values.map((v) => (
                          <option key={v} value={v}>
                            {v}
                            {param.unit ? ` ${param.unit}` : ''}
                          </option>
                        ))}
                      </select>
                    )}

                    {/* Numeric range (int/float) */}
                    {(param.param_type === 'int' || param.param_type === 'float') && (
                      <div className="flex items-center gap-3">
                        <input
                          type="range"
                          min={param.valid_values[0]}
                          max={param.valid_values[1]}
                          step={param.step || (param.param_type === 'float' ? 0.1 : 1)}
                          value={radioValues[param.name] ?? param.valid_values[0]}
                          onChange={(e) => {
                            const val = param.param_type === 'int'
                              ? parseInt(e.target.value)
                              : parseFloat(e.target.value);
                            updateRadioParam(param.name, val);
                          }}
                          disabled={param.readonly}
                          className={`flex-1 ${param.readonly ? 'opacity-50 cursor-not-allowed' : ''}`}
                        />
                        <input
                          type="number"
                          min={param.valid_values[0]}
                          max={param.valid_values[1]}
                          step={param.step || (param.param_type === 'float' ? 0.1 : 1)}
                          value={radioValues[param.name] ?? ''}
                          onChange={(e) => {
                            const val = param.param_type === 'int'
                              ? parseInt(e.target.value)
                              : parseFloat(e.target.value);
                            if (!isNaN(val)) updateRadioParam(param.name, val);
                          }}
                          disabled={param.readonly}
                          className={`w-24 bg-gray-800 border border-gray-700 px-2 py-1 rounded text-sm ${
                            param.readonly ? 'opacity-50 cursor-not-allowed' : ''
                          }`}
                        />
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : selectedContact ? (
          <>
            <div className="p-4 border-b border-gray-700 bg-gray-800">
              <h2 className="font-bold">{selectedContact.name}</h2>
              <p className="text-xs text-gray-400">{selectedContact.id}</p>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-3 [&::-webkit-scrollbar]:w-2 [&::-webkit-scrollbar-track]:bg-gray-900 [&::-webkit-scrollbar-thumb]:bg-gray-600 [&::-webkit-scrollbar-thumb]:rounded-full hover:[&::-webkit-scrollbar-thumb]:bg-gray-500">
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
                      <p>{m.content}</p>
                      
                      {/* Flex container for Time + Status Icon */}
                      <div className="flex items-center justify-end gap-1.5 mt-1">
                        <p className="text-xs text-gray-400">
                          {formatTime(m.timestamp)}
                        </p>

                        {/* Status Indicator Logic */}
                        {own && (
                          <span className="flex items-center">
                            {m.status === 'sending' && (
                              <div className="w-3 h-3 border-2 border-gray-400 border-t-transparent rounded-full animate-spin" />
                            )}
                            
                            {m.status === 'sent' && (
                              <svg className="w-3.5 h-3.5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M5 13l4 4L19 7" />
                              </svg>
                            )}

                            {m.status === 'failed' && (
                              <span title="Failed to send" className="text-red-500 text-xs leading-none">
                                ⚠️
                              </span>
                            )}
                          </span>
                        )}
                      </div>
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
              <button className="bg-green-700 px-4 py-2 rounded flex items-center gap-2">
                <Send className="w-4 h-4" />
                <span>Send</span>
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
