export interface Node {
  id: string;
  name: string;
  x?: number;
  y?: number;
  status: 'online' | 'offline' | 'error';
  config: { encryption: string };
}

export interface BackendTraffic {
  id: number;
  sender: string;
  data: string;
  timestamp: number;
}

export interface BackendState {
  nodes: string[];
  topology: Record<string, string[]>;
  traffic: BackendTraffic[];
}