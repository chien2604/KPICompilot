import {
  BarChartOutlined,
  FileDoneOutlined,
  FileSearchOutlined,
  HeatMapOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  ProfileOutlined,
  ProjectOutlined,
  RobotOutlined,
  SettingOutlined,
  TeamOutlined,
  UserOutlined,
  LockOutlined,
  BankOutlined,
  BellOutlined,
  CalendarOutlined,
  SearchOutlined,
} from "@ant-design/icons";
import {
  AutoComplete,
  Avatar,
  Badge,
  Button,
  Drawer,
  Grid,
  Layout,
  Menu,
  Tag,
  Tooltip,
  Modal,
  Input,
  Form,
  message,
} from "antd";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { useState } from "react";
import { useAuth } from "../contexts/AuthContext";
import { authApi } from "../api/authApi";
import FloatingCopilot from "../components/FloatingCopilot";

const { Header, Sider, Content } = Layout;

const WEEKDAYS = [
  "Chủ nhật",
  "Thứ hai",
  "Thứ ba",
  "Thứ tư",
  "Thứ năm",
  "Thứ sáu",
  "Thứ bảy",
];

const ORGANIZATION_ROLE_TAG = {
  ADMIN: { label: "Quản trị viên", color: "red" },
  LEADERSHIP: { label: "Lãnh đạo xã", color: "gold" },
  UNIT_HEAD: { label: "Trưởng đơn vị", color: "blue" },
  UNIT_DEPUTY: { label: "Phó trưởng đơn vị", color: "cyan" },
  SPECIALIST: { label: "Chuyên môn", color: "geekblue" },
  OUT_OF_SCOPE: { label: "Chưa áp dụng KPI", color: "default" },
};

