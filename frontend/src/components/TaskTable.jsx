import {
  Avatar,
  Badge,
  Button,
  Descriptions,
  Drawer,
  Progress,
  Select,
  Space,
  Table,
  Tag,
  Timeline,
  Tooltip,
  Typography,
} from "antd";
import {
  CalendarOutlined,
  ClockCircleOutlined,
  FileTextOutlined,
  TeamOutlined,
  TrophyOutlined,
  UserOutlined,
} from "@ant-design/icons";
import { useState } from "react";
import StatusTag from "./StatusTag";
import { formatDate } from "../utils/formatters";

const PRIORITY_COLOR = { HIGH: "#e53935", MEDIUM: "#f59e0b", LOW: "#2563eb" };
const PRIORITY_LABEL = { HIGH: "Cao", MEDIUM: "Trung bình", LOW: "Thấp" };

const STATUS_PROGRESS = {
  VERIFIED: 100,
  SUBMITTED: 100,
  IN_PROGRESS: 50,
  NOT_STARTED: 0,
  OVERDUE: 75,
};
const STATUS_COLOR = {
  VERIFIED: "#16a34a",
  SUBMITTED: "#2563eb",
  IN_PROGRESS: "#f59e0b",
  NOT_STARTED: "#94a3b8",
  OVERDUE: "#e53935",
};

const STATUS_OPTIONS = [
  { value: "SUBMITTED", label: "Chờ xác minh", color: "#2563eb" },
  { value: "IN_PROGRESS", label: "Đang thực hiện", color: "#f59e0b" },
  { value: "NOT_STARTED", label: "Chưa bắt đầu", color: "#64748b" },
];

/** Render the task detail drawer interface. */
function TaskDetailDrawer({ task, open, onClose, onStatusChange, onEditTask }) {
  if (!task) return null;

  const totalAssignees = task.assignees?.length || 0;
  const scoredCount =
    task.assignees?.filter((a) => a.leader_score != null).length || 0;
  const avgScore =
    totalAssignees > 0
      ? (
          task.assignees.reduce((s, a) => s + (a.final_score || 0), 0) /
          totalAssignees
        ).toFixed(1)
      : null;

  return (
    <Drawer
      title={
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <FileTextOutlined style={{ color: "#d31a1a", fontSize: 18 }} />
          <span style={{ fontWeight: 700, fontSize: 16 }}>
            Chi tiết nhiệm vụ
          </span>
        </div>
      }
      open={open}
      onClose={onClose}
      width={520}
      styles={{ body: { padding: "20px 24px" } }}
      extra={
        onEditTask && (
          <Button
            type="primary"
            onClick={() => {
              onEditTask(task);
              onClose();
            }}
          >
            Sửa nhiệm vụ
          </Button>
        )
      }
    >
      {/* Tiêu đề nhiệm vụ */}
      <div style={{ marginBottom: 20 }}>
        <Typography.Title level={4} style={{ margin: "0 0 6px" }}>
          {task.title}
        </Typography.Title>
        {task.description && (
          <Typography.Text
            type="secondary"
            style={{ fontSize: 14, lineHeight: 1.6 }}
          >
            {task.description}
          </Typography.Text>
        )}
      </div>

      {/* Trạng thái + tiến độ */}
      <div style={{ marginBottom: 20 }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            marginBottom: 8,
          }}
        >
          <Select
            value={task.status}
            onChange={(newStatus) => onStatusChange?.(task.id, newStatus)}
            style={{ width: 150 }}
            options={STATUS_OPTIONS}
            optionRender={(option) => (
              <span style={{ color: option.data.color, fontWeight: 500 }}>
                {option.data.label}
              </span>
            )}
          />
          {task.priority && (
            <Tag
              color={PRIORITY_COLOR[task.priority]}
              style={{ borderRadius: 4 }}
            >
              {PRIORITY_LABEL[task.priority]}
            </Tag>
          )}
          <Tag
            style={{
              borderRadius: 4,
              background: "#fff7f6",
              color: "#a80f16",
              borderColor: "#ffd1ce",
            }}
          >
            Mã: {task.work_catalog_code || "—"}
          </Tag>
        </div>
        <Progress
          percent={STATUS_PROGRESS[task.status] || 0}
          strokeColor={STATUS_COLOR[task.status]}
          showInfo={false}
          size="small"
        />
      </div>

      {/* Thông tin cơ bản */}
      <Descriptions
        column={1}
        size="small"
        bordered
        style={{ marginBottom: 20 }}
      >
        <Descriptions.Item
          label={
            <span>
              <CalendarOutlined /> Hạn xử lý
            </span>
          }
        >
          {task.deadline ? (
            <span
              style={{
                fontWeight: 600,
                color: task.status === "OVERDUE" ? "#dc2626" : "inherit",
              }}
            >
              {formatDate(task.deadline)}
            </span>
          ) : (
            "—"
          )}
        </Descriptions.Item>
        <Descriptions.Item
          label={
            <span>
              <TrophyOutlined /> Hệ số quy đổi
            </span>
          }
        >
          <span style={{ fontWeight: 600 }}>
            {task.conversion_factor ?? "—"}
          </span>
        </Descriptions.Item>
        <Descriptions.Item
          label={
            <span>
              <ClockCircleOutlined /> Tạo lúc
            </span>
          }
        >
          {formatDate(task.created_at)}
        </Descriptions.Item>
        <Descriptions.Item label="Minh chứng">
          <Badge
            count={task.evidence_count || 0}
            showZero
            style={{
              background: task.evidence_count > 0 ? "#d31a1a" : "#94a3b8",
            }}
          />
        </Descriptions.Item>
      </Descriptions>

      {/* Người thực hiện */}
      {task.assignees?.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <div
            style={{
              fontWeight: 700,
              fontSize: 14,
              marginBottom: 10,
              display: "flex",
              alignItems: "center",
              gap: 6,
            }}
          >
            <TeamOutlined style={{ color: "#d31a1a" }} />
            Người thực hiện
            <span style={{ fontWeight: 400, color: "#64748b", fontSize: 13 }}>
              — {scoredCount}/{totalAssignees} đã chấm điểm
              {avgScore && ` · Điểm TB: ${avgScore}`}
            </span>
          </div>
          <Space direction="vertical" style={{ width: "100%" }} size={8}>
            {task.assignees.map((a) => (
              <div
                key={a.user_id}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "8px 12px",
                  background: "#f8fafc",
                  borderRadius: 6,
                  border: "1px solid #f1f5f9",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <Avatar
                    size={32}
                    icon={<UserOutlined />}
                    style={{ background: "#fff0ef", color: "#d31a1a" }}
                  />
                  <span style={{ fontWeight: 600, fontSize: 14 }}>
                    {a.full_name}
                  </span>
                </div>
                <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                  {a.self_score != null && (
                    <Tooltip title="Tự chấm">
                      <Tag color="blue" style={{ borderRadius: 4, margin: 0 }}>
                        TC: {a.self_score}
                      </Tag>
                    </Tooltip>
                  )}
                  {a.leader_score != null && (
                    <Tooltip title="Lãnh đạo chấm">
                      <Tag color="gold" style={{ borderRadius: 4, margin: 0 }}>
                        LĐ: {a.leader_score}
                      </Tag>
                    </Tooltip>
                  )}
                  {a.final_score != null && (
                    <Tooltip title="Điểm cuối">
                      <Tag
                        color="green"
                        style={{ borderRadius: 4, margin: 0, fontWeight: 700 }}
                      >
                        ✓ {Number(a.final_score).toFixed(1)}
                      </Tag>
                    </Tooltip>
                  )}
                  {a.progress_percent != null && (
                    <Tag
                      style={{
                        borderRadius: 4,
                        margin: 0,
                        background: "#f0fdf4",
                        color: "#16a34a",
                        borderColor: "#bbf7d0",
                      }}
                    >
                      {a.progress_percent}%
                    </Tag>
                  )}
                </div>
              </div>
            ))}
          </Space>
        </div>
      )}

      <Button block onClick={onClose} style={{ marginTop: 8 }}>
        Đóng
      </Button>
    </Drawer>
  );
}

