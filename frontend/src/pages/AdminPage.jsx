import {
  CheckCircleOutlined,
  EditOutlined,
  KeyOutlined,
  LockOutlined,
  ReloadOutlined,
  SearchOutlined,
  UnlockOutlined,
} from "@ant-design/icons";
import {
  Avatar,
  Button,
  Card,
  Col,
  Drawer,
  Form,
  Input,
  InputNumber,
  Modal,
  Row,
  Select,
  Space,
  Statistic,
  Table,
  Tag,
  Tooltip,
  Typography,
  message,
} from "antd";
import { useEffect, useMemo, useState } from "react";
import { adminApi } from "../api/adminApi";
import {
  kpiTemplateLabel,
  organizationRoleLabel,
  roleLabel,
} from "../utils/formatters";

const { Text, Title } = Typography;

const ROLE_OPTIONS = [
  { value: "user", label: "Người dùng" },
  { value: "admin", label: "Quản trị viên" },
];

/** Return commune unit options and omit the organization root. */
function departmentOptions(departments) {
  return departments
    .filter((department) =>
      ["LEADERSHIP", "UNIT"].includes(department.unit_type),
    )
    .map((department) => ({ label: department.name, value: department.id }));
}

/** Render the administrator account provisioning workspace. */
export default function AdminPage() {
  const [users, setUsers] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [positionTemplates, setPositionTemplates] = useState([]);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [searchText, setSearchText] = useState("");
  const [departmentFilter, setDepartmentFilter] = useState(null);
  const [selectedUser, setSelectedUser] = useState(null);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [passwordModalOpen, setPasswordModalOpen] = useState(false);
  const [editForm] = Form.useForm();
  const [passwordForm] = Form.useForm();

  /** Load personnel, organization unit, and permission template data. */
  const loadData = async () => {
    setLoading(true);
    try {
      const [userData, departmentData, templateData] = await Promise.all([
        adminApi.listUsers(),
        adminApi.listDepartments(),
        adminApi.listPositionTemplates(),
      ]);
      setUsers(userData);
      setDepartments(departmentData);
      setPositionTemplates(templateData);
    } catch (error) {
      message.error(
        error.response?.data?.detail || "Không thể tải dữ liệu quản trị.",
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const departmentOptionsList = useMemo(
    () => departmentOptions(departments),
    [departments],
  );
  const filteredUsers = useMemo(() => {
    const normalizedSearch = searchText.trim().toLocaleLowerCase("vi");
    return users.filter((user) => {
      const searchableText = [
        user.full_name,
        user.email,
        user.phone_number,
        user.position_title,
        user.department_name,
      ]
        .filter(Boolean)
        .join(" ")
        .toLocaleLowerCase("vi");
      const matchesSearch =
        !normalizedSearch || searchableText.includes(normalizedSearch);
      const matchesDepartment =
        !departmentFilter || user.department_id === departmentFilter;
      return matchesSearch && matchesDepartment;
    });
  }, [departmentFilter, searchText, users]);

  const personnelUsers = users.filter((user) => !user.is_admin);
  const statistics = {
    total: personnelUsers.length,
    configured: personnelUsers.filter((user) => user.account_configured).length,
    active: personnelUsers.filter((user) => user.is_active).length,
    inactive: personnelUsers.filter((user) => !user.is_active).length,
  };

  /** Open a personnel profile and account configuration form. */
  const openEditModal = (user) => {
    setSelectedUser(user);
    editForm.setFieldsValue({ ...user, password: undefined });
    setEditModalOpen(true);
  };

  /** Save account credentials, permission template, and personnel fields. */
  const saveUser = async (values) => {
    setSubmitting(true);
    try {
      const payload = { ...values };
      if (!payload.password) delete payload.password;
      await adminApi.updateUser(selectedUser.id, payload);
      message.success(`Đã cập nhật hồ sơ ${selectedUser.full_name}.`);
      setEditModalOpen(false);
      await loadData();
    } catch (error) {
      message.error(
        error.response?.data?.detail || "Không thể cập nhật hồ sơ.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  /** Open the password reset form for an existing account. */
  const openPasswordModal = (user) => {
    setSelectedUser(user);
    passwordForm.resetFields();
    setPasswordModalOpen(true);
  };

  /** Replace the selected account password. */
  const resetPassword = async (values) => {
    setSubmitting(true);
    try {
      await adminApi.resetPassword(selectedUser.id, values.new_password);
      message.success(`Đã đặt lại mật khẩu cho ${selectedUser.full_name}.`);
      setPasswordModalOpen(false);
      await loadData();
    } catch (error) {
      message.error(
        error.response?.data?.detail || "Không thể đặt lại mật khẩu.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  /** Activate or deactivate a configured account. */
  const toggleAccount = async (user) => {
    try {
      if (user.is_active) await adminApi.deactivateUser(user.id);
      else await adminApi.activateUser(user.id);
      message.success(
        user.is_active ? "Đã khóa tài khoản." : "Đã kích hoạt tài khoản.",
      );
      await loadData();
    } catch (error) {
      message.error(
        error.response?.data?.detail ||
          "Không thể thay đổi trạng thái tài khoản.",
      );
    }
  };

  const columns = [
    {
      title: "Cán bộ",
      key: "user",
      width: 250,
      render: (_, user) => (
        <Space>
          <Avatar src={user.avatar_url}>{user.full_name?.[0]}</Avatar>
          <div>
            <div style={{ fontWeight: 600 }}>{user.full_name}</div>
            <Text type="secondary">{user.email || "Chưa cấu hình email"}</Text>
          </div>
        </Space>
      ),
    },
    { title: "Đơn vị", dataIndex: "department_name", width: 190 },
    {
      title: "Chức vụ",
      dataIndex: "position_title",
      width: 210,
      render: (value, user) => (
        <div>
          <div>{value || "Chưa cập nhật"}</div>
          <Text type="secondary">
            {kpiTemplateLabel[user.kpi_role_template] || user.kpi_role_template}
          </Text>
        </div>
      ),
    },
    {
      title: "Vai trò",
      dataIndex: "organization_role",
      width: 190,
      render: (value, user) => (
        <Tag color={user.is_admin ? "red" : "blue"}>
          {user.is_admin
            ? roleLabel.admin
            : organizationRoleLabel[value] || value}
        </Tag>
      ),
    },
    {
      title: "Tài khoản",
      key: "account",
      width: 150,
      render: (_, user) => (
        <Space direction="vertical" size={2}>
          <Tag color={user.account_configured ? "green" : "default"}>
            {user.account_configured ? "Đã cấu hình" : "Chưa cấu hình"}
          </Tag>
          <Tag
            color={user.is_active ? "processing" : "default"}
            icon={user.is_active ? <CheckCircleOutlined /> : null}
          >
            {user.is_active ? "Đang hoạt động" : "Chưa kích hoạt"}
          </Tag>
        </Space>
      ),
    },
    {
      title: "Thao tác",
      key: "actions",
      width: 140,
      fixed: "right",
      render: (_, user) => (
        <Space size={4}>
          <Tooltip title="Cấu hình hồ sơ và tài khoản">
            <Button
              type="primary"
              icon={<EditOutlined />}
              disabled={user.is_admin}
              onClick={() => openEditModal(user)}
            />
          </Tooltip>
          <Tooltip title="Đặt lại mật khẩu">
            <Button
              icon={<KeyOutlined />}
              disabled={!user.email}
              onClick={() => openPasswordModal(user)}
            />
          </Tooltip>
          <Tooltip
            title={user.is_active ? "Khóa tài khoản" : "Kích hoạt tài khoản"}
          >
            <Button
              danger={user.is_active}
              disabled={user.is_admin}
              icon={user.is_active ? <LockOutlined /> : <UnlockOutlined />}
              onClick={() => toggleAccount(user)}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  return (
    <div className="page">
      <div className="page-title-row">
        <div>
          <Title level={3} style={{ margin: 0 }}>
            Quản trị tài khoản
          </Title>
          <Text type="secondary">
            Cấu hình đăng nhập trên danh sách cán bộ nhập từ XLS
          </Text>
        </div>
        <Button icon={<ReloadOutlined />} onClick={loadData} loading={loading}>
          Tải lại
        </Button>
      </div>

      <Row gutter={[16, 16]} style={{ margin: "20px 0" }}>
        <Col xs={12} lg={6}>
          <Card className="admin-stat-card admin-stat-card--red">
            <Statistic title="Tổng hồ sơ" value={statistics.total} />
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card className="admin-stat-card admin-stat-card--blue">
            <Statistic title="Đã cấu hình" value={statistics.configured} />
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card className="admin-stat-card admin-stat-card--green">
            <Statistic title="Đang hoạt động" value={statistics.active} />
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card className="admin-stat-card admin-stat-card--orange">
            <Statistic title="Chưa kích hoạt" value={statistics.inactive} />
          </Card>
        </Col>
      </Row>

      <Card className="admin-table-card">
        <Space wrap className="admin-filter-bar">
          <Input
            prefix={<SearchOutlined />}
            placeholder="Tìm theo tên, email, số điện thoại, chức vụ"
            value={searchText}
            onChange={(event) => setSearchText(event.target.value)}
            allowClear
            style={{ width: 360 }}
          />
          <Select
            placeholder="Lọc theo đơn vị"
            options={departmentOptionsList}
            value={departmentFilter}
            onChange={setDepartmentFilter}
            allowClear
            style={{ width: 220 }}
          />
        </Space>
        <Table
          dataSource={filteredUsers}
          columns={columns}
          rowKey="id"
          loading={loading}
          scroll={{ x: 1050 }}
          pagination={{ pageSize: 15 }}
        />
      </Card>

      <Drawer
        title={`Cấu hình hồ sơ - ${selectedUser?.full_name || ""}`}
        open={editModalOpen}
        onClose={() => setEditModalOpen(false)}
        width={620}
        destroyOnHidden
      >
        <Form form={editForm} layout="vertical" onFinish={saveUser}>
          <Row gutter={16}>
            <Col xs={24} md={12}>
              <Form.Item
                name="email"
                label="Email đăng nhập"
                rules={[{ type: "email", message: "Email không hợp lệ" }]}
              >
                <Input placeholder="canbo@nghialam.gov.vn" />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item
                name="password"
                label={
                  selectedUser?.account_configured
                    ? "Mật khẩu mới (không bắt buộc)"
                    : "Mật khẩu khởi tạo"
                }
                rules={[
                  { min: 8, message: "Mật khẩu phải có tối thiểu 8 ký tự" },
                ]}
              >
                <Input.Password placeholder="Tối thiểu 8 ký tự" />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item
                name="role"
                label="Vai trò hệ thống"
                rules={[{ required: true }]}
              >
                <Select options={ROLE_OPTIONS} />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item
                name="is_active"
                label="Trạng thái tài khoản"
                rules={[{ required: true }]}
              >
                <Select
                  options={[
                    { value: true, label: "Kích hoạt" },
                    { value: false, label: "Chưa kích hoạt" },
                  ]}
                />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item
                name="department_id"
                label="Đơn vị công tác"
                rules={[{ required: true }]}
              >
                <Select
                  options={departmentOptionsList}
                  showSearch
                  optionFilterProp="label"
                />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item
                name="kpi_role_template"
                label="Nhóm chức vụ và phân quyền"
                rules={[{ required: true }]}
              >
                <Select
                  options={positionTemplates.map((template) => ({
                    value: template.code,
                    label: template.name,
                  }))}
                />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item
                name="position_title"
                label="Chức vụ ghi trong hồ sơ"
                rules={[{ required: true }]}
              >
                <Input />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item
                name="phone_number"
                label="Số điện thoại"
                rules={[
                  {
                    pattern: /^\d{10}$/,
                    message: "Số điện thoại gồm 10 chữ số",
                  },
                ]}
              >
                <Input />
              </Form.Item>
            </Col>
            <Col xs={24} md={8}>
              <Form.Item name="birth_year" label="Năm sinh">
                <InputNumber min={1900} max={2100} style={{ width: "100%" }} />
              </Form.Item>
            </Col>
            <Col xs={24} md={8}>
              <Form.Item name="ethnicity" label="Dân tộc">
                <Input />
              </Form.Item>
            </Col>
            <Col xs={24} md={8}>
              <Form.Item name="party_joined_date" label="Ngày vào Đảng">
                <Input />
              </Form.Item>
            </Col>
            <Col xs={24} md={8}>
              <Form.Item name="general_education" label="Giáo dục phổ thông">
                <Input />
              </Form.Item>
            </Col>
            <Col xs={24} md={8}>
              <Form.Item name="professional_qualification" label="Chuyên môn">
                <Input />
              </Form.Item>
            </Col>
            <Col xs={24} md={8}>
              <Form.Item name="political_theory" label="Lý luận chính trị">
                <Input />
              </Form.Item>
            </Col>
          </Row>
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
            <Button onClick={() => setEditModalOpen(false)}>Hủy</Button>
            <Button type="primary" htmlType="submit" loading={submitting}>
              Lưu cấu hình
            </Button>
          </div>
        </Form>
      </Drawer>

      <Modal
        title={`Đặt lại mật khẩu - ${selectedUser?.full_name || ""}`}
        open={passwordModalOpen}
        onCancel={() => setPasswordModalOpen(false)}
        footer={null}
        destroyOnHidden
      >
        <Form form={passwordForm} layout="vertical" onFinish={resetPassword}>
          <Form.Item
            name="new_password"
            label="Mật khẩu mới"
            rules={[
              {
                required: true,
                min: 8,
                message: "Nhập mật khẩu tối thiểu 8 ký tự",
              },
            ]}
          >
            <Input.Password />
          </Form.Item>
          <Form.Item
            name="confirm_password"
            label="Xác nhận mật khẩu"
            dependencies={["new_password"]}
            rules={[
              { required: true },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  return !value || getFieldValue("new_password") === value
                    ? Promise.resolve()
                    : Promise.reject(new Error("Mật khẩu xác nhận không khớp"));
                },
              }),
            ]}
          >
            <Input.Password />
          </Form.Item>
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
            <Button onClick={() => setPasswordModalOpen(false)}>Hủy</Button>
            <Button type="primary" htmlType="submit" loading={submitting}>
              Đặt lại mật khẩu
            </Button>
          </div>
        </Form>
      </Modal>
    </div>
  );
}
