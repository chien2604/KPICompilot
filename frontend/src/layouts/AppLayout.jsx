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
  TeamOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { Avatar, Button, Layout, Menu, Tag, Tooltip } from 'antd';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import FloatingCopilot from '../components/FloatingCopilot';

const { Header, Sider, Content } = Layout;

const WEEKDAYS = ['Chủ nhật', 'Thứ hai', 'Thứ ba', 'Thứ tư', 'Thứ năm', 'Thứ sáu', 'Thứ bảy'];

const LEVEL_TAG = {
  1: { label: 'Giám đốc', color: 'purple' },
  2: { label: 'Phó GĐ', color: 'blue' },
  3: { label: 'Trưởng phòng', color: 'cyan' },
  4: { label: 'Phó phòng', color: 'green' },
  5: { label: 'Chuyên viên', color: 'gold' },
};

function KpiLogo() {
  return (
    <svg width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <rect width="32" height="32" rx="8" fill="white" fillOpacity="0.2"/>
      <path d="M8 22L13 14l4 5 3-4 4 7" stroke="white" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"/>
      <circle cx="24" cy="10" r="3" fill="white" fillOpacity="0.9"/>
      <path d="M21.5 10h-13" stroke="white" strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
  );
}

export default function AppLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuth();
  const [collapsed, setCollapsed] = useState(false);

  const now = new Date();
  const userId = user?.user_id;
  const levelInfo = LEVEL_TAG[user?.level] || { label: 'Cán bộ', color: 'default' };

  const handleLogout = () => {
    logout();
    navigate('/login', { replace: true });
  };

  const menuItems = [
    { key: '/dashboard', icon: <BarChartOutlined />, label: 'Tổng quan' },
    ...(user?.level <= 2 ? [{ key: '/heatmap', icon: <HeatMapOutlined />, label: 'Heatmap' }] : []),
    { key: `/employees/${userId}`, icon: <TeamOutlined />, label: 'Hồ sơ' },
    { key: '/tasks', icon: <ProjectOutlined />, label: 'Công việc' },
    { key: '/evidences', icon: <FileSearchOutlined />, label: 'Minh chứng' },
    { key: `/kpi/${userId}`, icon: <FileDoneOutlined />, label: 'AI đánh giá' },
    { key: '/copilot', icon: <RobotOutlined />, label: 'AI Copilot' },
    { key: '/reports', icon: <ProfileOutlined />, label: 'Báo cáo' },
  ];

  return (
    <Layout className="app-shell">
      <Header className="app-header">
        <div className="app-header__left">
          <KpiLogo />
          <span className="app-header__brand">AI KPI Copilot</span>
        </div>
        <div className="app-header__right">
          <div className="app-header__datetime">
            <span className="app-header__weekday">{WEEKDAYS[now.getDay()]},</span>
            <span className="app-header__date">
              {String(now.getDate()).padStart(2, '0')}/
              {String(now.getMonth() + 1).padStart(2, '0')}/
              {now.getFullYear()}
            </span>
          </div>

          {/* Thông tin user đăng nhập */}
          <div className="header-user-info">
            <Avatar
              size={34}
              src={user?.avatar_url}
              icon={<UserOutlined />}
              style={{ background: '#6366f1', flexShrink: 0 }}
            />
            <div className="header-user-info__text">
              <span className="header-user-info__name">{user?.full_name}</span>
              <Tag color={levelInfo.color} style={{ fontSize: 11, lineHeight: '18px', margin: 0 }}>
                {levelInfo.label}
              </Tag>
            </div>
            <Tooltip title="Đăng xuất">
              <Button
                id="logout-btn"
                type="text"
                danger
                icon={<LogoutOutlined />}
                onClick={handleLogout}
                style={{ color: 'rgba(255,255,255,0.75)' }}
              />
            </Tooltip>
          </div>
        </div>
      </Header>
      <Layout>
        <Sider
          width={248}
          collapsedWidth={64}
          collapsed={collapsed}
          className="app-sidebar"
        >
          <Menu
            theme="light"
            mode="inline"
            selectedKeys={[location.pathname]}
            items={menuItems}
            onClick={({ key }) => navigate(key)}
            inlineCollapsed={collapsed}
          />
          <div className="sidebar-collapse-btn-wrap">
            <Tooltip title={collapsed ? 'Mở rộng menu' : 'Thu gọn menu'} placement="right">
              <button
                className="sidebar-collapse-btn"
                onClick={() => setCollapsed((v) => !v)}
                type="button"
                aria-label="Toggle sidebar"
              >
                {collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
                {!collapsed && <span className="sidebar-collapse-btn__text">Thu gọn</span>}
              </button>
            </Tooltip>
          </div>
        </Sider>
        <Content className="app-content">
          <Outlet />
        </Content>
      </Layout>
      <FloatingCopilot />
    </Layout>
  );
}
