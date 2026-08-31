import { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { Alert, Button, Form, Input, Spin, Modal, message } from "antd";
import { BankOutlined, LockOutlined, MailOutlined } from "@ant-design/icons";
import { useAuth } from "../contexts/AuthContext";
import { authApi } from "../api/authApi";

/** Render the email and password login workflow. */
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

  const from = location.state?.from?.pathname || "/dashboard";

  /** Authenticate an active account and navigate to the requested page. */
  const handleSubmit = async (values) => {
    setError(null);
    setLoading(true);
    try {
      await login(values.email, values.password);
      navigate(from, { replace: true });
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          "Đăng nhập thất bại. Vui lòng kiểm tra lại.",
      );
    } finally {
      setLoading(false);
    }
  };

  /** Change the password after validating the current public credentials. */
  const handlePublicChangePassword = async (values) => {
    setPwdLoading(true);
    try {
      await authApi.changePasswordPublic(
        values.email,
        values.oldPassword,
        values.newPassword,
      );
      message.success(
        "Đổi mật khẩu thành công! Hãy đăng nhập lại bằng mật khẩu mới.",
      );
      setIsModalOpen(false);
      pwdForm.resetFields();
    } catch (err) {
      message.error(
        err.response?.data?.detail ||
          "Đổi mật khẩu thất bại. Vui lòng kiểm tra lại thông tin.",
      );
    } finally {
      setPwdLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-bg" aria-hidden="true" />

      <div className="login-card">
        <div className="login-logo">
          <BankOutlined />
        </div>

        <span className="login-agency">ỦY BAN NHÂN DÂN XÃ NGHĨA LÂM</span>
        <h1 className="login-title">AI KPI Copilot</h1>
        <p className="login-subtitle">
          Hệ thống quản lý nhiệm vụ và đánh giá công chức · Tỉnh Nghệ An
        </p>

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
              { required: true, message: "Vui lòng nhập email" },
              { type: "email", message: "Email không hợp lệ" },
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
            rules={[{ required: true, message: "Vui lòng nhập mật khẩu" }]}
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

          <div style={{ textAlign: "center" }}>
            <Button
              type="link"
              onClick={() => setIsModalOpen(true)}
              style={{ color: "#38bdf8", fontSize: 13, padding: 0 }}
            >
              Yêu cầu đổi mật khẩu?
            </Button>
          </div>
        </Form>
      </div>

      <Modal
        title={
          <span style={{ color: "#0f172a", fontWeight: 700 }}>
            Đổi mật khẩu tài khoản
          </span>
        }
        open={isModalOpen}
        onCancel={() => {
          setIsModalOpen(false);
          pwdForm.resetFields();
        }}
        footer={null}
        destroyOnHidden
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
              { required: true, message: "Vui lòng nhập email" },
              { type: "email", message: "Email không hợp lệ" },
            ]}
          >
            <Input placeholder="Ví dụ: canbo@nghialam.gov.vn" />
          </Form.Item>

          <Form.Item
            name="oldPassword"
            label="Mật khẩu hiện tại"
            rules={[
              { required: true, message: "Vui lòng nhập mật khẩu hiện tại" },
            ]}
          >
            <Input.Password placeholder="Mật khẩu hiện tại của bạn" />
          </Form.Item>

          <Form.Item
            name="newPassword"
            label="Mật khẩu mới"
            rules={[
              { required: true, message: "Vui lòng nhập mật khẩu mới" },
              { min: 8, message: "Mật khẩu mới phải từ 8 ký tự trở lên" },
            ]}
          >
            <Input.Password placeholder="Mật khẩu mới muốn thay đổi" />
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
            <Input.Password placeholder="Nhập lại mật khẩu mới" />
          </Form.Item>

          <div
            style={{
              display: "flex",
              justifyContent: "flex-end",
              gap: 8,
              marginTop: 24,
            }}
          >
            <Button
              onClick={() => {
                setIsModalOpen(false);
                pwdForm.resetFields();
              }}
            >
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