/** Render authenticated navigation and the active application page. */
export default function AppLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout, isAdmin } = useAuth();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [isChangePasswordOpen, setIsChangePasswordOpen] = useState(false);
  const [pwdLoading, setPwdLoading] = useState(false);
  const [pwdForm] = Form.useForm();
  const screens = Grid.useBreakpoint();
  const isMobile = !screens.md;

  const now = new Date();
  const userId = user?.user_id;
  const levelInfo = ORGANIZATION_ROLE_TAG[
    user?.is_admin ? "ADMIN" : user?.organization_role
  ] || {
    label: "Cán bộ",
    color: "default",
  };

  /** Handle the logout. */
  const handleLogout = () => {
    logout();
    navigate("/login", { replace: true });
  };

  /** Navigate to a menu item and close the mobile navigation drawer. */
  const handleMenuClick = ({ key }) => {
    navigate(key);
    setMobileMenuOpen(false);
  };

  /** Handle the change password. */
  const handleChangePassword = async (values) => {
    setPwdLoading(true);
    try {
      await authApi.changePassword(values.oldPassword, values.newPassword);
      message.success("Đổi mật khẩu thành công!");
      setIsChangePasswordOpen(false);
      pwdForm.resetFields();
    } catch (error) {
      message.error(
        error.response?.data?.detail ||
          "Không thể đổi mật khẩu, vui lòng kiểm tra lại!",
      );
    } finally {
      setPwdLoading(false);
    }
  };

  const menuItems = [
    { key: "/dashboard", icon: <BarChartOutlined />, label: "Tổng quan" },
    ...(["LEADERSHIP", "UNIT_HEAD", "UNIT_DEPUTY"].includes(
      user?.organization_role,
    ) || isAdmin
      ? [{ key: "/heatmap", icon: <HeatMapOutlined />, label: "Heatmap" }]
      : []),
    { key: `/employees/${userId}`, icon: <TeamOutlined />, label: "Hồ sơ" },
    { key: "/tasks", icon: <ProjectOutlined />, label: "Công việc" },
    { key: "/evidences", icon: <FileSearchOutlined />, label: "Minh chứng" },
    { key: `/kpi/${userId}`, icon: <FileDoneOutlined />, label: "AI đánh giá" },
    { key: "/copilot", icon: <RobotOutlined />, label: "AI Copilot" },
    { key: "/reports", icon: <ProfileOutlined />, label: "Báo cáo" },
    ...(isAdmin
      ? [
          {
            key: "/admin",
            icon: <SettingOutlined />,
            label: "Quản trị",
            style: { color: "#ff4d4f", fontWeight: 600 },
          },
        ]
      : []),
  ];

  const searchOptions = menuItems.map((item) => ({
    value: item.key,
    label: item.label,
  }));
  const selectedMenuKey = location.pathname.startsWith("/employees/")
    ? `/employees/${userId}`
    : location.pathname.startsWith("/kpi/")
      ? `/kpi/${userId}`
      : location.pathname.startsWith("/evidences/")
        ? "/evidences"
        : location.pathname;

  return (
    <Layout className="app-shell">
      {!isMobile && (
        <Sider
          width={232}
          collapsedWidth={72}
          collapsed={collapsed}
          className="app-sidebar"
        >
          <div
            className={`sidebar-brand ${collapsed ? "sidebar-brand--collapsed" : ""}`}
          >
            <span className="sidebar-brand__seal">
              <BankOutlined />
            </span>
            {!collapsed && (
              <span className="sidebar-brand__copy">
                <strong>UBND XÃ NGHĨA LÂM</strong>
                <small>AI KPI Copilot · Tỉnh Nghệ An</small>
              </span>
            )}
          </div>
          <Menu
            theme="dark"
            mode="inline"
            selectedKeys={[selectedMenuKey]}
            items={menuItems}
            onClick={handleMenuClick}
            inlineCollapsed={collapsed}
          />
          <div className="sidebar-footer">
            <div
              className={`sidebar-account ${collapsed ? "sidebar-account--collapsed" : ""}`}
            >
              <Avatar
                size={34}
                src={user?.avatar_url}
                icon={<UserOutlined />}
                className="sidebar-account__avatar"
              />
              {!collapsed && (
                <span className="sidebar-account__copy">
                  <strong>{user?.full_name}</strong>
                  <small>{levelInfo.label}</small>
                </span>
              )}
            </div>
            <Tooltip
              title={collapsed ? "Mở rộng menu" : "Thu gọn menu"}
              placement="right"
            >
              <button
                className="sidebar-collapse-btn"
                onClick={() => setCollapsed((value) => !value)}
                type="button"
                aria-label={collapsed ? "Mở rộng menu" : "Thu gọn menu"}
              >
                {collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
                {!collapsed && <span>Thu gọn</span>}
              </button>
            </Tooltip>
          </div>
        </Sider>
      )}

      <Drawer
        title={
          <div className="mobile-drawer-brand">
            <span className="mobile-drawer-brand__seal">
              <BankOutlined />
            </span>
            <span>
              <strong>UBND XÃ NGHĨA LÂM</strong>
              <small>AI KPI Copilot · Tỉnh Nghệ An</small>
            </span>
          </div>
        }
        placement="left"
        width={280}
        open={mobileMenuOpen}
        onClose={() => setMobileMenuOpen(false)}
        className="mobile-navigation"
        styles={{ body: { padding: 0 } }}
      >
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedMenuKey]}
          items={menuItems}
          onClick={handleMenuClick}
        />
        <div className="mobile-navigation__account">
          <Avatar src={user?.avatar_url} icon={<UserOutlined />} />
          <span>
            <strong>{user?.full_name}</strong>
            <small>{levelInfo.label}</small>
          </span>
        </div>
      </Drawer>

      <Layout className="app-main">
        <Header className="app-header">
          <div className="app-header__left">
            <Button
              type="text"
              className="mobile-menu-trigger"
              icon={
                isMobile || collapsed ? (
                  <MenuUnfoldOutlined />
                ) : (
                  <MenuFoldOutlined />
                )
              }
              onClick={() =>
                isMobile
                  ? setMobileMenuOpen(true)
                  : setCollapsed((value) => !value)
              }
              aria-label={isMobile ? "Mở menu điều hướng" : "Thu gọn menu"}
            />
            <AutoComplete
              className="global-search"
              options={searchOptions}
              onSelect={(value) => navigate(value)}
              filterOption={(input, option) =>
                String(option?.label || "")
                  .toLocaleLowerCase("vi")
                  .includes(input.toLocaleLowerCase("vi"))
              }
            >
              <Input
                prefix={<SearchOutlined />}
                placeholder="Tìm kiếm KPI, cán bộ, đơn vị, minh chứng..."
                allowClear
              />
            </AutoComplete>
          </div>
          <div className="app-header__right">
            <div className="app-header__datetime">
              <CalendarOutlined />
              <span>{WEEKDAYS[now.getDay()]},</span>
              <strong>
                {String(now.getDate()).padStart(2, "0")}/
                {String(now.getMonth() + 1).padStart(2, "0")}/
                {now.getFullYear()}
              </strong>
            </div>
            <Tooltip title="Thông báo">
              <Badge dot offset={[-5, 5]}>
                <Button
                  type="text"
                  className="header-icon-button"
                  icon={<BellOutlined />}
                  aria-label="Thông báo"
                />
              </Badge>
            </Tooltip>
            <div className="header-user-info">
              <Avatar
                size={32}
                src={user?.avatar_url}
                icon={<UserOutlined />}
              />
              <div className="header-user-info__text">
                <span className="header-user-info__name">
                  {user?.full_name}
                </span>
                <span className="header-user-info__role">
                  {levelInfo.label}
                </span>
              </div>
              <Tooltip title="Đổi mật khẩu">
                <Button
                  id="change-pwd-btn"
                  type="text"
                  icon={<LockOutlined />}
                  onClick={() => setIsChangePasswordOpen(true)}
                />
              </Tooltip>
              <Tooltip title="Đăng xuất">
                <Button
                  id="logout-btn"
                  type="text"
                  danger
                  icon={<LogoutOutlined />}
                  onClick={handleLogout}
                />
              </Tooltip>
            </div>
          </div>
        </Header>
        <Content className="app-content">
          <Outlet />
        </Content>
      </Layout>

      <Modal
        title="Đổi mật khẩu"
        open={isChangePasswordOpen}
        onCancel={() => {
          setIsChangePasswordOpen(false);
          pwdForm.resetFields();
        }}
        footer={null}
        destroyOnHidden
      >
        <Form form={pwdForm} layout="vertical" onFinish={handleChangePassword}>
          <Form.Item
            name="oldPassword"
            label="Mật khẩu cũ"
            rules={[{ required: true, message: "Vui lòng nhập mật khẩu cũ" }]}
          >
            <Input.Password placeholder="Nhập mật khẩu cũ" />
          </Form.Item>
          <Form.Item
            name="newPassword"
            label="Mật khẩu mới"
            rules={[
              { required: true, message: "Vui lòng nhập mật khẩu mới" },
              { min: 8, message: "Mật khẩu mới phải từ 8 ký tự trở lên" },
            ]}
          >
            <Input.Password placeholder="Nhập mật khẩu mới" />
          </Form.Item>
          <Form.Item
            name="confirmPassword"
            label="Xác nhận mật khẩu mới"
            dependencies={["newPassword"]}
            rules={[
              { required: true, message: "Vui lòng xác nhận mật khẩu mới" },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue("newPassword") === value) {
                    return Promise.resolve();
                  }
                  return Promise.reject(
                    new Error("Mật khẩu xác nhận không khớp!"),
                  );
                },
              }),
            ]}
          >
            <Input.Password placeholder="Xác nhận mật khẩu mới" />
          </Form.Item>
          <div className="modal-actions">
            <Button
              onClick={() => {
                setIsChangePasswordOpen(false);
                pwdForm.resetFields();
              }}
            >
              Hủy
            </Button>
            <Button type="primary" htmlType="submit" loading={pwdLoading}>
              Cập nhật
            </Button>
          </div>
        </Form>
      </Modal>
      <FloatingCopilot />
    </Layout>
  );
}
