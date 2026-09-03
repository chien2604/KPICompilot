import { Button, Progress, Space, Table, Tag } from "antd";
import { CheckOutlined, CloseOutlined, EyeOutlined } from "@ant-design/icons";
import { Link } from "react-router-dom";
import { formatDate } from "../utils/formatters";

/** Render the evidence table interface. */
export default function EvidenceTable({
  data = [],
  loading = false,
  onVerify,
}) {
  const verificationLabels = {
    PENDING_REVIEW: "Chờ xác minh",
    VERIFIED: "Đã xác minh",
    REJECTED: "Từ chối",
    DRAFT: "Bản nháp",
  };

  return (
    <Table
      rowKey="id"
      loading={loading}
      dataSource={data}
      pagination={{ pageSize: 10 }}
      rowClassName={() => "evidence-table-row"}
      columns={[
        {
          title: "Sản phẩm",
          dataIndex: "file_name",
          render: (value, row) =>
            row.source_type === "EXTERNAL_LINK" ? (
              <a href={row.file_path} target="_blank" rel="noreferrer">
                {value}
              </a>
            ) : (
              value
            ),
        },
        { title: "Task", dataIndex: "task_id", width: 90 },
        {
          title: "Xác minh",
          dataIndex: "verification_status",
          width: 130,
          render: (value) => (
            <Tag>{verificationLabels[value] || value || "Bản nháp"}</Tag>
          ),
        },
        {
          title: "Phù hợp",
          dataIndex: "ai_relevance_score",
          width: 150,
          render: (value) =>
            value == null ? (
              <Tag>Chưa phân tích</Tag>
            ) : (
              <Progress percent={Math.round(value)} size="small" />
            ),
        },
        {
          title: "Ngày tạo",
          dataIndex: "created_at",
          width: 130,
          render: formatDate,
        },
        {
          title: "",
          width: 230,
          render: (_, row) => (
            <Space>
              <Link to={`/evidences/${row.id}/analysis`}>
                <Button icon={<EyeOutlined />}>Phân tích</Button>
              </Link>
              {onVerify && row.verification_status === "PENDING_REVIEW" && (
                <>
                  <Button
                    type="primary"
                    icon={<CheckOutlined />}
                    onClick={() => onVerify(row.id, "VERIFIED")}
                  />
                  <Button
                    danger
                    icon={<CloseOutlined />}
                    onClick={() => onVerify(row.id, "REJECTED")}
                  />
                </>
              )}
            </Space>
          ),
        },
      ]}
    />
  );
}
