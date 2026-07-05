import {
  Button, Card, DatePicker, Form, Input, InputNumber, Modal,
  Select, Space, Tabs, Tag, Typography, message,
} from 'antd';
import {
  FilterOutlined, PlusOutlined, ReloadOutlined, SaveOutlined, UserOutlined,
} from '@ant-design/icons';
import { useEffect, useMemo, useState } from 'react';
import dayjs from 'dayjs';
import { taskApi } from '../api/taskApi';
import { authApi } from '../api/authApi';
import { useAuth } from '../contexts/AuthContext';
import TaskTable from '../components/TaskTable';

const STATUS_OPTIONS = [
  { value: 'COMPLETED',   label: 'Hoàn thành',     color: '#16a34a' },
  { value: 'IN_PROGRESS', label: 'Đang thực hiện', color: '#f59e0b' },
  { value: 'NOT_STARTED', label: 'Chưa bắt đầu',  color: '#64748b' },
  { value: 'OVERDUE',     label: 'Quá hạn',        color: '#dc2626' },
];

export default function TasksPage() {
  const { user } = useAuth();
  const myId = user?.user_id;
  const canAssign = user?.level <= 4; // Chuyên viên (5) không giao được

  // Danh sách người có thể giao việc (theo phân quyền)
  const [assignableUsers, setAssignableUsers] = useState([]);

  // Tasks của mình (được giao cho mình)
  const [myTasks, setMyTasks]         = useState([]);
  // Tasks mình đã giao cho cấp dưới
  const [assignedTasks, setAssignedTasks] = useState([]);

  const [open, setOpen]               = useState(false);
  const [scoreModal, setScoreModal]   = useState(null); // { taskId, userId, userName }
  const [form]                        = Form.useForm();
  const [scoreForm]                   = Form.useForm();

  // Bộ lọc
  const [filterStatus,    setFilterStatus]    = useState(null);
  const [filterDateRange, setFilterDateRange] = useState(null);

  // Tab đang active
  const [activeTab, setActiveTab] = useState('mine');

  /* ── Load data ───────────────────────────────── */
  const loadAll = () => {
    if (!myId) return;
    // Task được giao cho mình
    taskApi.list({ assigned_user_id: myId }).then(setMyTasks);
    // Task mình đã tạo (giao cho cấp dưới)
    if (canAssign) {
      taskApi.list({ creator_id: myId }).then(setAssignedTasks);
    }
  };

  useEffect(() => {
    loadAll();
    authApi.assignableUsers().then(setAssignableUsers).catch(() => setAssignableUsers([]));
  }, [myId]);

  /* ── Dropdown giao việc nhóm theo phòng ban ──── */
  const assignedUserOptions = useMemo(() => {
    const byDept = {};
    assignableUsers.forEach((u) => {
      const k = u.department_name || 'Khác';
      if (!byDept[k]) byDept[k] = [];
      byDept[k].push({ value: u.id, label: `${u.full_name} — ${u.position_title || ''}` });
    });
    return Object.entries(byDept).map(([label, options]) => ({ label, options }));
  }, [assignableUsers]);

  /* ── Lọc client-side ─────────────────────────── */
  const applyFilter = (list) => {
    let result = list;
    if (filterStatus) result = result.filter((t) => t.status === filterStatus);
    if (filterDateRange?.[0] && filterDateRange?.[1]) {
      const from = filterDateRange[0].startOf('day');
      const to   = filterDateRange[1].endOf('day');
      result = result.filter((t) => {
        if (!t.deadline) return false;
        const d = dayjs(t.deadline);
        return d.isAfter(from) && d.isBefore(to);
      });
    }
    return result;
  };

  const filteredMine     = useMemo(() => applyFilter(myTasks),     [myTasks,     filterStatus, filterDateRange]);
  const filteredAssigned = useMemo(() => applyFilter(assignedTasks), [assignedTasks, filterStatus, filterDateRange]);

  const hasFilter = filterStatus || filterDateRange;
  const clearFilters = () => { setFilterStatus(null); setFilterDateRange(null); };

  /* ── Tạo nhiệm vụ ────────────────────────────── */
  const createTask = async () => {
    const values = await form.validateFields();
    await taskApi.create({
      ...values,
      creator_id: myId,
      assigned_user_ids: values.assigned_user_ids || [],
    });
    message.success('Đã tạo nhiệm vụ');
    setOpen(false);
    form.resetFields();
    loadAll();
    setActiveTab('assigned'); // chuyển sang tab đã giao
  };

  /* ── Chấm điểm ───────────────────────────────── */
  const submitScore = async () => {
    const values = await scoreForm.validateFields();
    await taskApi.scoreAssignment(scoreModal.taskId, scoreModal.userId, values.leader_score);
    message.success(`Đã chấm điểm cho ${scoreModal.userName}`);
    setScoreModal(null);
    scoreForm.resetFields();
    loadAll();
  };

  /* ── Cập nhật trạng thái ─────────────────────── */
  const updateTaskStatus = async (taskId, newStatus) => {
    try {
      await taskApi.updateStatus(taskId, { status: newStatus });
      message.success('Đã cập nhật trạng thái công việc');
      loadAll();
    } catch (err) {
      message.error('Lỗi khi cập nhật trạng thái');
    }
  };

  /* ── Render bộ lọc (dùng lại ở cả 2 tab) ─────── */
  const FilterBar = ({ total, shown }) => (
    <Card size="small" className="task-filter-bar" style={{ marginBottom: 16 }}>
      <div className="task-filter-bar__inner">
        <FilterOutlined style={{ color: '#64748b', fontSize: 16 }} />
        <span className="task-filter-bar__title">Lọc theo:</span>

        <div className="task-filter-bar__group">
          <span className="task-filter-bar__label">Trạng thái</span>
          <Space size={8} wrap>
            {STATUS_OPTIONS.map((opt) => (
              <Tag
                key={opt.value}
                className="task-filter-tag"
                style={{
                  borderColor: opt.color,
                  color: filterStatus === opt.value ? '#fff' : opt.color,
                  background: filterStatus === opt.value ? opt.color : `${opt.color}15`,
                  cursor: 'pointer', fontSize: 14, padding: '3px 12px',
                  borderRadius: 20, userSelect: 'none',
                }}
                onClick={() => setFilterStatus(filterStatus === opt.value ? null : opt.value)}
              >
                {opt.label}{filterStatus === opt.value && ' ✕'}
              </Tag>
            ))}
          </Space>
        </div>

        <div className="task-filter-bar__group">
          <span className="task-filter-bar__label">Hạn xử lý</span>
          <DatePicker.RangePicker
            value={filterDateRange}
            onChange={setFilterDateRange}
            format="DD/MM/YYYY"
            placeholder={['Từ ngày', 'Đến ngày']}
          />
        </div>

        {hasFilter && (
          <Button size="small" danger type="primary" onClick={clearFilters} style={{ marginLeft: 'auto' }}>
            Xóa bộ lọc
          </Button>
        )}
      </div>
      {hasFilter && (
        <div className="task-filter-bar__result">
          Hiển thị <b>{shown}</b> / {total} nhiệm vụ
        </div>
      )}
    </Card>
  );

  /* ── Tab items ───────────────────────────────── */
  const tabItems = [
    {
      key: 'mine',
      label: (
        <span>
          <UserOutlined /> Nhiệm vụ phụ trách
          <Tag style={{ marginLeft: 8, borderRadius: 20 }} color="blue">{myTasks.length}</Tag>
        </span>
      ),
      children: (
        <>
          <FilterBar total={myTasks.length} shown={filteredMine.length} />
          <Card>
            <TaskTable data={filteredMine} onStatusChange={updateTaskStatus} />
          </Card>
        </>
      ),
    },
    ...(canAssign ? [{
      key: 'assigned',
      label: (
        <span>
          Nhiệm vụ đã giao
          <Tag style={{ marginLeft: 8, borderRadius: 20 }} color="gold">{assignedTasks.length}</Tag>
        </span>
      ),
      children: (
        <>
          <FilterBar total={assignedTasks.length} shown={filteredAssigned.length} />
          <Card>
            <TaskTable
              data={filteredAssigned}
              canScore
              assignableUserIds={new Set(assignableUsers.map((u) => u.id))}
              onScoreAssignment={(taskId, userId, userName) => setScoreModal({ taskId, userId, userName })}
              onStatusChange={updateTaskStatus}
            />
          </Card>
        </>
      ),
    }] : []),
  ];

  return (
    <Space direction="vertical" size={18} className="page">
      <div className="page-title-row">
        <Typography.Title level={3} style={{ margin: 0 }}>Quản lý Công việc</Typography.Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={loadAll}>Tải lại</Button>
          {canAssign && (
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setOpen(true)}>
              Tạo nhiệm vụ
            </Button>
          )}
        </Space>
      </div>

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={tabItems}
        size="large"
        style={{ background: 'transparent' }}
      />

      {/* Modal tạo nhiệm vụ */}
      <Modal
        title="Tạo nhiệm vụ mới"
        open={open}
        onOk={createTask}
        onCancel={() => { setOpen(false); form.resetFields(); }}
        okText="Tạo"
        cancelText="Huỷ"
      >
        <Form layout="vertical" form={form} initialValues={{ document_type: 'C', status: 'NOT_STARTED', priority: 'MEDIUM' }}>
          <Form.Item name="title" label="Tên nhiệm vụ" rules={[{ required: true, message: 'Vui lòng nhập tên nhiệm vụ' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="description" label="Mô tả">
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item name="document_type" label="Nhóm văn bản">
            <Select options={['A', 'B', 'C', 'D'].map((v) => ({ value: v, label: v }))} />
          </Form.Item>
          <Form.Item
            name="assigned_user_ids"
            label={`Giao cho (${assignableUsers.length} người trong phạm vi quyền)`}
            help={assignableUsers.length === 0 ? 'Bạn không có quyền giao việc cho ai.' : undefined}
          >
            <Select
              mode="multiple"
              showSearch
              optionFilterProp="label"
              options={assignedUserOptions}
              placeholder="Chọn người nhận việc..."
            />
          </Form.Item>
        </Form>
      </Modal>

      {/* Modal chấm điểm */}
      <Modal
        title={`Chấm điểm: ${scoreModal?.userName}`}
        open={!!scoreModal}
        onOk={submitScore}
        onCancel={() => { setScoreModal(null); scoreForm.resetFields(); }}
        okText="Lưu điểm"
        cancelText="Huỷ"
      >
        <Form layout="vertical" form={scoreForm}>
          <Form.Item
            name="leader_score"
            label="Điểm lãnh đạo chấm (0 – 100)"
            rules={[{ required: true, message: 'Vui lòng nhập điểm' }]}
          >
            <InputNumber min={0} max={100} step={0.5} style={{ width: '100%' }} size="large" />
          </Form.Item>
          <p style={{ color: '#64748b', fontSize: 13 }}>
            Điểm cuối = 30% tự chấm + 70% lãnh đạo chấm (nếu cán bộ đã tự chấm).
          </p>
        </Form>
      </Modal>
    </Space>
  );
}
