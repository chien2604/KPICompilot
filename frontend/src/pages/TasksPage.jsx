import { Button, Card, DatePicker, Form, Input, Modal, Select, Space, Tag, Typography, message } from 'antd';
import { FilterOutlined, PlusOutlined, ReloadOutlined } from '@ant-design/icons';
import { useEffect, useMemo, useState } from 'react';
import dayjs from 'dayjs';
import { taskApi } from '../api/taskApi';
import { userApi } from '../api/userApi';
import TaskTable from '../components/TaskTable';

const STATUS_OPTIONS = [
  { value: 'COMPLETED',   label: 'Hoàn thành',      color: '#16a34a' },
  { value: 'IN_PROGRESS', label: 'Đang thực hiện',  color: '#f59e0b' },
  { value: 'NOT_STARTED', label: 'Chưa bắt đầu',   color: '#64748b' },
  { value: 'OVERDUE',     label: 'Quá hạn',         color: '#dc2626' },
];

export default function TasksPage() {
  const [tasks, setTasks]             = useState([]);
  const [users, setUsers]             = useState([]);
  const [departments, setDepartments] = useState([]);
  const [open, setOpen]               = useState(false);
  const [form]                        = Form.useForm();

  // Bộ lọc
  const [filterStatus,    setFilterStatus]    = useState(null);
  const [filterDateRange, setFilterDateRange] = useState(null); // [dayjs, dayjs]

  const load = () => taskApi.list().then(setTasks);

  useEffect(() => {
    load();
    Promise.all([userApi.list(), userApi.departments()]).then(([u, d]) => {
      setUsers(u);
      setDepartments(d);
    });
  }, []);

  // Lọc client-side
  const filtered = useMemo(() => {
    let result = tasks;
    if (filterStatus) {
      result = result.filter((t) => t.status === filterStatus);
    }
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
  }, [tasks, filterStatus, filterDateRange]);

  const hasFilter = filterStatus || filterDateRange;

  const clearFilters = () => {
    setFilterStatus(null);
    setFilterDateRange(null);
  };

  const assignedUserOptions = [
    ...departments.map((dep) => ({
      label: dep.name,
      options: users
        .filter((u) => u.department_id === dep.id)
        .map((u) => ({ value: u.id, label: `${u.full_name} - ${u.position_title}` })),
    })).filter((g) => g.options.length > 0),
    {
      label: 'Chưa phân phòng',
      options: users
        .filter((u) => !departments.some((d) => d.id === u.department_id))
        .map((u) => ({ value: u.id, label: `${u.full_name} - ${u.position_title}` })),
    },
  ].filter((g) => g.options.length > 0);

  const createTask = async () => {
    const values = await form.validateFields();
    await taskApi.create({ ...values, assigned_user_ids: values.assigned_user_ids || [] });
    message.success('Đã tạo nhiệm vụ');
    setOpen(false);
    form.resetFields();
    load();
  };

  return (
    <Space direction="vertical" size={18} className="page">
      <div className="page-title-row">
        <Typography.Title level={3}>Quản lý Công việc</Typography.Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={load}>Tải lại</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setOpen(true)}>Tạo nhiệm vụ</Button>
        </Space>
      </div>

      {/* Bộ lọc */}
      <Card size="small" className="task-filter-bar">
        <div className="task-filter-bar__inner">
          <FilterOutlined style={{ color: '#64748b', fontSize: 16 }} />
          <span className="task-filter-bar__title">Lọc theo:</span>

          {/* Lọc trạng thái */}
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
                    cursor: 'pointer',
                    fontSize: 16,
                    padding: '4px 14px',
                    borderRadius: 20,
                    userSelect: 'none',
                  }}
                  onClick={() => setFilterStatus(filterStatus === opt.value ? null : opt.value)}
                >
                  {opt.label}
                  {filterStatus === opt.value && ' ✕'}
                </Tag>
              ))}
            </Space>
          </div>

          {/* Lọc hạn xử lý */}
          <div className="task-filter-bar__group">
            <span className="task-filter-bar__label">Hạn xử lý</span>
            <DatePicker.RangePicker
              value={filterDateRange}
              onChange={setFilterDateRange}
              format="DD/MM/YYYY"
              placeholder={['Từ ngày', 'Đến ngày']}
              style={{ fontSize: 16 }}
            />
          </div>

          {/* Clear */}
          {hasFilter && (
            <Button size="small" danger type="primary" onClick={clearFilters} style={{ marginLeft: 'auto' }}>
              Xóa bộ lọc
            </Button>
          )}
        </div>

        {/* Hiển thị số kết quả */}
        {hasFilter && (
          <div className="task-filter-bar__result">
            Hiển thị <b>{filtered.length}</b> / {tasks.length} nhiệm vụ
          </div>
        )}
      </Card>

      <Card>
        <TaskTable data={filtered} />
      </Card>

      <Modal title="Tạo nhiệm vụ" open={open} onOk={createTask} onCancel={() => setOpen(false)}>
        <Form layout="vertical" form={form} initialValues={{ document_type: 'C', status: 'NOT_STARTED', priority: 'MEDIUM' }}>
          <Form.Item name="title" label="Tên nhiệm vụ" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="description" label="Mô tả"><Input.TextArea rows={3} /></Form.Item>
          <Form.Item name="document_type" label="Nhóm văn bản"><Select options={['A', 'B', 'C', 'D'].map((v) => ({ value: v, label: v }))} /></Form.Item>
          <Form.Item name="assigned_user_ids" label="Giao cho">
            <Select mode="multiple" showSearch optionFilterProp="label" options={assignedUserOptions} />
          </Form.Item>
        </Form>
      </Modal>
    </Space>
  );
}
