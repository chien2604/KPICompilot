import { Button, Card, Form, Input, Modal, Select, Space, Typography, message } from 'antd';
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons';
import { useEffect, useState } from 'react';
import { taskApi } from '../api/taskApi';
import { userApi } from '../api/userApi';
import TaskTable from '../components/TaskTable';

export default function TasksPage() {
  const [tasks, setTasks] = useState([]);
  const [users, setUsers] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [open, setOpen] = useState(false);
  const [form] = Form.useForm();
  const load = () => taskApi.list().then(setTasks);
  useEffect(() => {
    load();
    Promise.all([userApi.list(), userApi.departments()]).then(([userRows, departmentRows]) => {
      setUsers(userRows);
      setDepartments(departmentRows);
    });
  }, []);

  const assignedUserOptions = [
    ...departments.map((department) => ({
      label: department.name,
      options: users
        .filter((user) => user.department_id === department.id)
        .map((user) => ({ value: user.id, label: `${user.full_name} - ${user.position_title}` })),
    })).filter((group) => group.options.length > 0),
    {
      label: 'Chưa phân phòng',
      options: users
        .filter((user) => !departments.some((department) => department.id === user.department_id))
        .map((user) => ({ value: user.id, label: `${user.full_name} - ${user.position_title}` })),
    },
  ].filter((group) => group.options.length > 0);

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
      <Card>
        <TaskTable data={tasks} />
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
