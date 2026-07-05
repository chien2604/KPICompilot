import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Alert, Button, Form, Input, Select, Spin } from 'antd';
import { LockOutlined, MailOutlined, UserOutlined } from '@ant-design/icons';
import { useAuth } from '../contexts/AuthContext';

const DEMO_USERS = [
  { label: 'Nguyễn Minh An — Giám đốc Sở', email: 'user1@demo.local' },
  { label: 'Trần Thu Hà — Phó Giám đốc Sở', email: 'user2@demo.local' },
  { label: 'Phạm Quốc Bảo — Phó Giám đốc Sở', email: 'user3@demo.local' },
  { label: 'Lê Thị Mai — Trưởng phòng VP', email: 'user4@demo.local' },
  { label: 'Hoàng Văn Nam — Trưởng phòng Dân tộc', email: 'user6@demo.local' },
  { label: 'Phó Huy — Phó trưởng phòng Thanh tra', email: 'user11@demo.local' },
  { label: 'Nguyễn Lan Anh — Chuyên viên', email: 'user12@demo.local' },
];

const ROLE_BADGE = {
  1: { label: 'Giám đốc', color: '#7c3aed' },
  2: { label: 'Phó Giám đốc', color: '#2563eb' },
  3: { label: 'Trưởng phòng', color: '#0891b2' },
  4: { label: 'Phó phòng', color: '#059669' },
  5: { label: 'Chuyên viên', color: '#d97706' },
};

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const from = location.state?.from?.pathname || '/dashboard';

  const handleSubmit = async (values) => {
    setError(null);
    setLoading(true);
    try {
      await login(values.email, values.password);
      navigate(from, { replace: true });
    } catch (err) {
      setError(err.response?.data?.detail || 'Đăng nhập thất bại. Vui lòng kiểm tra lại.');
    } finally {
      setLoading(false);
    }
  };

  const handleDemoSelect = (email) => {
    form.setFieldsValue({ email, password: '123456' });
  };

  return (
    <div className="login-page">
      <div className="login-bg" aria-hidden="true" />

      <div className="login-card">
        {/* Logo */}
        <div className="login-logo">
          <svg width="48" height="48" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect width="32" height="32" rx="8" fill="url(#grad)" />
            <path d="M8 22L13 14l4 5 3-4 4 7" stroke="white" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
            <circle cx="24" cy="10" r="3" fill="white" fillOpacity="0.9" />
            <path d="M21.5 10h-13" stroke="white" strokeWidth="1.5" strokeLinecap="round" />
            <defs>
              <linearGradient id="grad" x1="0" y1="0" x2="32" y2="32" gradientUnits="userSpaceOnUse">
                <stop stopColor="#6366f1" />
                <stop offset="1" stopColor="#0ea5e9" />
              </linearGradient>
            </defs>
          </svg>
        </div>

        <h1 className="login-title">AI KPI Copilot</h1>
        <p className="login-subtitle">Hệ thống đánh giá KPI thông minh dành cho cơ quan Nhà nước</p>

        {/* Demo quick select */}
        <div className="login-demo-section">
          <label className="login-demo-label">
            <UserOutlined /> Chọn nhanh tài khoản demo
          </label>
          <Select
            id="demo-user-select"
            placeholder="Chọn người dùng demo..."
            style={{ width: '100%' }}
            onChange={handleDemoSelect}
            options={DEMO_USERS.map((u) => ({ value: u.email, label: u.label }))}
            popupMatchSelectWidth={false}
            allowClear
          />
          <p className="login-demo-hint">Mật khẩu mặc định: <code>123456</code></p>
        </div>

        {/* Divider */}
        <div className="login-divider"><span>Hoặc đăng nhập thủ công</span></div>

        {/* Form */}
        <Form
          id="login-form"
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          requiredMark={false}
        >
          <Form.Item
            name="email"
            rules={[
              { required: true, message: 'Vui lòng nhập email' },
              { type: 'email', message: 'Email không hợp lệ' },
            ]}
          >
            <Input
              id="login-email"
              prefix={<MailOutlined />}
              placeholder="Email công vụ"
              size="large"
              autoComplete="email"
            />
          </Form.Item>

          <Form.Item
            name="password"
            rules={[{ required: true, message: 'Vui lòng nhập mật khẩu' }]}
          >
            <Input.Password
              id="login-password"
              prefix={<LockOutlined />}
              placeholder="Mật khẩu"
              size="large"
              autoComplete="current-password"
            />
          </Form.Item>

          {error && (
            <Form.Item>
              <Alert type="error" message={error} showIcon />
            </Form.Item>
          )}

          <Form.Item style={{ marginBottom: 0 }}>
            <Button
              id="login-submit"
              type="primary"
              htmlType="submit"
              size="large"
              block
              loading={loading}
              icon={loading ? <Spin size="small" /> : null}
            >
              Đăng nhập
            </Button>
          </Form.Item>
        </Form>

        {/* Role legend */}
        <div className="login-role-legend">
          <p className="login-role-legend__title">Phân cấp quyền hạn</p>
          <div className="login-role-legend__grid">
            {Object.entries(ROLE_BADGE).map(([lvl, { label, color }]) => (
              <span key={lvl} className="login-role-badge" style={{ background: color + '18', color }}>
                {label}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
