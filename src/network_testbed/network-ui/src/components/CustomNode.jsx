import { Handle, Position } from 'reactflow';

export default function CustomNode({ data }) {
  return (
    <div
      style={{
        background: '#1e293b',
        color: '#e2e8f0',
        border: '0px solid #3b82f6',
        borderRadius: '8px',
        padding: '12px 20px',
        fontSize: '14px',
        fontWeight: '500',
        width: 150,
      }}
    >
      {/* Top handles */}
      <Handle type="target" position={Position.Top} id="top-target" />
      <Handle type="source" position={Position.Top} id="top-source" />

      {/* Right handles */}
      <Handle type="target" position={Position.Right} id="right-target" />
      <Handle type="source" position={Position.Right} id="right-source" />

      <div>{data.label}</div>

      {/* Bottom handles */}
      <Handle type="target" position={Position.Bottom} id="bottom-target" />
      <Handle type="source" position={Position.Bottom} id="bottom-source" />

      {/* Left handles */}
      <Handle type="target" position={Position.Left} id="left-target" />
      <Handle type="source" position={Position.Left} id="left-source" />
    </div>
  );
}
