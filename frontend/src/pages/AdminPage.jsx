import {
  CheckCircleOutlined,
  EditOutlined,
  KeyOutlined,
  LockOutlined,
  PlusOutlined,
  ReloadOutlined,
  SearchOutlined,
  StopOutlined,
  UnlockOutlined,
  UserAddOutlined,
  ApiOutlined,
} from '@ant-design/icons';
import {
  Avatar,
  Badge,
  Button,
  Col,
  Form,
  Input,
  Modal,
  Row,
  Select,
  Space,
  Table,
  Tag,
  Tooltip,
  Typography,
  message,
  Statistic,
  Card,
  Divider,
} from 'antd';
import { useEffect, useState } from 'react';
import { adminApi } from '../api/adminApi';

const { Title, Text } = Typography;
const { Option } = Select;

const ROLE_OPTIONS = [
  { value: 'staff', label: 'Nhân viên (Staff)' },
  { value: 'admin', label: 'Quản trị viên (Admin)' },
];

// Cấp bậc (chức vụ) — user chỉ chọn cái này
// Backend tự xử lí kpi_role_template dựa vào đây
const POSITION_OPTIONS = [
  // Cấp sở (level 1-2)
  { value: 'Giám đốc', label: 'Giám đốc', group: 'Lãnh đạo Sở' },
  { value: 'Phó Giám đốc', label: 'Phó Giám đốc', group: 'Lãnh đạo Sở' },
  // Cấp phòng (level 3-4)
  { value: 'Chánh Văn phòng', label: 'Chánh Văn phòng', group: 'Lãnh đạo phòng' },
  { value: 'Phó Chánh Văn phòng', label: 'Phó Chánh Văn phòng', group: 'Lãnh đạo phòng' },
  { value: 'Trưởng phòng', label: 'Trưởng phòng', group: 'Lãnh đạo phòng' },
  { value: 'Trưởng phòng Chính sách Dân tộc', label: 'Trưởng phòng Chính sách Dân tộc', group: 'Lãnh đạo phòng' },
  { value: 'Phó Trưởng phòng', label: 'Phó Trưởng phòng', group: 'Lãnh đạo phòng' },
  // Công chức (level 5)
  { value: 'Chuyên viên', label: 'Chuyên viên', group: 'Công chức' },
  { value: 'Kế toán', label: 'Kế toán', group: 'Công chức' },
  { value: 'Văn thư', label: 'Văn thư', group: 'Công chức' },
  { value: 'Nhân viên lái xe', label: 'Nhân viên lái xe', group: 'Công chức' },
];

// Auto-map chức vụ → kpi_role_template (backend dùng)
function getKpiTemplate(positionTitle) {
  if (!positionTitle) return 'CONG_CHUC_KHONG_CHUC_VU';
  const p = positionTitle.toLowerCase();
  if (p.includes('giám đốc')) return 'BAN_GIAM_DOC';
  if (p.includes('trưởng phòng') || p.includes('phó trưởng') || p.includes('chánh văn phòng') || p.includes('phó chánh')) return 'TRUONG_PHO_PHONG';
  return 'CONG_CHUC_KHONG_CHUC_VU';
}

const LEVEL_LABEL = {
  0: { label: 'Admin', color: 'red' },
  1: { label: 'Giám đốc', color: 'purple' },
  2: { label: 'Phó GĐ', color: 'blue' },
  3: { label: 'Trưởng phòng', color: 'cyan' },
  4: { label: 'Phó phòng', color: 'green' },
  5: { label: 'Chuyên viên', color: 'gold' },
};

