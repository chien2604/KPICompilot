import { Tag } from "antd";
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  LoadingOutlined,
  MinusCircleOutlined,
} from "@ant-design/icons";
import { statusLabel } from "../utils/formatters";

const colors = {
  COMPLETED: "success",
  IN_PROGRESS: "processing",
  OVERDUE: "error",
  NOT_STARTED: "default",
  UPLOADED: "default",
  PROCESSING: "processing",
  ANALYZED: "success",
  FAILED: "error",
};

const icons = {
  COMPLETED: <CheckCircleOutlined />,
  IN_PROGRESS: <LoadingOutlined />,
  OVERDUE: <ExclamationCircleOutlined />,
  NOT_STARTED: <MinusCircleOutlined />,
  PROCESSING: <LoadingOutlined />,
  ANALYZED: <CheckCircleOutlined />,
  FAILED: <ExclamationCircleOutlined />,
};

/** Render the status tag interface. */
export default function StatusTag({ status }) {
  return (
    <Tag
      color={colors[status] || "default"}
      icon={icons[status] || <ClockCircleOutlined />}
      className={`status-tag status-tag--${String(status || "").toLowerCase()}`}
    >
      {statusLabel[status] || status}
    </Tag>
  );
}
