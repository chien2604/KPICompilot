import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Alert, Button, Form, Input, Select, Spin, Modal, message } from 'antd';
import { LockOutlined, MailOutlined, UserOutlined, EditOutlined } from '@ant-design/icons';
import { useAuth } from '../contexts/AuthContext';
import { authApi } from '../api/authApi';

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
  1: { label: 'Giám đốc', color: '#1d4ed8' },     // Deep Blue
  2: { label: 'Phó Giám đốc', color: '#2563eb' }, // Royal Blue
  3: { label: 'Trưởng phòng', color: '#0284c7' }, // Sky Blue
  4: { label: 'Phó phòng', color: '#0ea5e9' },    // Light Cyan
  5: { label: 'Chuyên viên', color: '#64748b' },  // Slate Grey
};

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [form] = Form.useForm();
  const [pwdForm] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [pwdLoading, setPwdLoading] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
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

  const handlePublicChangePassword = async (values) => {
    setPwdLoading(true);
    try {
      await authApi.changePasswordPublic(values.email, values.oldPassword, values.newPassword);
      message.success('Đổi mật khẩu thành công! Hãy đăng nhập lại bằng mật khẩu mới.');
      setIsModalOpen(false);
      pwdForm.resetFields();
    } catch (err) {
      message.error(err.response?.data?.detail || 'Đổi mật khẩu thất bại. Vui lòng kiểm tra lại thông tin.');
    } finally {
      setPwdLoading(false);
    }
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

          <Form.Item style={{ marginBottom: 12 }}>
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

          <div style={{ textAlign: 'center' }}>
            <Button 
              type="link" 
              onClick={() => setIsModalOpen(true)}
              style={{ color: '#38bdf8', fontSize: 13, padding: 0 }}
            >
              Yêu cầu đổi mật khẩu?
            </Button>
          </div>
        </Form>
      </div>

      <Modal
        title={<span style={{ color: '#0f172a', fontWeight: 700 }}>Đổi mật khẩu tài khoản</span>}
        open={isModalOpen}
        onCancel={() => {
          setIsModalOpen(false);
          pwdForm.resetFields();
        }}
        footer={null}
        destroyOnClose
      >
        <Form
          form={pwdForm}
          layout="vertical"
          onFinish={handlePublicChangePassword}
        >
          <Form.Item
            name="email"
            label="Email công vụ"
            rules={[
              { required: true, message: 'Vui lòng nhập email' },
              { type: 'email', message: 'Email không hợp lệ' }
            ]}
          >
            <Input placeholder="Ví dụ: giangnh@dantoc.daklak.gov.vn" />
          </Form.Item>
          
          <Form.Item
            name="oldPassword"
            label="Mật khẩu hiện tại"
            rules={[{ required: true, message: 'Vui lòng nhập mật khẩu hiện tại' }]}
          >
            <Input.Password placeholder="Mật khẩu hiện tại của bạn" />
          </Form.Item>
          
          <Form.Item
            name="newPassword"
            label="Mật khẩu mới"
            rules={[
              { required: true, message: 'Vui lòng nhập mật khẩu mới' },
              { min: 6, message: 'Mật khẩu mới phải từ 6 ký tự trở lên' }
            ]}
          >
            <Input.Password placeholder="Mật khẩu mới muốn thay đổi" />
          </Form.Item>
          
          <Form.Item
            name="confirmPassword"
            label="Xác nhận mật khẩu mới"
            dependencies={['newPassword']}
            rules={[
              { required: true, message: 'Vui lòng xác nhận mật khẩu mới' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('newPassword') === value) {
                    return Promise.resolve();
                  }
                  return Promise.reject(new Error('Mật khẩu xác nhận không khớp!'));
                },
              }),
            ]}
          >
            <Input.Password placeholder="Nhập lại mật khẩu mới" />
          </Form.Item>
          
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 24 }}>
            <Button onClick={() => {
              setIsModalOpen(false);
              pwdForm.resetFields();
            }}>
              Hủy
            </Button>
            <Button type="primary" htmlType="submit" loading={pwdLoading}>
              Đổi mật khẩu
            </Button>
          </div>
        </Form>
      </Modal>
    </div>
  );
}
