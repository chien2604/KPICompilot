import {
  BarChartOutlined,
  FileDoneOutlined,
  FileSearchOutlined,
  HeatMapOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  ProfileOutlined,
  ProjectOutlined,
  RobotOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import { Layout, Menu, Select, Tooltip } from 'antd';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useEffect, useMemo, useState } from 'react';
import { userApi } from '../api/userApi';
import FloatingCopilot from '../components/FloatingCopilot';

const { Header, Sider, Content } = Layout;

const WEEKDAYS = ['Chủ nhật', 'Thứ hai', 'Thứ ba', 'Thứ tư', 'Thứ năm', 'Thứ sáu', 'Thứ bảy'];

function useDate() {
  const [now] = useState(new Date());
  return now;
}

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
  const now = useDate();
  const [users, setUsers] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [selectedUser, setSelectedUser] = useState(localStorage.getItem('selected_user_id') || '1');
  const [filterDept, setFilterDept] = useState(null);
  const [filterPosition, setFilterPosition] = useState(null);
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    Promise.all([userApi.list(), userApi.departments()]).then(([rows, departmentRows]) => {
      setUsers(rows);
      setDepartments(departmentRows);
      const stored = localStorage.getItem('selected_user_id');
      const storedIsValid = rows.some((user) => String(user.id) === String(stored));
      if ((!stored || !storedIsValid) && rows[0]) {
        const fallbackUserId = String(rows[0].id);
        setSelectedUser(fallbackUserId);
        localStorage.setItem('selected_user_id', fallbackUserId);
        window.dispatchEvent(new CustomEvent('demo-user-change', { detail: fallbackUserId }));
        if (location.pathname.startsWith('/employees/')) navigate(`/employees/${fallbackUserId}`, { replace: true });
        if (location.pathname.startsWith('/kpi/')) navigate(`/kpi/${fallbackUserId}`, { replace: true });
      }
    }).catch(() => {
      setUsers([]);
      setDepartments([]);
    });
  }, [location.pathname, navigate]);

  // Danh sách đơn vị
  const deptOptions = useMemo(() =>
    departments.map((d) => ({ value: d.id, label: d.name })),
    [departments]
  );

  // Danh sách chức vụ lọc theo đơn vị đã chọn
  const positionOptions = useMemo(() => {
    const pool = filterDept ? users.filter((u) => u.department_id === filterDept) : users;
    const unique = [...new Set(pool.map((u) => u.position_title).filter(Boolean))];
    return unique.map((p) => ({ value: p, label: p }));
  }, [users, filterDept]);

  // Danh sách người lọc theo đơn vị + chức vụ
  const userOptions = useMemo(() => {
    let pool = users;
    if (filterDept) pool = pool.filter((u) => u.department_id === filterDept);
    if (filterPosition) pool = pool.filter((u) => u.position_title === filterPosition);
    return pool.map((u) => ({ value: String(u.id), label: u.full_name }));
  }, [users, filterDept, filterPosition]);

  const handleDeptChange = (val) => {
    setFilterDept(val);
    setFilterPosition(null);
  };

  const handlePositionChange = (val) => {
    setFilterPosition(val);
  };

  const handleUserChange = (value) => {
    setSelectedUser(value);
    localStorage.setItem('selected_user_id', value);
    window.dispatchEvent(new CustomEvent('demo-user-change', { detail: value }));
    if (location.pathname.startsWith('/employees/')) navigate(`/employees/${value}`);
    if (location.pathname.startsWith('/kpi/')) navigate(`/kpi/${value}`);
  };

  const menuItems = [
    { key: '/dashboard', icon: <BarChartOutlined />, label: 'Tổng quan' },
    { key: '/heatmap', icon: <HeatMapOutlined />, label: 'Heatmap' },
    { key: `/employees/${selectedUser}`, icon: <TeamOutlined />, label: 'Hồ sơ' },
    { key: '/tasks', icon: <ProjectOutlined />, label: 'Công việc' },
    { key: '/evidences', icon: <FileSearchOutlined />, label: 'Minh chứng' },
    { key: `/kpi/${selectedUser}`, icon: <FileDoneOutlined />, label: 'AI đánh giá' },
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
          <div className="header-user-filter">
            <Select
              allowClear
              placeholder="Đơn vị"
              className="header-select header-select--dept"
              options={deptOptions}
              value={filterDept}
              onChange={handleDeptChange}
              popupMatchSelectWidth={false}
            />
            <Select
              allowClear
              placeholder="Chức vụ"
              className="header-select header-select--position"
              options={positionOptions}
              value={filterPosition}
              onChange={handlePositionChange}
              disabled={positionOptions.length === 0}
              popupMatchSelectWidth={false}
            />
            <Select
              showSearch
              placeholder="Chọn người"
              className="header-select header-select--user"
              options={userOptions}
              value={selectedUser}
              onChange={handleUserChange}
              optionFilterProp="label"
              popupMatchSelectWidth={false}
            />
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