export default function AdminPage() {
  const [users, setUsers] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');

  // Modal states
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [resetPwdModalOpen, setResetPwdModalOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const [editForm] = Form.useForm();
  const [createForm] = Form.useForm();
  const [resetPwdForm] = Form.useForm();

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const data = await adminApi.listUsers();
      setUsers(data);
    } catch {
      message.error('Không thể tải danh sách người dùng.');
    } finally {
      setLoading(false);
    }
  };

  const fetchDepartments = async () => {
    try {
      const data = await adminApi.listDepartments();
      setDepartments(data);
    } catch {
      /* ignore */
    }
  };

  useEffect(() => {
    fetchUsers();
    fetchDepartments();
  }, []);

  // Thống kê
  const stats = {
    total: users.length,
    active: users.filter((u) => u.is_active).length,
    admins: users.filter((u) => u.is_admin).length,
    inactive: users.filter((u) => !u.is_active).length,
  };

  // Filter theo search
  const filteredUsers = users.filter(
    (u) =>
      u.full_name?.toLowerCase().includes(searchText.toLowerCase()) ||
      u.email?.toLowerCase().includes(searchText.toLowerCase()) ||
      u.position_title?.toLowerCase().includes(searchText.toLowerCase()) ||
      u.department_name?.toLowerCase().includes(searchText.toLowerCase()),
  );

  // Handlers
  const openEditModal = (user) => {
    setSelectedUser(user);
    editForm.setFieldsValue({
      role: user.role,
      position_title: user.position_title,
      department_id: user.department_id,
      is_active: user.is_active,
    });
    setEditModalOpen(true);
  };

  const openResetPwdModal = (user) => {
    setSelectedUser(user);
    resetPwdForm.resetFields();
    setResetPwdModalOpen(true);
  };

  const handleEditSubmit = async (values) => {
    setSubmitting(true);
    try {
      // Tự động gán kpi_role_template dựa theo chức vụ
      const payload = { ...values, kpi_role_template: getKpiTemplate(values.position_title) };
      await adminApi.updateUserRole(selectedUser.id, payload);
      message.success(`Đã cập nhật quyền cho ${selectedUser.full_name}`);
      setEditModalOpen(false);
      fetchUsers();
    } catch (err) {
      message.error(err.response?.data?.detail || 'Cập nhật thất bại.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleCreateSubmit = async (values) => {
    setSubmitting(true);
    try {
      // Tự động gán kpi_role_template dựa theo chức vụ
      const payload = { ...values, kpi_role_template: getKpiTemplate(values.position_title) };
      await adminApi.createUser(payload);
      message.success(`Đã tạo tài khoản cho ${values.full_name}`);
      setCreateModalOpen(false);
      createForm.resetFields();
      fetchUsers();
    } catch (err) {
      message.error(err.response?.data?.detail || 'Tạo tài khoản thất bại.');
    } finally {
      setSubmitting(false);
    }
  };
  const handleResetPassword = async (values) => {
    setSubmitting(true);
    try {
      await adminApi.resetPassword(selectedUser.id, values.new_password);
      message.success(`Đã đặt lại mật khẩu cho ${selectedUser.full_name}`);
      setResetPwdModalOpen(false);
    } catch (err) {
      message.error(err.response?.data?.detail || 'Đặt lại mật khẩu thất bại.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleToggleActive = async (user) => {
    try {
      if (user.is_active) {
        await adminApi.deactivateUser(user.id);
        message.success(`Đã vô hiệu hoá tài khoản ${user.full_name}`);
      } else {
        await adminApi.activateUser(user.id);
        message.success(`Đã kích hoạt tài khoản ${user.full_name}`);
      }
      fetchUsers();
    } catch (err) {
      message.error(err.response?.data?.detail || 'Thao tác thất bại.');
    }
  };

  const columns = [
    {
      title: 'Người dùng',
      key: 'user',
      fixed: 'left',
      width: 220,
      render: (_, record) => (
        <Space>
          <Badge dot status={record.is_active ? 'success' : 'error'} offset={[-2, 32]}>
            <Avatar src={record.avatar_url} size={38} style={{ background: record.is_admin ? '#ff4d4f' : '#6366f1', flexShrink: 0 }}>
              {record.full_name?.[0]}
            </Avatar>
          </Badge>
          <div>
            <div style={{ fontWeight: 600, fontSize: 13 }}>{record.full_name}</div>
            <div style={{ fontSize: 11, color: '#999' }}>{record.email}</div>
          </div>
        </Space>
      ),
    },
    {
      title: 'Chức vụ',
      dataIndex: 'position_title',
      key: 'position_title',
      width: 160,
      render: (v) => v || <Text type="secondary">—</Text>,
    },
    {
      title: 'Phòng ban',
      dataIndex: 'department_name',
      key: 'department_name',
      width: 160,
      render: (v) => v || <Text type="secondary">Không có</Text>,
    },
    {
      title: 'Cấp',
      key: 'cap',
      width: 150,
      render: (_, record) => {
        if (record.is_admin) {
          return <Tag color="geekblue" style={{ borderColor: '#1d39c4' }}>Admin</Tag>;
        }
        const posOpt = POSITION_OPTIONS.find(p => p.value === record.position_title);
        const capLabel = posOpt ? posOpt.group : 'Công chức';
        
        let color = 'cyan'; // Công chức
        if (capLabel === 'Lãnh đạo Sở') color = 'blue';
        else if (capLabel === 'Lãnh đạo phòng') color = 'processing';
        
        return <Tag color={color}>{capLabel}</Tag>;
      },
    },
    {
      title: 'Trạng thái',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 110,
      render: (active) =>
        active ? (
          <Tag color="blue" icon={<CheckCircleOutlined />}>Hoạt động</Tag>
        ) : (
          <Tag color="default" icon={<StopOutlined />}>Đã khoá</Tag>
        ),
    },
    {
      title: 'Thao tác',
      key: 'actions',
      fixed: 'right',
      width: 140,
      render: (_, record) => (
        <Space size={4}>
          <Tooltip title="Phân quyền">
            <Button
              id={`edit-role-btn-${record.id}`}
              size="small"
              type="primary"
              icon={<EditOutlined />}
              onClick={() => openEditModal(record)}
            />
          </Tooltip>
          <Tooltip title="Đặt lại mật khẩu">
            <Button
              id={`reset-pwd-btn-${record.id}`}
              size="small"
              icon={<KeyOutlined />}
              onClick={() => openResetPwdModal(record)}
            />
          </Tooltip>
          <Tooltip title={record.is_active ? 'Vô hiệu hoá' : 'Kích hoạt lại'}>
            <Button
              id={`toggle-active-btn-${record.id}`}
              size="small"
              danger={record.is_active}
              type={record.is_active ? 'default' : 'primary'}
              icon={record.is_active ? <LockOutlined /> : <UnlockOutlined />}
              onClick={() => handleToggleActive(record)}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px', maxWidth: 1200, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24 }}>
        <div>
          <Title level={3} style={{ margin: 0, color: '#002c8c', display: 'flex', alignItems: 'center', gap: 8 }}>
            <ApiOutlined style={{ color: '#1677ff' }} /> Quản trị hệ thống
          </Title>
          <Text type="secondary" style={{ marginTop: 4, display: 'block' }}>Quản lý tài khoản và phân quyền hệ thống</Text>
        </div>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchUsers} loading={loading}>
            Làm mới
          </Button>
          <Button
            id="create-user-btn"
            type="primary"
            icon={<UserAddOutlined />}
            onClick={() => {
              createForm.resetFields();
              setCreateModalOpen(true);
            }}
            style={{ background: '#1677ff', borderColor: '#1677ff' }}
          >
            Thêm người dùng
          </Button>
        </Space>
      </div>

      {/* Thống kê */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card bordered={false} style={{ background: 'linear-gradient(135deg, #0958d9 0%, #003eb3 100%)', borderRadius: 12, boxShadow: '0 4px 12px rgba(9, 88, 217, 0.15)' }}>
            <Statistic title={<span style={{ color: 'rgba(255,255,255,0.7)' }}>Tổng người dùng</span>} value={stats.total} valueStyle={{ color: '#fff', fontWeight: 700 }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card bordered={false} style={{ background: 'linear-gradient(135deg, #13c2c2 0%, #08979c 100%)', borderRadius: 12, boxShadow: '0 4px 12px rgba(19, 194, 194, 0.15)' }}>
            <Statistic title={<span style={{ color: 'rgba(255,255,255,0.7)' }}>Đang hoạt động</span>} value={stats.active} valueStyle={{ color: '#fff', fontWeight: 700 }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card bordered={false} style={{ background: 'linear-gradient(135deg, #2f54eb 0%, #1d39c4 100%)', borderRadius: 12, boxShadow: '0 4px 12px rgba(47, 84, 235, 0.15)' }}>
            <Statistic title={<span style={{ color: 'rgba(255,255,255,0.7)' }}>Quản trị viên</span>} value={stats.admins} valueStyle={{ color: '#fff', fontWeight: 700 }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card bordered={false} style={{ background: 'linear-gradient(135deg, #595959 0%, #434343 100%)', borderRadius: 12, boxShadow: '0 4px 12px rgba(89, 89, 89, 0.15)' }}>
            <Statistic title={<span style={{ color: 'rgba(255,255,255,0.7)' }}>Đã khoá</span>} value={stats.inactive} valueStyle={{ color: '#fff', fontWeight: 700 }} />
          </Card>
        </Col>
      </Row>

      {/* Search + Table */}
      <div style={{ background: '#fff', borderRadius: 12, padding: 20, boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}>
        <div style={{ marginBottom: 16 }}>
          <Input
            id="admin-search-input"
            placeholder="Tìm kiếm theo tên, email, chức vụ, phòng ban..."
            prefix={<SearchOutlined style={{ color: '#bbb' }} />}
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            style={{ maxWidth: 400, borderRadius: 8 }}
            allowClear
          />
        </div>
        <Table
          id="admin-users-table"
          dataSource={filteredUsers}
          columns={columns}
          rowKey="id"
          loading={loading}
          size="small"
          scroll={{ x: 900 }}
          pagination={{ pageSize: 15, showSizeChanger: false }}
          rowClassName={(record) => (!record.is_active ? 'admin-row-inactive' : '')}
        />
      </div>

      {/* Modal Phân quyền */}
      <Modal
        title={
          <Space>
            <EditOutlined style={{ color: '#6366f1' }} />
            <span>Phân quyền — {selectedUser?.full_name}</span>
          </Space>
        }
        open={editModalOpen}
        onCancel={() => setEditModalOpen(false)}
        footer={null}
        destroyOnClose
        width={520}
      >
        <Form form={editForm} layout="vertical" onFinish={handleEditSubmit} style={{ marginTop: 16 }}>
          <Form.Item name="role" label="Loại tài khoản" rules={[{ required: true }]}>
            <Select id="edit-role-select" placeholder="Chọn loại tài khoản">
              {ROLE_OPTIONS.map((o) => (
                <Option key={o.value} value={o.value}>{o.label}</Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item name="position_title" label="Chức vụ (quyết định Cấp bậc & Nhóm KPI)">
            <Select id="edit-position-select" placeholder="Chọn chức vụ" showSearch allowClear>
              {POSITION_OPTIONS.reduce((groups, item) => {
                const group = groups.find(g => g.label === item.group);
                if (group) group.options.push(item);
                else groups.push({ label: item.group, options: [item] });
                return groups;
              }, []).map(group => (
                <Select.OptGroup key={group.label} label={group.label}>
                  {group.options.map(opt => (
                    <Option key={opt.value} value={opt.value}>{opt.label}</Option>
                  ))}
                </Select.OptGroup>
              ))}
            </Select>
          </Form.Item>

          <Form.Item name="department_id" label="Phòng ban">
            <Select id="edit-dept-select" placeholder="Chọn phòng ban" allowClear>
              {departments.map((d) => (
                <Option key={d.id} value={d.id}>{d.name}</Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item name="is_active" label="Trạng thái tài khoản">
            <Select id="edit-active-select">
              <Option value={true}>✅ Đang hoạt động</Option>
              <Option value={false}>🔒 Vô hiệu hoá</Option>
            </Select>
          </Form.Item>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 8 }}>
            <Button onClick={() => setEditModalOpen(false)}>Huỷ</Button>
            <Button type="primary" htmlType="submit" loading={submitting} style={{ background: '#6366f1' }}>
              Lưu thay đổi
            </Button>
          </div>
        </Form>
      </Modal>

      {/* Modal Tạo người dùng mới */}
      <Modal
        title={
          <Space>
            <UserAddOutlined style={{ color: '#6366f1' }} />
            <span>Thêm người dùng mới</span>
          </Space>
        }
        open={createModalOpen}
        onCancel={() => setCreateModalOpen(false)}
        footer={null}
        destroyOnClose
        width={580}
      >
        <Form form={createForm} layout="vertical" onFinish={handleCreateSubmit} style={{ marginTop: 16 }}>
          <Row gutter={12}>
            <Col span={14}>
              <Form.Item
                name="full_name"
                label="Họ và tên"
                rules={[{ required: true, message: 'Vui lòng nhập họ tên' }]}
              >
                <Input id="create-fullname-input" placeholder="Nguyễn Văn A" />
              </Form.Item>
            </Col>
            <Col span={10}>
              <Form.Item name="role" label="Loại tài khoản" initialValue="staff">
                <Select id="create-role-select">
                  {ROLE_OPTIONS.map((o) => (
                    <Option key={o.value} value={o.value}>{o.label}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="email"
            label="Email đăng nhập"
            rules={[
              { required: true, message: 'Vui lòng nhập email' },
              { type: 'email', message: 'Email không hợp lệ' },
            ]}
          >
            <Input id="create-email-input" placeholder="example@gov.vn" />
          </Form.Item>

          <Form.Item
            name="password"
            label="Mật khẩu khởi tạo"
            rules={[
              { required: true, message: 'Vui lòng nhập mật khẩu' },
              { min: 6, message: 'Mật khẩu phải từ 6 ký tự trở lên' },
            ]}
          >
            <Input.Password id="create-password-input" placeholder="Tối thiểu 6 ký tự" />
          </Form.Item>

          <Divider style={{ margin: '8px 0 16px' }}>Thông tin công việc</Divider>

          <Form.Item name="position_title" label="Chức vụ (quyết định Cấp bậc & Nhóm KPI)">
            <Select id="create-position-select" placeholder="Chọn chức vụ" showSearch allowClear>
              {POSITION_OPTIONS.reduce((groups, item) => {
                const group = groups.find(g => g.label === item.group);
                if (group) group.options.push(item);
                else groups.push({ label: item.group, options: [item] });
                return groups;
              }, []).map(group => (
                <Select.OptGroup key={group.label} label={group.label}>
                  {group.options.map(opt => (
                    <Option key={opt.value} value={opt.value}>{opt.label}</Option>
                  ))}
                </Select.OptGroup>
              ))}
            </Select>
          </Form.Item>

          <Form.Item name="department_id" label="Phòng ban">
            <Select id="create-dept-select" placeholder="Chọn phòng ban" allowClear>
              {departments.map((d) => (
                <Option key={d.id} value={d.id}>{d.name}</Option>
              ))}
            </Select>
          </Form.Item>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 8 }}>
            <Button onClick={() => setCreateModalOpen(false)}>Huỷ</Button>
            <Button
              type="primary"
              htmlType="submit"
              loading={submitting}
              icon={<PlusOutlined />}
              style={{ background: '#6366f1' }}
            >
              Tạo tài khoản
            </Button>
          </div>
        </Form>
      </Modal>

      {/* Modal Đặt lại mật khẩu */}
      <Modal
        title={
          <Space>
            <KeyOutlined style={{ color: '#faad14' }} />
            <span>Đặt lại mật khẩu — {selectedUser?.full_name}</span>
          </Space>
        }
        open={resetPwdModalOpen}
        onCancel={() => setResetPwdModalOpen(false)}
        footer={null}
        destroyOnClose
        width={400}
      >
        <Form form={resetPwdForm} layout="vertical" onFinish={handleResetPassword} style={{ marginTop: 16 }}>
          <Form.Item
            name="new_password"
            label="Mật khẩu mới"
            rules={[
              { required: true, message: 'Vui lòng nhập mật khẩu mới' },
              { min: 6, message: 'Mật khẩu phải từ 6 ký tự trở lên' },
            ]}
          >
            <Input.Password id="reset-password-input" placeholder="Tối thiểu 6 ký tự" />
          </Form.Item>
          <Form.Item
            name="confirm_password"
            label="Xác nhận mật khẩu"
            dependencies={['new_password']}
            rules={[
              { required: true, message: 'Vui lòng xác nhận mật khẩu' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('new_password') === value) return Promise.resolve();
                  return Promise.reject(new Error('Mật khẩu xác nhận không khớp!'));
                },
              }),
            ]}
          >
            <Input.Password id="reset-confirm-password-input" placeholder="Nhập lại mật khẩu mới" />
          </Form.Item>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 8 }}>
            <Button onClick={() => setResetPwdModalOpen(false)}>Huỷ</Button>
            <Button type="primary" htmlType="submit" loading={submitting} danger>
              Đặt lại mật khẩu
            </Button>
          </div>
        </Form>
      </Modal>

      <style>{`
        .admin-row-inactive td {
          opacity: 0.5;
        }
      `}</style>
    </div>
  );
}