/* ─────────────────────────────────────────────── */

export default function TaskTable({
  data = [],
  loading = false,
  canScore = false,
  assignableUserIds = new Set(),
  onScoreAssignment,
  onStatusChange,
  onEditTask,
}) {
  const [selected, setSelected] = useState(null);

  /** Handle the status change. */
  const handleStatusChange = (taskId, newStatus) => {
    if (selected && selected.id === taskId) {
      setSelected({ ...selected, status: newStatus });
    }
    onStatusChange?.(taskId, newStatus);
  };

  const columns = [
    {
      title: "Nhiệm vụ",
      dataIndex: "title",
      render: (text, record) => (
        <div>
          <div style={{ fontWeight: 600, color: "#1e293b" }}>{text}</div>
          {record.description && (
            <div
              style={{
                fontSize: 12,
                color: "#94a3b8",
                marginTop: 2,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
                maxWidth: 300,
              }}
            >
              {record.description}
            </div>
          )}
        </div>
      ),
    },
    {
      title: "Trạng thái",
      dataIndex: "status",
      width: 150,
      render: (value) => <StatusTag status={value} />,
    },
    {
      title: "Mã công việc",
      dataIndex: "work_catalog_code",
      width: 120,
      align: "center",
    },
    {
      title: "Hạn xử lý",
      dataIndex: "deadline",
      width: 120,
      render: (v, record) => (
        <span
          style={{
            color: record.status === "OVERDUE" ? "#dc2626" : "inherit",
            fontWeight: record.status === "OVERDUE" ? 700 : 400,
          }}
        >
          {formatDate(v)}
        </span>
      ),
    },
    {
      title: "Người nhận",
      width: 130,
      render: (_, record) => {
        const count = record.assignees?.length || 0;
        if (count === 0) return <span style={{ color: "#94a3b8" }}>—</span>;
        return (
          <Avatar.Group maxCount={3} size={28}>
            {record.assignees.map((a) => (
              <Tooltip key={a.user_id} title={a.full_name}>
                <Avatar
                  size={28}
                  icon={<UserOutlined />}
                  style={{
                    background: "#fff0ef",
                    color: "#d31a1a",
                    fontSize: 12,
                  }}
                />
              </Tooltip>
            ))}
          </Avatar.Group>
        );
      },
    },
    {
      title: "Minh chứng",
      dataIndex: "evidence_count",
      width: 100,
      align: "center",
      render: (v) =>
        v > 0 ? (
          <Badge count={v} color="#d31a1a" />
        ) : (
          <span style={{ color: "#94a3b8" }}>0</span>
        ),
    },
  ];

  return (
    <>
      <Table
        rowKey="id"
        loading={loading}
        dataSource={data}
        columns={columns}
        pagination={{ pageSize: 10, showSizeChanger: false }}
        scroll={{ x: 700 }}
        onRow={(record) => ({
          onClick: () => setSelected(record),
          style: { cursor: "pointer" },
        })}
        rowClassName={(record) =>
          selected?.id === record.id ? "task-row--selected" : ""
        }
      />

      <TaskDetailDrawer
        task={selected}
        open={!!selected}
        onClose={() => setSelected(null)}
        onStatusChange={handleStatusChange}
        onEditTask={onEditTask}
      />
    </>
  );
}
