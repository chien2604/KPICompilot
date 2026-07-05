import { useRef, useEffect, useState, useCallback } from 'react';
import { Drawer, Avatar, Tag } from 'antd';
import { UserOutlined } from '@ant-design/icons';
import { riskColor } from '../utils/formatters';

// ── Helpers ──────────────────────────────────────────────────────────────────

function buildTree(departments, kpiMap) {
  const nodeMap = {};
  departments.forEach((d) => {
    nodeMap[d.id] = {
      ...d,
      avg_kpi: kpiMap[d.id]?.avg_kpi ?? null,
      user_count: kpiMap[d.id]?.user_count ?? 0,
      children: [],
    };
  });
  const roots = [];
  departments.forEach((d) => {
    if (d.parent_id && nodeMap[d.parent_id]) {
      nodeMap[d.parent_id].children.push(nodeMap[d.id]);
    } else if (!d.parent_id) {
      roots.push(nodeMap[d.id]);
    }
  });
  return roots;
}

function collectEdges(nodes) {
  const edges = [];
  function walk(list) {
    list.forEach((node) => {
      node.children.forEach((child) => {
        edges.push({ from: node.id, to: child.id });
        walk([child]);
      });
    });
  }
  walk(nodes);
  return edges;
}

// ── Drawer thông tin cán bộ ───────────────────────────────────────────────────

function StaffDrawer({ open, onClose, position, users, scoreMap }) {
  return (
    <Drawer
      title={
        <span style={{ fontSize: 16, fontWeight: 700 }}>
          {position} <span style={{ color: '#94a3b8', fontWeight: 400, fontSize: 13 }}>({users.length} người)</span>
        </span>
      }
      open={open}
      onClose={onClose}
      width={380}
      bodyStyle={{ padding: '12px 16px' }}
    >
      <div className="org-drawer-list">
        {users.map((u) => {
          const score = scoreMap?.[u.id];
          const color = score != null ? riskColor(score) : '#94a3b8';
          return (
            <div key={u.id} className="org-drawer-item">
              <Avatar
                src={u.avatar_url}
                icon={<UserOutlined />}
                size={40}
                style={{ flexShrink: 0, background: '#e6f0ff', color: '#0062ff' }}
              />
              <div className="org-drawer-item__info">
                <div className="org-drawer-item__name-row">
                  <span className="org-drawer-item__name">{u.full_name}</span>
                  {score != null && (
                    <span className="org-drawer-item__score" style={{ color }}>
                      {score}
                    </span>
                  )}
                </div>
                <div className="org-drawer-item__meta">
                  <Tag color="blue" style={{ fontSize: 12 }}>{u.position_title}</Tag>
                  {u.role === 'LEADER' && <Tag color="gold" style={{ fontSize: 12 }}>Lãnh đạo</Tag>}
                  {u.role === 'MANAGER' && <Tag color="cyan" style={{ fontSize: 12 }}>Quản lý</Tag>}
                </div>
                <div style={{ fontSize: 12, color: '#94a3b8', marginTop: 2 }}>{u.email}</div>
              </div>
            </div>
          );
        })}
      </div>
    </Drawer>
  );
}

// ── Node card ─────────────────────────────────────────────────────────────────

function OrgNodeCard({ node, isRoot, nodeRef, deptUsers, scoreMap }) {
  const score = node.avg_kpi;
  const color = score !== null ? riskColor(score) : '#94a3b8';

  // Nhóm unique chức vụ trong dept này
  const positions = [...new Set(deptUsers.map((u) => u.position_title).filter(Boolean))];

  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selectedPosition, setSelectedPosition] = useState(null);

  const usersOfPosition = selectedPosition
    ? deptUsers.filter((u) => u.position_title === selectedPosition)
    : [];

  const handlePositionClick = (pos, e) => {
    e.stopPropagation();
    setSelectedPosition(pos);
    setDrawerOpen(true);
  };

  return (
    <>
      <div
        ref={nodeRef}
        className={`org-card ${isRoot ? 'org-card--root' : ''}`}
        style={{ borderColor: color }}
        data-node-id={node.id}
      >
        <div className="org-card__name">{node.name}</div>
        <div className="org-card__score" style={{ color }}>
          {score !== null ? score : '—'}
        </div>
        {!isRoot && (
          <div className="org-card__meta">{node.user_count} cán bộ</div>
        )}

        {/* Danh sách chức vụ */}
        {positions.length > 0 && (
          <div className="org-card__positions">
            {positions.map((pos) => {
              const count = deptUsers.filter((u) => u.position_title === pos).length;
              return (
                <button
                  key={pos}
                  className="org-card__position-btn"
                  onClick={(e) => handlePositionClick(pos, e)}
                  type="button"
                  style={{ borderColor: color + '55', color }}
                >
                  <span className="org-card__position-name">{pos}</span>
                  <span className="org-card__position-count">{count}</span>
                </button>
              );
            })}
          </div>
        )}
      </div>

      <StaffDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        position={selectedPosition}
        users={usersOfPosition}
        scoreMap={scoreMap}
      />
    </>
  );
}

