import {
  Alert,
  Avatar,
  Button,
  Card,
  Col,
  Empty,
  Form,
  InputNumber,
  Progress,
  Row,
  Select,
  Space,
  Spin,
  Table,
  Tag,
  Typography,
  message,
} from "antd";
import {
  BulbOutlined,
  CheckCircleOutlined,
  ReloadOutlined,
  RobotOutlined,
  SaveOutlined,
  UserOutlined,
} from "@ant-design/icons";
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { authApi } from "../api/authApi";
import { kpiApi } from "../api/kpiApi";
import { useAuth } from "../contexts/AuthContext";
import { riskColor, riskLevelLabel } from "../utils/formatters";

const MANAGEMENT_FIELDS = [
  ["unit_result_percent", "Kết quả đơn vị/lĩnh vực phụ trách"],
  ["implementation_percent", "Năng lực tổ chức thực hiện"],
  ["cohesion_percent", "Đoàn kết nội bộ"],
];

/** Render deterministic KPI inputs and results under Decree 335. */
export default function KpiEvaluationPage() {
  const { userId } = useParams();
  const navigate = useNavigate();
  const { user: currentUser } = useAuth();
  const [form] = Form.useForm();
  const [profile, setProfile] = useState(null);
  const [score, setScore] = useState(null);
  const [criteria, setCriteria] = useState([]);
  const [selectableUsers, setSelectableUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const canReview =
    currentUser?.is_admin ||
    selectableUsers.some((person) => String(person.id) === String(userId));

  /** Load profile, official criteria, reviewer inputs, and any existing score. */
  const load = async () => {
    setLoading(true);
    try {
      const profileData = await kpiApi.profile(userId);
      setProfile(profileData);
      const [criterionData, inputData, scoreData] = await Promise.all([
        kpiApi.criteria(profileData.user.kpi_role_template),
        kpiApi.assessmentInputs(userId).catch(() => ({
          common_scores: {},
          management_metrics: {},
        })),
        kpiApi.score(userId).catch(() => null),
      ]);
      setCriteria(criterionData);
      setScore(scoreData);
      form.setFieldsValue({
        common_scores: inputData.common_scores,
        management_metrics: inputData.management_metrics,
      });
    } catch (error) {
      setProfile(null);
      message.error(error.response?.data?.detail || "Không thể tải hồ sơ KPI.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    authApi
      .assignableUsers()
      .then(setSelectableUsers)
      .catch(() => setSelectableUsers([]));
  }, []);

  useEffect(() => {
    load();
  }, [userId]);

  const groupedUsers = useMemo(() => {
    const users = currentUser?.is_admin
      ? selectableUsers
      : [
          ...(profile?.user?.id === currentUser?.user_id ? [profile.user] : []),
          ...selectableUsers,
        ];
    const uniqueUsers = [
      ...new Map(users.map((person) => [person.id, person])).values(),
    ];
    const groups = {};
    uniqueUsers.forEach((person) => {
      const department = person.department_name || person.department || "Khác";
      if (!groups[department]) groups[department] = [];
      groups[department].push({
        value: person.id,
        label: `${person.full_name} · ${person.position_title || "Chưa cập nhật"}`,
      });
    });
    return Object.entries(groups).map(([label, options]) => ({
      label,
      options,
    }));
  }, [currentUser, profile, selectableUsers]);

  /** Persist manual inputs, then ask only the deterministic engine to recompute. */
  const saveAndRecompute = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      await kpiApi.saveAssessmentInputs(userId, {
        common_scores: values.common_scores || {},
        management_metrics: values.management_metrics || {},
      });
      const result = await kpiApi.recompute(userId);
      setScore(result);
      message.success("Đã lưu đầu vào và tính lại KPI bằng Rule Engine.");
    } catch (error) {
      message.error(error.response?.data?.detail || "Không thể tính lại KPI.");
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <Spin fullscreen />;
  if (!profile) return <Empty description="Không có dữ liệu hồ sơ" />;

  const target = profile.user;
  const isManager = ["LEADERSHIP", "UNIT_HEAD", "UNIT_DEPUTY"].includes(
    target.organization_role,
  );
  const missingInputs = score?.breakdown_json?.missing_inputs || [];
  const breakdown = score?.breakdown_json?.breakdown || [];

  return (
    <Space direction="vertical" size={18} className="page">
      <div className="page-title-row">
        <div>
          <Typography.Title level={3} style={{ margin: 0 }}>
            Đánh giá KPI theo Nghị định 335
          </Typography.Title>
          <Typography.Text type="secondary">
            Quyết định 283/QĐ-UBND ngày 31/05/2026 · UBND xã Nghĩa Lâm
          </Typography.Text>
        </div>
        <Select
          showSearch
          optionFilterProp="label"
          options={groupedUsers}
          value={Number(userId)}
          onChange={(value) => navigate(`/kpi/${value}`)}
          style={{ width: 390 }}
        />
      </div>

      {!target.is_kpi_eligible && (
        <Alert
          type="info"
          showIcon
          message="Chưa thuộc phạm vi KPI hiện hành"
          description="Hồ sơ vẫn thuộc cơ cấu 42 người nhưng chưa có tiêu chí cụ thể trong Quyết định 283."
        />
      )}

      {target.is_kpi_eligible && (
        <>
          <Row gutter={[16, 16]}>
            <Col xs={24} lg={8}>
              <Card className="kpi-person-card">
                <div className="kpi-person-card__identity">
                  <Avatar
                    size={62}
                    src={target.avatar_url}
                    icon={<UserOutlined />}
                  />
                  <div>
                    <strong>{target.full_name}</strong>
                    <span>{target.position_title}</span>
                    <small>{target.department}</small>
                  </div>
                </div>
                <Tag>{target.kpi_role_template}</Tag>
              </Card>
            </Col>
            <Col xs={24} lg={16}>
              <Card title="Kết quả hiện tại" className="kpi-result-card">
                {score ? (
                  <Row gutter={20} align="middle">
                    <Col flex="180px">
                      <Progress
                        type="dashboard"
                        percent={score.total_score}
                        strokeColor={riskColor(score.total_score)}
                        format={(value) => `${value}/100`}
                      />
                    </Col>
                    <Col flex="auto">
                      <Typography.Title level={4}>
                        {score.classification}
                      </Typography.Title>
                      <Tag color={riskColor(score.total_score)}>
                        Rủi ro{" "}
                        {riskLevelLabel[score.risk_level] || score.risk_level}
                      </Tag>
                      {missingInputs.length > 0 && (
                        <Alert
                          style={{ marginTop: 12 }}
                          type="warning"
                          showIcon
                          message={`Kết quả tạm tính, còn ${missingInputs.length} đầu vào thiếu`}
                        />
                      )}
                    </Col>
                  </Row>
                ) : (
                  <Empty description="Chưa tính điểm cho kỳ hiện tại" />
                )}
              </Card>
            </Col>
          </Row>

          {canReview && (
            <Form form={form} layout="vertical">
              <Row gutter={[16, 16]} align="top">
                <Col xs={24} xl={18}>
                  <Card
                    title="Phần A · Tiêu chí chung (30 điểm)"
                    extra="Điểm do người có thẩm quyền nhập"
                    className="kpi-criteria-card"
                  >
                    <div className="kpi-criteria-grid">
                      {criteria.map((criterion, index) => (
                        <div
                          className="kpi-criterion-row"
                          key={criterion.criterion_code}
                        >
                          <span className="kpi-criterion-row__number">
                            {index + 1}
                          </span>
                          <span className="kpi-criterion-row__content">
                            <strong>{criterion.criterion_code}</strong>
                            <span>{criterion.criterion_name}</span>
                          </span>
                          <Form.Item
                            name={["common_scores", criterion.criterion_code]}
                            rules={[
                              { required: true, message: "Chưa nhập điểm" },
                            ]}
                          >
                            <InputNumber
                              min={0}
                              max={criterion.max_score}
                              step={0.5}
                              addonAfter={`/ ${criterion.max_score}`}
                            />
                          </Form.Item>
                        </div>
                      ))}
                    </div>
                  </Card>

                  {isManager && (
                    <Card
                      title="Tỷ lệ bổ sung cho lãnh đạo, quản lý"
                      className="kpi-management-card"
                      style={{ marginTop: 16 }}
                    >
                      <Row gutter={16}>
                        {MANAGEMENT_FIELDS.map(([code, label]) => (
                          <Col xs={24} md={8} key={code}>
                            <Form.Item
                              name={["management_metrics", code]}
                              label={label}
                              rules={[
                                { required: true, message: "Chưa nhập tỷ lệ" },
                              ]}
                            >
                              <InputNumber
                                min={0}
                                max={100}
                                addonAfter="%"
                                style={{ width: "100%" }}
                              />
                            </Form.Item>
                          </Col>
                        ))}
                      </Row>
                    </Card>
                  )}
                </Col>
                <Col xs={24} xl={6}>
                  <Card className="kpi-assistant-card">
                    <div className="kpi-assistant-card__robot">
                      <RobotOutlined />
                    </div>
                    <Typography.Title level={5}>
                      AI Copilot gợi ý
                    </Typography.Title>
                    {missingInputs.length ? (
                      <Alert
                        type="warning"
                        showIcon
                        message={`${missingInputs.length} đầu vào đang thiếu`}
                        description="Bổ sung đầy đủ dữ liệu để Rule Engine tính kết quả chính thức."
                      />
                    ) : (
                      <div className="kpi-assistant-card__complete">
                        <CheckCircleOutlined />
                        <span>Các đầu vào hiện đã đầy đủ.</span>
                      </div>
                    )}
                    <div className="kpi-assistant-card__tips">
                      <strong>
                        <BulbOutlined /> Lưu ý đánh giá
                      </strong>
                      <span>
                        Đối chiếu kết quả nhiệm vụ và minh chứng kèm theo.
                      </span>
                      <span>AI chỉ giải thích, không tự sửa điểm đã nhập.</span>
                    </div>
                  </Card>
                </Col>
              </Row>

              <div className="kpi-sticky-actions">
                <Button icon={<ReloadOutlined />} onClick={load}>
                  Tải lại
                </Button>
                <Button
                  type="primary"
                  icon={<SaveOutlined />}
                  loading={saving}
                  onClick={saveAndRecompute}
                >
                  Lưu và tính KPI
                </Button>
              </div>
            </Form>
          )}

          <Card title="Breakdown Rule Engine" style={{ marginTop: 0 }}>
            <Table
              rowKey="group_code"
              pagination={false}
              dataSource={breakdown}
              columns={[
                { title: "Nhóm", dataIndex: "group_name" },
                { title: "Điểm tối đa", dataIndex: "max_score", width: 130 },
                { title: "Điểm", dataIndex: "score", width: 110 },
                {
                  title: "Căn cứ",
                  dataIndex: "reasons",
                  render: (reasons = []) => reasons.join(" "),
                },
              ]}
            />
          </Card>
        </>
      )}
    </Space>
  );
}
