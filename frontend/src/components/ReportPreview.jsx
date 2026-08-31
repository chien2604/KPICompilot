import { Alert, Empty, Table, Tag } from "antd";
import ReactMarkdown from "react-markdown";
import rehypeRaw from "rehype-raw";
import { riskColor } from "../utils/formatters";

const STATUS_LABEL = {
  COMPLETED: "Hoàn thành",
  IN_PROGRESS: "Đang thực hiện",
  NOT_STARTED: "Chưa bắt đầu",
  OVERDUE: "Quá hạn",
};

const STATUS_COLOR = {
  COMPLETED: "#16a34a",
  IN_PROGRESS: "#f59e0b",
  NOT_STARTED: "#64748b",
  OVERDUE: "#dc2626",
};

/** Render the task status table interface. */
function TaskStatusTable({ tasksByStatus = {}, totalTasks }) {
  const rows = Object.entries(tasksByStatus).map(([key, count]) => ({
    key,
    status: STATUS_LABEL[key] || key,
    count,
    color: STATUS_COLOR[key] || "#94a3b8",
    pct: totalTasks ? Math.round((count / totalTasks) * 100) : 0,
  }));

  // Thêm hàng tổng
  rows.push({
    key: "__total__",
    status: "Tổng cộng",
    count: totalTasks,
    color: "#0ea5e9",
    pct: 100,
    isTotal: true,
  });

  return (
    <Table
      dataSource={rows}
      rowKey="key"
      pagination={false}
      size="small"
      bordered
      style={{ marginBottom: 24 }}
      rowClassName={(r) => (r.isTotal ? "report-table-total-row" : "")}
      columns={[
        {
          title: "Trạng thái nhiệm vụ",
          dataIndex: "status",
          render: (text, record) => (
            <span
              style={{
                fontWeight: record.isTotal ? 700 : 500,
                color: record.color,
              }}
            >
              {!record.isTotal && (
                <span
                  style={{
                    display: "inline-block",
                    width: 10,
                    height: 10,
                    borderRadius: "50%",
                    background: record.color,
                    marginRight: 8,
                  }}
                />
              )}
              {text}
            </span>
          ),
        },
        {
          title: "Số lượng",
          dataIndex: "count",
          width: 100,
          align: "center",
          render: (val, record) => (
            <span
              style={{ fontWeight: 700, fontSize: 16, color: record.color }}
            >
              {val}
            </span>
          ),
        },
      ]}
    />
  );
}

/** Render the risk users table interface. */
function RiskUsersTable({ riskUsers = [] }) {
  if (!riskUsers.length) return null;
  return (
    <Table
      dataSource={riskUsers}
      rowKey={(r) => r.name}
      pagination={false}
      size="small"
      bordered
      style={{ marginBottom: 24 }}
      columns={[
        {
          title: "Họ tên",
          dataIndex: "name",
          render: (v) => <span style={{ fontWeight: 600 }}>{v}</span>,
        },
        { title: "Đơn vị", dataIndex: "department" },
        {
          title: "Điểm KPI",
          dataIndex: "score",
          width: 100,
          align: "center",
          render: (v) => (
            <span
              style={{ fontWeight: 700, color: riskColor(v), fontSize: 16 }}
            >
              {v}
            </span>
          ),
        },
        {
          title: "Mức rủi ro",
          dataIndex: "risk",
          width: 120,
          align: "center",
          render: (v) => (
            <Tag
              color={v === "HIGH" ? "red" : v === "MEDIUM" ? "orange" : "green"}
              style={{ fontSize: 13 }}
            >
              {v === "HIGH" ? "Cao" : v === "MEDIUM" ? "Trung bình" : "Thấp"}
            </Tag>
          ),
        },
      ]}
    />
  );
}

/** Render the report preview interface. */
export default function ReportPreview({ report }) {
  if (!report) return <Empty description="Chưa chọn báo cáo" />;

  const summary = report.summary_json || {};
  const tasksByStatus = summary.tasks_by_status || {};
  const totalTasks = summary.total_tasks || 0;
  const riskUsers = summary.risk_users || [];
  const hasStructured = totalTasks > 0;
  const contentHasConfigurationError =
    /(?:GROQ|OPENAI|ANTHROPIC|API)[_\s-]*KEY|không sinh được báo cáo từ AI|configuration|credentials/i.test(
      report.content || "",
    );

  return (
    <div className="report-preview">
      {/* Bảng thống kê nhiệm vụ */}
      {hasStructured && (
        <div className="report-preview__section">
          <div className="report-preview__section-title">Thống kê nhiệm vụ</div>
          <TaskStatusTable
            tasksByStatus={tasksByStatus}
            totalTasks={totalTasks}
          />
        </div>
      )}

      {/* Bảng cán bộ rủi ro */}
      {riskUsers.length > 0 && (
        <div className="report-preview__section">
          <div className="report-preview__section-title">
            Cán bộ có nguy cơ không đạt KPI
          </div>
          <RiskUsersTable riskUsers={riskUsers} />
        </div>
      )}

      {/* Nội dung từ LLM — luôn dùng ReactMarkdown (hỗ trợ cả inline HTML) */}
      {report.content && !contentHasConfigurationError && (
        <div className="report-preview__section">
          <div className="report-preview__section-title">Nội dung báo cáo</div>
          <div className="report-content ai-markdown-container">
            <ReactMarkdown
              rehypePlugins={[rehypeRaw]}
              components={{
                p: ({ node, ...props }) => <p {...props} />,
                h2: ({ node, ...props }) => <h2 {...props} />,
                h3: ({ node, ...props }) => <h3 {...props} />,
              }}
            >
              {report.content}
            </ReactMarkdown>
          </div>
        </div>
      )}
      {contentHasConfigurationError && (
        <Alert
          type="warning"
          showIcon
          message="Chưa thể tạo nội dung báo cáo tự động"
          description="Vui lòng thử sinh lại báo cáo sau. Dữ liệu tổng hợp bên trên vẫn có thể sử dụng để theo dõi."
        />
      )}
    </div>
  );
}
