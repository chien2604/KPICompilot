import {
  Button,
  Card,
  Col,
  Form,
  Row,
  Select,
  Space,
  Tag,
  Typography,
  Upload,
  message,
} from "antd";
import {
  CloudUploadOutlined,
  FileProtectOutlined,
  UploadOutlined,
} from "@ant-design/icons";
import { useEffect, useMemo, useState } from "react";
import { evidenceApi } from "../api/evidenceApi";
import { taskApi } from "../api/taskApi";
import { useAuth } from "../contexts/AuthContext";
import EvidenceTable from "../components/EvidenceTable";

/** Render the evidences page interface. */
export default function EvidencesPage() {
  const { user } = useAuth();
  const myId = user?.user_id;
  const canAssign = user?.is_admin || user?.level <= 2;

  const [evidences, setEvidences] = useState([]);
  const [myTasks, setMyTasks] = useState([]); // task được giao cho mình
  const [assignedTasks, setAssignedTasks] = useState([]); // task mình đã giao
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [tableLoading, setTableLoading] = useState(false);
  const [form] = Form.useForm();

  /** Load the all. */
  const loadAll = () => {
    if (!myId) return;
    setTableLoading(true);
    const requests = [
      evidenceApi.list({ uploaded_by: myId }),
      taskApi.list({ assigned_user_id: myId }),
    ];
    if (canAssign) requests.push(taskApi.list({ creator_id: myId }));

    Promise.all(requests)
      .then(([evidenceList, assigned, created]) => {
        setEvidences(evidenceList);
        setMyTasks(assigned);
        setAssignedTasks(created || []);
      })
      .catch(console.error)
      .finally(() => setTableLoading(false));
  };

  useEffect(() => {
    loadAll();
  }, [myId]);

  // Gộp task + gắn nhãn, loại trùng id
  const allTaskOptions = useMemo(() => {
    const seen = new Set();
    const opts = [];

    myTasks.forEach((t) => {
      if (!seen.has(t.id)) {
        seen.add(t.id);
        opts.push({
          value: t.id,
          label: `[Phụ trách] ${t.id} – ${t.title}`,
          group: "mine",
        });
      }
    });

    assignedTasks.forEach((t) => {
      if (!seen.has(t.id)) {
        seen.add(t.id);
        opts.push({
          value: t.id,
          label: `[Đã giao] ${t.id} – ${t.title}`,
          group: "assigned",
        });
      }
    });

    return opts;
  }, [myTasks, assignedTasks]);

  // Nhóm theo "Phụ trách" / "Đã giao"
  const taskSelectOptions = useMemo(() => {
    const groups = [];
    const mine = allTaskOptions.filter((o) => o.group === "mine");
    const assigned = allTaskOptions.filter((o) => o.group === "assigned");
    if (mine.length)
      groups.push({ label: "Nhiệm vụ phụ trách", options: mine });
    if (assigned.length)
      groups.push({ label: "Nhiệm vụ đã giao", options: assigned });
    return groups;
  }, [allTaskOptions]);

  /** Handle the upload operation. */
  const upload = async () => {
    let values;
    try {
      values = await form.validateFields();
    } catch {
      return;
    }
    if (!file) return message.warning("Chọn file minh chứng");

    setUploading(true);
    try {
      await evidenceApi.upload({
        task_id: values.task_id,
        uploaded_by: myId,
        file,
      });
      message.success("Đã upload và phân tích minh chứng");
      setFile(null);
      form.resetFields();
      loadAll();
    } catch (err) {
      console.error(err);
      message.error("Gặp lỗi khi tải lên hoặc phân tích minh chứng");
    } finally {
      setUploading(false);
    }
  };

  return (
    <Space direction="vertical" size={18} className="page">
      <div className="page-intro">
        <div>
          <Typography.Title level={3}>Minh chứng công việc</Typography.Title>
          <Typography.Text>
            Tải lên, quản lý và theo dõi kết quả phân tích minh chứng
          </Typography.Text>
        </div>
        <span className="page-intro__period">
          {evidences.length} minh chứng của bạn
        </span>
      </div>

      <Card title="Tải lên minh chứng" className="evidence-upload-card">
        <Form layout="vertical" form={form} disabled={uploading}>
          <Row gutter={[18, 12]}>
            <Col xs={24} lg={9}>
              <Form.Item
                label="Nhiệm vụ"
                name="task_id"
                rules={[{ required: true, message: "Chọn nhiệm vụ" }]}
              >
                <Select
                  showSearch
                  optionFilterProp="label"
                  placeholder="Chọn nhiệm vụ cần nộp minh chứng"
                  options={taskSelectOptions}
                  optionRender={(opt) => (
                    <div className="task-option">
                      <span>
                        {opt.data.group === "assigned"
                          ? opt.data.label.replace("[Đã giao] ", "")
                          : opt.data.label.replace("[Phụ trách] ", "")}
                      </span>
                      <Tag
                        color={opt.data.group === "assigned" ? "gold" : "blue"}
                      >
                        {opt.data.group === "assigned"
                          ? "Đã giao"
                          : "Phụ trách"}
                      </Tag>
                    </div>
                  )}
                />
              </Form.Item>
              <div className="evidence-upload-meta">
                <FileProtectOutlined />
                <span>
                  {myTasks.length} việc phụ trách
                  {canAssign ? ` · ${assignedTasks.length} việc đã giao` : ""}
                </span>
              </div>
            </Col>
            <Col xs={24} lg={15}>
              <Form.Item label="Tệp tin minh chứng" required>
                <Upload.Dragger
                  className="evidence-dragger"
                  beforeUpload={(selected) => {
                    setFile(selected);
                    return false;
                  }}
                  maxCount={1}
                  fileList={file ? [file] : []}
                  onRemove={() => setFile(null)}
                >
                  <CloudUploadOutlined className="evidence-dragger__icon" />
                  <strong>Kéo thả tệp tin vào đây</strong>
                  <span>hoặc bấm để chọn từ thiết bị</span>
                  <small>Hỗ trợ PDF, DOCX, XLSX, ảnh và tệp văn bản</small>
                </Upload.Dragger>
              </Form.Item>
              <div className="evidence-upload-actions">
                <Button
                  type="primary"
                  icon={<UploadOutlined />}
                  onClick={upload}
                  loading={uploading}
                >
                  Tải lên minh chứng
                </Button>
              </div>
            </Col>
          </Row>
        </Form>
      </Card>

      <Card title="Danh sách minh chứng">
        <EvidenceTable data={evidences} loading={tableLoading} />
      </Card>
    </Space>
  );
}
