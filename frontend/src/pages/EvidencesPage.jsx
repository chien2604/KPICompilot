import {
  Button,
  Card,
  Col,
  Form,
  Input,
  Row,
  Segmented,
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
  LinkOutlined,
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
  const canAssign =
    !user?.is_admin &&
    ["UBND_AUTHORITY", "UNIT_HEAD", "UNIT_DEPUTY"].includes(
      user?.organization_role,
    );
  const canReview =
    !user?.is_admin &&
    ["UBND_AUTHORITY", "UNIT_HEAD", "UNIT_DEPUTY"].includes(
      user?.organization_role,
    );

  const [evidences, setEvidences] = useState([]);
  const [myTasks, setMyTasks] = useState([]); // task được giao cho mình
  const [assignedTasks, setAssignedTasks] = useState([]); // task mình đã giao
  const [file, setFile] = useState(null);
  const [submissionMode, setSubmissionMode] = useState("file");
  const [uploading, setUploading] = useState(false);
  const [tableLoading, setTableLoading] = useState(false);
  const [form] = Form.useForm();

  /** Load the all. */
  const loadAll = () => {
    if (!myId) return;
    setTableLoading(true);
    const requests = [
      evidenceApi.list(canReview ? {} : { uploaded_by: myId }),
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
          assignmentId: t.assignees?.find((item) => item.user_id === myId)
            ?.user_id
            ? t.assignees.find((item) => item.user_id === myId)?.assignment_id
            : null,
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

  /** Submit either a file or an authoritative external product reference. */
  const submitProduct = async () => {
    let values;
    try {
      values = await form.validateFields();
    } catch {
      return;
    }
    if (submissionMode === "file" && !file) {
      return message.warning("Chọn tệp sản phẩm cần nộp");
    }

    setUploading(true);
    try {
      const task = myTasks.find((item) => item.id === values.task_id);
      const assignmentId = task?.assignees.find(
        (item) => item.user_id === myId,
      )?.assignment_id;
      const result =
        submissionMode === "file"
          ? await evidenceApi.upload({
              task_id: values.task_id,
              assignment_id: assignmentId,
              file,
            })
          : await evidenceApi.createReference({
              task_id: values.task_id,
              assignment_id: assignmentId,
              url: values.url,
              title: values.reference_title,
              source_system: values.source_system,
              source_record_id: values.source_record_id,
              document_number: values.document_number,
            });
      if (result.status === "AI_CHECK_FAILED") {
        message.warning(
          "Đã nộp sản phẩm; AI chưa phân tích được nhưng không chặn xác minh.",
        );
      } else {
        message.success("Đã nộp sản phẩm và chuyển chờ xác minh.");
      }
      setFile(null);
      form.resetFields();
      loadAll();
    } catch (err) {
      console.error(err);
      message.error(
        err.response?.data?.detail || "Không thể nộp sản phẩm đầu ra.",
      );
    } finally {
      setUploading(false);
    }
  };

  const verifyProduct = async (evidenceId, verificationStatus) => {
    try {
      await evidenceApi.verify(evidenceId, {
        verification_status: verificationStatus,
      });
      message.success("Đã cập nhật kết quả xác minh sản phẩm.");
      loadAll();
    } catch (error) {
      message.error(
        error.response?.data?.detail || "Không thể xác minh sản phẩm.",
      );
    }
  };

  return (
    <Space direction="vertical" size={18} className="page">
      <div className="page-intro">
        <div>
          <Typography.Title level={3}>Sản phẩm công việc</Typography.Title>
          <Typography.Text>
            Nộp sản phẩm, xác minh và xem phân tích hỗ trợ từ AI
          </Typography.Text>
        </div>
        <span className="page-intro__period">
          {evidences.length} minh chứng của bạn
        </span>
      </div>

      <Card
        title="Nộp sản phẩm đầu ra"
        extra={
          <Segmented
            value={submissionMode}
            onChange={(value) => {
              setSubmissionMode(value);
              setFile(null);
              form.resetFields([
                "url",
                "reference_title",
                "source_system",
                "source_record_id",
                "document_number",
              ]);
            }}
            options={[
              { value: "file", label: "Tệp tải lên", icon: <UploadOutlined /> },
              {
                value: "reference",
                label: "Liên kết nguồn",
                icon: <LinkOutlined />,
              },
            ]}
          />
        }
        className="evidence-upload-card"
      >
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
              {submissionMode === "file" ? (
                <Form.Item label="Tệp sản phẩm" required>
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
              ) : (
                <Row gutter={12}>
                  <Col span={24}>
                    <Form.Item
                      name="url"
                      label="Liên kết sản phẩm"
                      rules={[
                        { required: true, message: "Nhập liên kết sản phẩm" },
                        { type: "url", message: "Liên kết không hợp lệ" },
                      ]}
                    >
                      <Input
                        prefix={<LinkOutlined />}
                        placeholder="https://..."
                      />
                    </Form.Item>
                  </Col>
                  <Col xs={24} md={12}>
                    <Form.Item
                      name="reference_title"
                      label="Tên sản phẩm"
                      rules={[{ required: true, message: "Nhập tên sản phẩm" }]}
                    >
                      <Input />
                    </Form.Item>
                  </Col>
                  <Col xs={24} md={12}>
                    <Form.Item name="document_number" label="Số văn bản/record">
                      <Input />
                    </Form.Item>
                  </Col>
                  <Col xs={24} md={12}>
                    <Form.Item name="source_system" label="Hệ thống nguồn">
                      <Input />
                    </Form.Item>
                  </Col>
                  <Col xs={24} md={12}>
                    <Form.Item name="source_record_id" label="Mã bản ghi nguồn">
                      <Input />
                    </Form.Item>
                  </Col>
                </Row>
              )}
              <div className="evidence-upload-actions">
                <Button
                  type="primary"
                  icon={<UploadOutlined />}
                  onClick={submitProduct}
                  loading={uploading}
                >
                  {submissionMode === "file" ? "Nộp tệp" : "Nộp liên kết"}
                </Button>
              </div>
            </Col>
          </Row>
        </Form>
      </Card>

      <Card title="Danh sách sản phẩm">
        <EvidenceTable
          data={evidences}
          loading={tableLoading}
          onVerify={canReview ? verifyProduct : null}
        />
      </Card>
    </Space>
  );
}
