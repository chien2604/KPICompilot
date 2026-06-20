import {
  BarChartOutlined,
  FileDoneOutlined,
  FileSearchOutlined,
  HeatMapOutlined,
  MessageOutlined,
  ProfileOutlined,
  ProjectOutlined,
  RobotOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import { Layout, Menu, Select, Typography } from 'antd';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { userApi } from '../api/userApi';

const { Header, Sider, Content } = Layout;

export default function AppLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const [users, setUsers] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [selectedUser, setSelectedUser] = useState(localStorage.getItem('selected_user_id') || '1');

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

  const userOptions = [
    ...departments.map((department) => ({
      label: department.name,
      options: users
        .filter((user) => user.department_id === department.id)
        .map((user) => ({ value: String(user.id), label: `${user.full_name} - ${user.position_title}` })),
    })).filter((group) => group.options.length > 0),
    {
      label: 'Chưa phân phòng',
      options: users
        .filter((user) => !departments.some((department) => department.id === user.department_id))
        .map((user) => ({ value: String(user.id), label: `${user.full_name} - ${user.position_title}` })),
    },
  ].filter((group) => group.options.length > 0);

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
      <Sider width={248} className="app-sidebar">
        <div className="logo"><MessageOutlined /> AI KPI Copilot</div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header className="app-header">
          <Typography.Title level={4}>AI KPI Copilot for Government</Typography.Title>
          <Select
            value={selectedUser}
            className="user-select"
            showSearch
            optionFilterProp="label"
            options={userOptions}
            onChange={(value) => {
              setSelectedUser(value);
              localStorage.setItem('selected_user_id', value);
              window.dispatchEvent(new CustomEvent('demo-user-change', { detail: value }));
              if (location.pathname.startsWith('/employees/')) navigate(`/employees/${value}`);
              if (location.pathname.startsWith('/kpi/')) navigate(`/kpi/${value}`);
            }}
          />
        </Header>
        <Content className="app-content">
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
