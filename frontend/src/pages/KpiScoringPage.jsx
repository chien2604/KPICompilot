import {
  Avatar,
  Badge,
  Button,
  Card,
  Col,
  Empty,
  InputNumber,
  Row,
  Select,
  Space,
  Spin,
  Statistic,
  Table,
  Tag,
  Tooltip,
  Typography,
  message,
} from "antd";
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  EditOutlined,
  SaveOutlined,
  StarFilled,
  TrophyOutlined,
  UserOutlined,
  WarningOutlined,
} from "@ant-design/icons";
import { useEffect, useMemo, useState } from "react";
import { authApi } from "../api/authApi";
import { taskApi } from "../api/taskApi";
import { kpiApi } from "../api/kpiApi";
import { useAuth } from "../contexts/AuthContext";
import { riskColor, riskLevelLabel } from "../utils/formatters";

const STATUS_META = {
  COMPLETED: {
    label: "Hoàn thành",
    color: "#16a34a",
    icon: <CheckCircleOutlined />,
  },
  IN_PROGRESS: {
    label: "Đang thực hiện",
    color: "#f59e0b",
    icon: <ClockCircleOutlined />,
  },
  NOT_STARTED: {
    label: "Chưa bắt đầu",
    color: "#94a3b8",
    icon: <ClockCircleOutlined />,
  },
  OVERDUE: { label: "Quá hạn", color: "#dc2626", icon: <WarningOutlined /> },
};

const LEVEL_TAG = {
  0: { label: "Quản trị viên", color: "red" },
  1: { label: "Bí thư Chi bộ", color: "purple" },
  2: { label: "Trưởng đơn vị", color: "blue" },
  3: { label: "Trưởng Ban Công tác Mặt trận", color: "cyan" },
};