// ── Tree renderer ─────────────────────────────────────────────────────────────

function TreeNodes({ nodes, depth, registerRef, usersByDept, scoreMap }) {
  return (
    <div className="org-tree-level">
      {nodes.map((node) => {
        const ref = (el) => registerRef(node.id, el);
        const deptUsers = usersByDept[node.id] || [];
        return (
          <div key={node.id} className="org-tree-node-wrap">
            <OrgNodeCard
              node={node}
              isRoot={depth === 0}
              nodeRef={ref}
              deptUsers={deptUsers}
              scoreMap={scoreMap}
            />
            {node.children.length > 0 && (
              <div className="org-tree-children-wrap">
                <TreeNodes
                  nodes={node.children}
                  depth={depth + 1}
                  registerRef={registerRef}
                  usersByDept={usersByDept}
                  scoreMap={scoreMap}
                />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── Main export ───────────────────────────────────────────────────────────────

export default function OrgHeatmap({ data = [], departments = [], users = [], ranking = [] }) {
  const kpiMap = {};
  data.forEach((d) => { kpiMap[d.department_id] = d; });
  const roots = buildTree(departments, kpiMap);

  // Map user_id -> score từ ranking
  const scoreMap = {};
  ranking.forEach((r) => { scoreMap[r.user_id] = r.score; });

  // Nhóm users theo department_id
  const usersByDept = {};
  users.forEach((u) => {
    if (!usersByDept[u.department_id]) usersByDept[u.department_id] = [];
    usersByDept[u.department_id].push(u);
  });

  const containerRef = useRef(null);
  const nodeRefs = useRef({});
  const [lines, setLines] = useState([]);

  const registerRef = useCallback((id, el) => {
    nodeRefs.current[id] = el;
  }, []);

  useEffect(() => {
    if (!containerRef.current || !roots.length) return;
    const compute = () => {
      const containerRect = containerRef.current.getBoundingClientRect();
      const edges = collectEdges(roots);
      const newLines = [];
      edges.forEach(({ from, to }) => {
        const fromEl = nodeRefs.current[from];
        const toEl = nodeRefs.current[to];
        if (!fromEl || !toEl) return;
        const fromRect = fromEl.getBoundingClientRect();
        const toRect = toEl.getBoundingClientRect();
        newLines.push({
          x1: fromRect.left + fromRect.width / 2 - containerRect.left,
          y1: fromRect.bottom - containerRect.top,
          x2: toRect.left + toRect.width / 2 - containerRect.left,
          y2: toRect.top - containerRect.top,
          id: `${from}-${to}`,
        });
      });
      setLines(newLines);
    };
    const timer = setTimeout(compute, 80);
    window.addEventListener('resize', compute);
    return () => { clearTimeout(timer); window.removeEventListener('resize', compute); };
  }, [roots, departments, data, users]);

  if (!roots.length) {
    return <div style={{ textAlign: 'center', color: '#94a3b8', padding: 40 }}>Đang tải dữ liệu...</div>;
  }

  return (
    <div ref={containerRef} className="org-tree-wrap" style={{ position: 'relative' }}>
      <svg style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', pointerEvents: 'none', overflow: 'visible' }}>
        {lines.map((line) => (
          <line key={line.id} x1={line.x1} y1={line.y1} x2={line.x2} y2={line.y2} stroke="#cbd5e1" strokeWidth="2" />
        ))}
      </svg>
      <TreeNodes nodes={roots} depth={0} registerRef={registerRef} usersByDept={usersByDept} scoreMap={scoreMap} />
    </div>
  );
}
