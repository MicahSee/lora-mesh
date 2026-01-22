import React, { useState, useEffect, useRef } from 'react';
import { Send, Radio, Signal, User } from 'lucide-react';

const serverAddr = import.meta.env.VITE_SERVER_ADDR;

const API_URL = `http://${serverAddr}`;
const WS_URL = `ws://${serverAddr}/ws`;

function App() {
  const [nodes, setNodes] = useState([]);
  const [messages, setMessages] = useState([]);
  const [selectedContact, setSelectedContact] = useState(null);
  const [newMessage, setNewMessage] = useState('');
  const [currentNodeId, setCurrentNodeId] = useState('raspberry-pi-001');
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    const connectWebSocket = () => {
      if (wsRef.current && wsRef.current.readyState !== WebSocket.CLOSED) return;

      const ws = new WebSocket(WS_URL);

      ws.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'new_message') {
          setMessages(prev => {
            if (prev.some(msg => msg.id === data.data.id)) return prev;
            return [...prev, data.data];
          });
        } else if (data.type === 'nodes_updated') {
          setNodes(data.data);
        }
      };

      ws.onclose = () => {
        console.log('WebSocket disconnected');
        setIsConnected(false);
        wsRef.current = null;
        setTimeout(connectWebSocket, 3000);
      };

      wsRef.current = ws;
    };

    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    const fetchNodes = async () => {
      try {
        const response = await fetch(`${API_URL}/api/nodes`);
        const data = await response.json();
        setNodes(data);
      } catch (error) {
        console.error('Error fetching nodes:', error);
      }
    };
    fetchNodes();
    const interval = setInterval(fetchNodes, 30000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const fetchMessages = async () => {
      try {
        const response = await fetch(`${API_URL}/api/messages`);
        const data = await response.json();
        setMessages(data);
      } catch (error) {
        console.error('Error fetching messages:', error);
      }
    };
    fetchMessages();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, selectedContact]);

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!newMessage.trim() || !selectedContact) return;

    try {
      const response = await fetch(`${API_URL}/api/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          recipient: selectedContact.id,
          content: newMessage,
        }),
      });
      const sentMessage = await response.json();
      setMessages(prev => [...prev, sentMessage]);
      setNewMessage('');
    } catch (error) {
      console.error('Error sending message:', error);
    }
  };

  const getContactMessages = () => {
    if (!selectedContact) return [];
    return messages
      .filter(msg =>
        (msg.sender === selectedContact.id && msg.recipient === currentNodeId) ||
        (msg.sender === currentNodeId && msg.recipient === selectedContact.id)
      )
      .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
  };

  const getLastMessage = (nodeId) => {
    const contactMessages = messages.filter(msg =>
      msg.sender === nodeId || msg.recipient === nodeId
    );
    if (contactMessages.length === 0) return null;
    return contactMessages[contactMessages.length - 1];
  };

  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const getSignalStrengthColor = (strength) => {
    if (!strength) return 'text-gray-400';
    if (strength > -50) return 'text-green-400';
    if (strength > -70) return 'text-yellow-400';
    return 'text-red-400';
  };

  return (
    <div className="flex h-screen bg-gray-900 text-white font-mono">
      {/* Sidebar */}
      <div className="w-80 bg-gray-800 border-r border-gray-700 flex flex-col">
        <div className="p-4 border-b border-gray-700">
          <div className="flex items-center justify-between mb-2">
            <h1 className="text-xl font-bold flex items-center gap-2 uppercase tracking-wider">
              <Radio className="w-6 h-6" />
              Tactical Mesh
            </h1>
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
              <span className="text-xs text-gray-400">{isConnected ? 'Online' : 'Offline'}</span>
            </div>
          </div>
          <p className="text-xs text-gray-400">Node: {currentNodeId}</p>
        </div>

        <div className="flex-1 overflow-y-auto bg-gray-900">
          {nodes.length === 0 ? (
            <div className="p-4 text-center text-gray-500">
              <Signal className="w-12 h-12 mx-auto mb-2 opacity-50" />
              <p>Scanning for nodes...</p>
            </div>
          ) : (
            nodes.map(node => {
              const lastMsg = getLastMessage(node.id);
              return (
                <button
                  key={node.id}
                  onClick={() => setSelectedContact(node)}
                  className={`w-full p-4 border-b border-gray-700 hover:bg-gray-700 transition-colors text-left ${
                    selectedContact?.id === node.id ? 'bg-gray-700' : ''
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <User className="w-5 h-5 text-gray-400" />
                      <span className="font-semibold">{node.name}</span>
                    </div>
                    <Signal className={`w-4 h-4 ${getSignalStrengthColor(node.signal_strength)}`} />
                  </div>
                  <p className="text-xs text-gray-400 mb-1">{node.id}</p>
                  {lastMsg && (
                    <p className="text-sm text-gray-500 truncate">
                      {lastMsg.sender === currentNodeId ? 'You: ' : ''}
                      {lastMsg.content}
                    </p>
                  )}
                </button>
              );
            })
          )}
        </div>
      </div>

      {/* Chat Area */}
      <div className="flex-1 flex flex-col bg-gray-900">
        {selectedContact ? (
          <>
            {/* Header */}
            <div className="p-4 bg-gray-800 border-b border-gray-700 flex justify-between items-center">
              <div>
                <h2 className="font-bold text-lg tracking-wide">{selectedContact.name}</h2>
                <p className="text-xs text-gray-400">{selectedContact.id}</p>
              </div>
              <div className="text-right">
                <p className="text-xs text-gray-500 uppercase">Signal</p>
                <p className={`text-sm font-medium ${getSignalStrengthColor(selectedContact.signal_strength)}`}>
                  {selectedContact.signal_strength} dBm
                </p>
              </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {getContactMessages().map((msg, idx) => {
                const isOwnMessage = msg.sender === currentNodeId;
                return (
                  <div key={idx} className={`flex ${isOwnMessage ? 'justify-end' : 'justify-start'}`}>
                    <div
                      className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg border ${
                        isOwnMessage
                          ? 'bg-green-900 border-green-700 text-green-100'
                          : 'bg-gray-800 border-gray-700 text-gray-200'
                      }`}
                    >
                      <p className="tracking-wide">{msg.content}</p>
                      <div className="flex items-center justify-end gap-2 mt-1 text-xs text-gray-400">
                        <span>{formatTime(msg.timestamp)}</span>
                        {isOwnMessage && (
                          <span>
                            {msg.status === 'sent' ? '✓' : msg.status === 'delivered' ? '✓✓' : '✗'}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
              <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <form onSubmit={handleSendMessage} className="p-4 bg-gray-800 border-t border-gray-700 flex items-center gap-2">
              <input
                type="text"
                value={newMessage}
                onChange={(e) => setNewMessage(e.target.value)}
                placeholder="Enter message..."
                className="flex-1 bg-gray-900 text-green-100 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-green-600"
              />
              <button
                type="submit"
                disabled={!newMessage.trim()}
                className="bg-green-700 hover:bg-green-600 disabled:bg-gray-600 text-white px-6 py-2 rounded-lg flex items-center gap-2 transition-colors"
              >
                <Send className="w-4 h-4" />
                Send
              </button>
            </form>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-gray-500">
            <div className="text-center">
              <Radio className="w-16 h-16 mx-auto mb-4 opacity-50" />
              <p className="text-lg uppercase tracking-wide">Select a contact to start messaging</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