/** Render the kpi scoring page interface. */
export default function KpiScoringPage() {
  const { user: me } = useAuth();

  // Danh sách người có thể chấm
  const [assignable, setAssignable] = useState([]);
  const [loadingUsers, setLoadingUsers] = useState(true);

  // Người được chọn để chấm
  const [selectedUser, setSelectedUser] = useState(null);

  // Nhiệm vụ của người được chọn
  const [tasks, setTasks] = useState([]);
  const [loadingTasks, setLoadingTasks] = useState(false);

  // Điểm KPI hiện tại
  const [kpiScore, setKpiScore] = useState(null);

  // Bảng chỉnh sửa điểm: { [taskId_userId]: draftScore }
  const [draftScores, setDraftScores] = useState({});
  const [saving, setSaving] = useState({});
  const [recomputing, setRecomputing] = useState(false);

  // Load danh sách người có thể chấm
  useEffect(() => {
    setLoadingUsers(true);
    authApi
      .assignableUsers()
      .then(setAssignable)
      .catch(() => setAssignable([]))
      .finally(() => setLoadingUsers(false));
  }, []);

  // Khi chọn người → load nhiệm vụ + KPI
  /** Handle the select user. */
  const handleSelectUser = async (userId) => {
    const u = assignable.find((x) => x.id === userId);
    setSelectedUser(u || null);
    setTasks([]);
    setKpiScore(null);
    setDraftScores({});
    if (!userId) return;

    setLoadingTasks(true);
    try {
      const [taskData, kpiData] = await Promise.all([
        taskApi.list({ assigned_user_id: userId }),
        kpiApi.score(userId).catch(() => null),
      ]);
      setTasks(taskData);
      setKpiScore(kpiData);
    } finally {
      setLoadingTasks(false);
    }
  };

  // Lưu điểm 1 task
  /** Handle the save score. */
  const handleSaveScore = async (taskId, userId, score) => {
    const key = `${taskId}_${userId}`;
    setSaving((s) => ({ ...s, [key]: true }));
    try {
      await taskApi.scoreAssignment(taskId, userId, score);
      message.success("Đã lưu điểm");
      // Cập nhật lại task trong state
      setTasks((prev) =>
        prev.map((t) => {
          if (t.id !== taskId) return t;
          return {
            ...t,
            assignees: t.assignees.map((a) =>
              a.user_id === userId
                ? {
                    ...a,
                    leader_score: score,
                    final_score:
                      a.self_score != null
                        ? a.self_score * 0.3 + score * 0.7
                        : score,
                  }
                : a,
            ),
          };
        }),
      );
      setDraftScores((d) => {
        const n = { ...d };
        delete n[key];
        return n;
      });
    } catch {
      message.error("Lưu điểm thất bại");
    } finally {
      setSaving((s) => ({ ...s, [key]: false }));
    }
  };

  // Tính lại KPI tổng sau khi đã chấm xong
  /** Handle the recompute. */
  const handleRecompute = async () => {
    if (!selectedUser) return;
    setRecomputing(true);
    try {
      const res = await kpiApi.recompute(selectedUser.id);
      setKpiScore(res);
      message.success("Đã tính lại KPI tổng hợp");
    } catch {
      message.error("Không tính lại được KPI");
    } finally {
      setRecomputing(false);
    }
  };

  // Group authorized personnel by organization unit.
  const userSelectOptions = useMemo(() => {
    const byDept = {};
    assignable.forEach((u) => {
      const k = u.department_name || "Khác";
      if (!byDept[k]) byDept[k] = [];
      byDept[k].push({
        value: u.id,
        label: `${u.full_name} — ${u.position_title || ""}`,
        user: u,
      });
    });
    return Object.entries(byDept).map(([label, options]) => ({
      label,
      options,
    }));
  }, [assignable]);

  const scoreColor = kpiScore ? riskColor(kpiScore.total_score) : "#94a3b8";

  // Cột bảng nhiệm vụ
  const columns = [
    {
      title: "Nhiệm vụ",
      dataIndex: "title",
      render: (t, record) => (
        <div>
          <div style={{ fontWeight: 600, fontSize: 14 }}>{t}</div>
          <div style={{ fontSize: 12, color: "#64748b", marginTop: 2 }}>
            {record.work_catalog_code || "Chưa có mã"} · Hệ số{" "}
            {record.conversion_factor ?? "—"}
          </div>
        </div>
      ),
    },
    {
      title: "Trạng thái",
      dataIndex: "status",
      width: 140,
      render: (s) => {
        const m = STATUS_META[s] || {};
        return (
          <Tag
            style={{
              borderRadius: 20,
              fontWeight: 600,
              borderColor: m.color,
              color: m.color,
              background: m.color + "15",
            }}
          >
            {m.icon} {m.label}
          </Tag>
        );
      },
    },
    {
      title: "Tự chấm",
      width: 90,
      align: "center",
      render: (_, record) => {
        const a = record.assignees?.find((x) => x.user_id === selectedUser?.id);
        return a?.self_score != null ? (
          <span style={{ fontWeight: 700, color: "#0891b2" }}>
            {a.self_score}
          </span>
        ) : (
          <span style={{ color: "#94a3b8" }}>—</span>
        );
      },
    },
    {
      title: "Điểm lãnh đạo",
      width: 160,
      align: "center",
      render: (_, record) => {
        const a = record.assignees?.find((x) => x.user_id === selectedUser?.id);
        const key = `${record.id}_${selectedUser?.id}`;
        const draft = draftScores[key];
        const current = a?.leader_score;
        return (
          <InputNumber
            min={0}
            max={100}
            step={0.5}
            value={draft !== undefined ? draft : current}
            onChange={(val) => setDraftScores((d) => ({ ...d, [key]: val }))}
            style={{ width: 90 }}
            placeholder="—"
          />
        );
      },
    },
    {
      title: "Điểm cuối",
      width: 90,
      align: "center",
      render: (_, record) => {
        const a = record.assignees?.find((x) => x.user_id === selectedUser?.id);
        if (a?.final_score == null)
          return <span style={{ color: "#94a3b8" }}>—</span>;
        const c = riskColor(a.final_score);
        return (
          <span style={{ fontWeight: 700, color: c }}>
            {a.final_score.toFixed(1)}
          </span>
        );
      },
    },
    {
      title: "",
      width: 80,
      render: (_, record) => {
        const key = `${record.id}_${selectedUser?.id}`;
        const draft = draftScores[key];
        if (draft === undefined) return null;
        return (
          <Tooltip title="Lưu điểm này">
            <Button
              type="primary"
              size="small"
              icon={<SaveOutlined />}
              loading={saving[key]}
              onClick={() => handleSaveScore(record.id, selectedUser.id, draft)}
            />
          </Tooltip>
        );
      },
    },
  ];

  return (
    <Space direction="vertical" size={20} className="page">
      <div className="page-title-row">
        <Typography.Title level={3}>
          <StarFilled style={{ color: "#f59e0b", marginRight: 8 }} />
          Chấm điểm KPI
        </Typography.Title>
      </div>

      {/* Chọn người chấm */}
      <Card>
        <Row gutter={[16, 12]} align="middle">
          <Col flex="none">
            <span style={{ fontWeight: 600, fontSize: 15 }}>
              Chọn cán bộ cần chấm:
            </span>
          </Col>
          <Col flex="auto">
            <Select
              id="kpi-scoring-user-select"
              showSearch
              allowClear
              placeholder="Tìm theo tên..."
              style={{ width: "100%", maxWidth: 420 }}
              loading={loadingUsers}
              options={userSelectOptions}
              optionFilterProp="label"
              onChange={handleSelectUser}
              notFoundContent={
                loadingUsers ? (
                  <Spin size="small" />
                ) : assignable.length === 0 ? (
                  <Empty
                    description="Bạn không có quyền chấm điểm cho ai"
                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                  />
                ) : null
              }
            />
          </Col>
          <Col flex="none" style={{ color: "#64748b", fontSize: 13 }}>
            {assignable.length > 0 &&
              `${assignable.length} người trong phạm vi quyền hạn`}
          </Col>
        </Row>
      </Card>

      {/* Kết quả sau khi chọn người */}
      {selectedUser && (
        <Spin spinning={loadingTasks}>
          <Space direction="vertical" size={16} style={{ width: "100%" }}>
            {/* Header: thông tin người được chọn + điểm KPI */}
            <Row gutter={[16, 16]}>
              <Col xs={24} md={14}>
                <Card>
                  <div
                    style={{ display: "flex", alignItems: "center", gap: 16 }}
                  >
                    <Avatar
                      size={64}
                      src={selectedUser.avatar_url}
                      icon={<UserOutlined />}
                      style={{ background: "#6366f1", flexShrink: 0 }}
                    />
                    <div>
                      <div style={{ fontSize: 20, fontWeight: 800 }}>
                        {selectedUser.full_name}
                      </div>
                      <div
                        style={{ color: "#64748b", fontSize: 14, marginTop: 2 }}
                      >
                        {selectedUser.position_title}
                      </div>
                      <div style={{ marginTop: 6 }}>
                        <Tag
                          color={
                            LEVEL_TAG[selectedUser.level]?.color || "default"
                          }
                        >
                          {LEVEL_TAG[selectedUser.level]?.label}
                        </Tag>
                        <Tag color="default">
                          {selectedUser.department_name}
                        </Tag>
                      </div>
                    </div>
                  </div>
                </Card>
              </Col>
              <Col xs={24} md={10}>
                <Card>
                  <Row gutter={16}>
                    <Col span={12}>
                      <Statistic
                        title="Điểm KPI hiện tại"
                        value={kpiScore?.total_score ?? "—"}
                        suffix={kpiScore ? "/100" : ""}
                        valueStyle={{ color: scoreColor, fontWeight: 800 }}
                        prefix={<TrophyOutlined />}
                      />
                    </Col>
                    <Col span={12}>
                      <Statistic
                        title="Phân loại"
                        value={
                          kpiScore?.reference_level ||
                          kpiScore?.classification ||
                          "—"
                        }
                        valueStyle={{
                          color: scoreColor,
                          fontSize: 16,
                          fontWeight: 700,
                        }}
                      />
                    </Col>
                  </Row>
                  <div style={{ marginTop: 16 }}>
                    <Button
                      type="primary"
                      block
                      loading={recomputing}
                      onClick={handleRecompute}
                      icon={<TrophyOutlined />}
                    >
                      {recomputing ? "Đang tính..." : "Tính lại KPI tổng hợp"}
                    </Button>
                  </div>
                </Card>
              </Col>
            </Row>

            {/* Hướng dẫn */}
            <div
              style={{
                background: "#f0f9ff",
                border: "1px solid #bae6fd",
                borderRadius: 8,
                padding: "10px 16px",
                fontSize: 13,
                color: "#0369a1",
              }}
            >
              <b>Hướng dẫn:</b> Nhập điểm lãnh đạo vào cột "Điểm lãnh đạo" →
              nhấn <SaveOutlined /> để lưu từng nhiệm vụ → nhấn{" "}
              <b>"Tính lại KPI tổng hợp"</b> để cập nhật điểm KPI cuối. Điểm
              cuối = 30% tự chấm + 70% lãnh đạo chấm.
            </div>

            {/* Bảng nhiệm vụ */}
            <Card
              title={
                <span>
                  Danh sách nhiệm vụ của <b>{selectedUser.full_name}</b>
                  <Badge
                    count={tasks.length}
                    style={{ marginLeft: 8, background: "#6366f1" }}
                  />
                </span>
              }
            >
              {tasks.length === 0 && !loadingTasks ? (
                <Empty description="Cán bộ này chưa có nhiệm vụ nào" />
              ) : (
                <Table
                  rowKey="id"
                  dataSource={tasks}
                  columns={columns}
                  pagination={{ pageSize: 15, showSizeChanger: false }}
                  scroll={{ x: 700 }}
                  rowClassName={(record) =>
                    record.status === "OVERDUE" ? "task-row--overdue" : ""
                  }
                />
              )}
            </Card>
          </Space>
        </Spin>
      )}

      {/* Trạng thái rỗng — chưa chọn ai */}
      {!selectedUser && !loadingUsers && (
        <Card>
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={
              assignable.length === 0
                ? "Bạn không có quyền chấm điểm KPI cho bất kỳ ai."
                : "Chọn cán bộ ở trên để bắt đầu chấm điểm KPI."
            }
          />
        </Card>
      )}
    </Space>
  );
}
