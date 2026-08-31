import {
  Button,
  Card,
  DatePicker,
  Form,
  Input,
  InputNumber,
  Modal,
  Select,
  Space,
  Tabs,
  Tag,
  Typography,
  message,
} from "antd";
import {
  FilterOutlined,
  PlusOutlined,
  ReloadOutlined,
  SaveOutlined,
  UserOutlined,
} from "@ant-design/icons";
import { useEffect, useMemo, useState } from "react";
import dayjs from "dayjs";
import { taskApi } from "../api/taskApi";
import { authApi } from "../api/authApi";
import { useAuth } from "../contexts/AuthContext";
import { kpiApi } from "../api/kpiApi";
import TaskTable from "../components/TaskTable";

const STATUS_OPTIONS = [
  { value: "COMPLETED", label: "Hoàn thành", color: "#16a34a" },
  { value: "IN_PROGRESS", label: "Đang thực hiện", color: "#f59e0b" },
  { value: "NOT_STARTED", label: "Chưa bắt đầu", color: "#64748b" },
  { value: "OVERDUE", label: "Quá hạn", color: "#dc2626" },
];

/** Render the tasks page interface. */
export default function TasksPage() {
  const { user } = useAuth();
  const myId = user?.user_id;
  const canAssign =
    user?.is_admin ||
    ["LEADERSHIP", "UNIT_HEAD", "UNIT_DEPUTY"].includes(
      user?.organization_role,
    );

  // Danh sách người có thể giao việc (theo phân quyền)
  const [assignableUsers, setAssignableUsers] = useState([]);
  const [workCatalog, setWorkCatalog] = useState([]);
  const [catalogLoading, setCatalogLoading] = useState(false);

  // Tasks của mình (được giao cho mình)
  const [myTasks, setMyTasks] = useState([]);
  // Tasks mình đã tạo (giao cho cấp dưới)
  const [assignedTasks, setAssignedTasks] = useState([]);
  // Toàn bộ tasks của cơ quan (Chỉ giám đốc)
  const [allTasks, setAllTasks] = useState([]);

  const [open, setOpen] = useState(false);
  const [editTaskId, setEditTaskId] = useState(null);
  const [scoreModal, setScoreModal] = useState(null); // { taskId, userId, userName }
  const [form] = Form.useForm();
  const [scoreForm] = Form.useForm();

  // Bộ lọc
  const [filterStatus, setFilterStatus] = useState(null);
  const [filterDateRange, setFilterDateRange] = useState(null);

  // Tab đang active
  const [activeTab, setActiveTab] = useState("mine");

  /* ── Load data ───────────────────────────────── */
  const loadAll = () => {
    if (!myId) return;
    // Task được giao cho mình
    taskApi.list({ assigned_user_id: myId }).then(setMyTasks);
    // Task mình đã tạo (giao cho cấp dưới)
    if (canAssign) {
      taskApi.list({ creator_id: myId }).then(setAssignedTasks);
    }
    // Cấp quản lý xem toàn bộ nhiệm vụ trong phạm vi quyền.
    if (canAssign) {
      taskApi.list({}).then(setAllTasks);
    }
  };

  useEffect(() => {
    loadAll();
    authApi
      .assignableUsers()
      .then(setAssignableUsers)
      .catch(() => setAssignableUsers([]));
  }, [myId]);

  /* Dropdown giao việc được nhóm theo đơn vị công tác. */
  const assignedUserOptions = useMemo(() => {
    const byDept = {};
    assignableUsers.forEach((u) => {
      const k = u.department_name || "Khác";
      if (!byDept[k]) byDept[k] = [];
      byDept[k].push({
        value: u.id,
        label: `${u.full_name} — ${u.position_title || ""}`,
      });
    });
    return Object.entries(byDept).map(([label, options]) => ({
      label,
      options,
    }));
  }, [assignableUsers]);

  const workCatalogOptions = useMemo(() => {
    const labels = {
      LEADERSHIP: "Công việc lãnh đạo, quản lý",
      COMMON: "Công việc dùng chung",
      DEPARTMENT: "Công việc theo phòng, đơn vị",
    };
    const groups = {};
    workCatalog.forEach((item) => {
      const label = labels[item.catalog_scope] || item.catalog_scope;
      if (!groups[label]) groups[label] = [];
      groups[label].push({
        value: item.id,
        label: `${item.code} · ${item.name} · Hệ số ${item.conversion_factor}`,
      });
    });
    return Object.entries(groups).map(([label, options]) => ({
      label,
      options,
    }));
  }, [workCatalog]);

  /** Load only work codes shared by every selected assignee. */
  const handleAssigneesChange = async (userIds) => {
    form.setFieldValue("assigned_user_ids", userIds);
    form.setFieldValue("work_catalog_item_id", undefined);
    if (!userIds.length) {
      setWorkCatalog([]);
      return;
    }
    setCatalogLoading(true);
    try {
      const catalogs = await Promise.all(
        userIds.map((userId) => kpiApi.workCatalog(userId)),
      );
      const sharedCodes = new Set(catalogs[0].map((item) => item.code));
      catalogs.slice(1).forEach((items) => {
        const codes = new Set(items.map((item) => item.code));
        [...sharedCodes].forEach((code) => {
          if (!codes.has(code)) sharedCodes.delete(code);
        });
      });
      setWorkCatalog(catalogs[0].filter((item) => sharedCodes.has(item.code)));
    } catch {
      setWorkCatalog([]);
      message.error("Không thể tải danh mục công việc phù hợp.");
    } finally {
      setCatalogLoading(false);
    }
  };

  /** Fill task content from the approved catalog while allowing later editing. */
  const handleCatalogChange = (catalogItemId) => {
    const item = workCatalog.find((entry) => entry.id === catalogItemId);
    if (!item) return;
    form.setFieldsValue({
      work_catalog_item_id: catalogItemId,
      title: item.name,
      description: `${item.details}\nSản phẩm đầu ra: ${item.output}`,
    });
  };

  /* ── Lọc client-side ─────────────────────────── */
  const applyFilter = (list) => {
    let result = list;
    if (filterStatus) result = result.filter((t) => t.status === filterStatus);
    if (filterDateRange?.[0] && filterDateRange?.[1]) {
      const from = filterDateRange[0].startOf("day");
      const to = filterDateRange[1].endOf("day");
      result = result.filter((t) => {
        if (!t.deadline) return false;
        const d = dayjs(t.deadline);
        return d.isAfter(from) && d.isBefore(to);
      });
    }
    return result;
  };

  const filteredMine = useMemo(
    () => applyFilter(myTasks),
    [myTasks, filterStatus, filterDateRange],
  );
  const filteredAssigned = useMemo(
    () => applyFilter(assignedTasks),
    [assignedTasks, filterStatus, filterDateRange],
  );
  const filteredAll = useMemo(
    () => applyFilter(allTasks),
    [allTasks, filterStatus, filterDateRange],
  );

  const hasFilter = filterStatus || filterDateRange;
  /** Handle the clear filters operation. */
  const clearFilters = () => {
    setFilterStatus(null);
    setFilterDateRange(null);
  };

  /* ── Tạo/Sửa nhiệm vụ ────────────────────────────── */
  const saveTask = async () => {
    const values = await form.validateFields();
    const payload = {
      ...values,
      deadline: values.deadline ? values.deadline.format("YYYY-MM-DD") : null,
      assigned_user_ids: values.assigned_user_ids || [],
    };

    if (editTaskId) {
      await taskApi.update(editTaskId, payload);
      message.success("Đã cập nhật nhiệm vụ");
    } else {
      await taskApi.create({ ...payload, creator_id: myId });
      message.success("Đã tạo nhiệm vụ");
      setActiveTab("assigned"); // chuyển sang tab đã giao nếu tạo mới
    }

    setOpen(false);
    setEditTaskId(null);
    form.resetFields();
    loadAll();
  };

  /** Handle the edit task. */
  const handleEditTask = async (task) => {
    setEditTaskId(task.id);
    form.setFieldsValue({
      title: task.title,
      description: task.description,
      work_catalog_item_id: task.work_catalog_item_id,
      document_type: task.document_type,
      deadline: task.deadline ? dayjs(task.deadline) : null,
      assigned_user_ids: task.assignees?.map((a) => a.user_id) || [],
    });
    await handleAssigneesChange(
      task.assignees?.map((assignment) => assignment.user_id) || [],
    );
    form.setFieldValue("work_catalog_item_id", task.work_catalog_item_id);
    setOpen(true);
  };

  /* ── Chấm điểm ───────────────────────────────── */
  const submitScore = async () => {
    const values = await scoreForm.validateFields();
    await taskApi.updateQuality(scoreModal.taskId, scoreModal.userId, values);
    message.success(
      `Đã cập nhật chất lượng sản phẩm của ${scoreModal.userName}`,
    );
    setScoreModal(null);
    scoreForm.resetFields();
    loadAll();
  };

  /* ── Cập nhật trạng thái ─────────────────────── */
  const updateTaskStatus = async (taskId, newStatus) => {
    try {
      await taskApi.updateStatus(taskId, { status: newStatus });
      message.success("Đã cập nhật trạng thái công việc");
      loadAll();
    } catch (err) {
      message.error("Lỗi khi cập nhật trạng thái");
    }
  };

  /* ── Render bộ lọc (dùng lại ở cả 2 tab) ─────── */
  const FilterBar = ({ total, shown }) => (
    <Card size="small" className="task-filter-bar" style={{ marginBottom: 16 }}>
      <div className="task-filter-bar__inner">
        <FilterOutlined style={{ color: "#64748b", fontSize: 16 }} />
        <span className="task-filter-bar__title">Lọc theo:</span>

        <div className="task-filter-bar__group">
          <span className="task-filter-bar__label">Trạng thái</span>
          <Space size={8} wrap>
            {STATUS_OPTIONS.map((opt) => (
              <Tag
                key={opt.value}
                className="task-filter-tag"
                style={{
                  borderColor: opt.color,
                  color: filterStatus === opt.value ? "#fff" : opt.color,
                  background:
                    filterStatus === opt.value ? opt.color : `${opt.color}15`,
                  cursor: "pointer",
                  fontSize: 14,
                  padding: "3px 12px",
                  borderRadius: 20,
                  userSelect: "none",
                }}
                onClick={() =>
                  setFilterStatus(filterStatus === opt.value ? null : opt.value)
                }
              >
                {opt.label}
                {filterStatus === opt.value && " ✕"}
              </Tag>
            ))}
          </Space>
        </div>

        <div className="task-filter-bar__group">
          <span className="task-filter-bar__label">Hạn xử lý</span>
          <DatePicker.RangePicker
            value={filterDateRange}
            onChange={setFilterDateRange}
            format="DD/MM/YYYY"
            placeholder={["Từ ngày", "Đến ngày"]}
          />
        </div>

        {hasFilter && (
          <Button
            size="small"
            danger
            type="primary"
            onClick={clearFilters}
            style={{ marginLeft: "auto" }}
          >
            Xóa bộ lọc
          </Button>
        )}
      </div>
      {hasFilter && (
        <div className="task-filter-bar__result">
          Hiển thị <b>{shown}</b> / {total} nhiệm vụ
        </div>
      )}
    </Card>
  );

  /* ── Tab items ───────────────────────────────── */
  const tabItems = [
    {
      key: "mine",
      label: (
        <span>
          <UserOutlined /> Nhiệm vụ phụ trách
          <Tag style={{ marginLeft: 8, borderRadius: 20 }} color="blue">
            {myTasks.length}
          </Tag>
        </span>
      ),
      children: (
        <>
          <FilterBar total={myTasks.length} shown={filteredMine.length} />
          <Card>
            <TaskTable data={filteredMine} onStatusChange={updateTaskStatus} />
          </Card>
        </>
      ),
    },
    ...(canAssign
      ? [
          {
            key: "assigned",
            label: (
              <span>
                Nhiệm vụ đã giao
                <Tag style={{ marginLeft: 8, borderRadius: 20 }} color="gold">
                  {assignedTasks.length}
                </Tag>
              </span>
            ),
            children: (
              <>
                <FilterBar
                  total={assignedTasks.length}
                  shown={filteredAssigned.length}
                />
                <Card>
                  <TaskTable
                    data={filteredAssigned}
                    canScore
                    assignableUserIds={
                      new Set(assignableUsers.map((u) => u.id))
                    }
                    onScoreAssignment={(taskId, userId, userName) =>
                      setScoreModal({ taskId, userId, userName })
                    }
                    onStatusChange={updateTaskStatus}
                    onEditTask={handleEditTask}
                  />
                </Card>
              </>
            ),
          },
        ]
      : []),
    ...(canAssign
      ? [
          {
            key: "all",
            label: (
              <span>
                {user?.is_admin
                  ? "Tổng nhiệm vụ toàn tổ chức"
                  : "Tổng nhiệm vụ trong phạm vi quản lý"}
                <Tag
                  style={{ marginLeft: 8, borderRadius: 20 }}
                  color="magenta"
                >
                  {allTasks.length}
                </Tag>
              </span>
            ),
            children: (
              <>
                <FilterBar total={allTasks.length} shown={filteredAll.length} />
                <Card>
                  <TaskTable
                    data={filteredAll}
                    canScore={false} // Lãnh đạo chỉ xem tổng quan, chấm điểm ở phần nhiệm vụ đã giao
                    assignableUserIds={new Set()}
                    onStatusChange={updateTaskStatus}
                    onEditTask={handleEditTask}
                  />
                </Card>
              </>
            ),
          },
        ]
      : []),
  ];

  return (
    <Space direction="vertical" size={18} className="page">
      <div className="page-title-row">
        <Typography.Title level={3} style={{ margin: 0 }}>
          Quản lý Công việc
        </Typography.Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={loadAll}>
            Tải lại
          </Button>
          {canAssign && (
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => setOpen(true)}
            >
              Tạo nhiệm vụ
            </Button>
          )}
        </Space>
      </div>

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={tabItems}
        size="large"
        style={{ background: "transparent" }}
      />

      {/* Modal tạo/sửa nhiệm vụ */}
      <Modal
        title={editTaskId ? "Sửa nhiệm vụ" : "Tạo nhiệm vụ mới"}
        open={open}
        onOk={saveTask}
        onCancel={() => {
          setOpen(false);
          setEditTaskId(null);
          form.resetFields();
        }}
        okText={editTaskId ? "Lưu lại" : "Tạo"}
        cancelText="Huỷ"
      >
        <Form
          layout="vertical"
          form={form}
          initialValues={{
            document_type: "C",
            status: "NOT_STARTED",
            priority: "MEDIUM",
          }}
        >
          <Form.Item
            name="assigned_user_ids"
            label={`Giao cho (${assignableUsers.length} người trong phạm vi quyền)`}
            rules={[
              { required: true, message: "Vui lòng chọn người nhận việc" },
            ]}
            help={
              assignableUsers.length === 0
                ? "Bạn không có quyền giao việc cho cán bộ nào."
                : undefined
            }
          >
            <Select
              mode="multiple"
              showSearch
              optionFilterProp="label"
              options={assignedUserOptions}
              onChange={handleAssigneesChange}
              placeholder="Chọn người nhận việc theo đơn vị..."
            />
          </Form.Item>
          <Form.Item
            name="work_catalog_item_id"
            label="Mã sản phẩm/công việc theo Quyết định 283"
            rules={[{ required: true, message: "Vui lòng chọn mã công việc" }]}
          >
            <Select
              showSearch
              optionFilterProp="label"
              options={workCatalogOptions}
              loading={catalogLoading}
              disabled={!workCatalog.length}
              onChange={handleCatalogChange}
              placeholder="Chọn người nhận trước để tải danh mục phù hợp"
            />
          </Form.Item>
          <Form.Item
            name="title"
            label="Tên nhiệm vụ"
            rules={[{ required: true, message: "Vui lòng nhập tên nhiệm vụ" }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            name="deadline"
            label="Hạn xử lý (Deadline)"
            rules={[{ required: true, message: "Vui lòng chọn hạn xử lý" }]}
          >
            <DatePicker
              style={{ width: "100%" }}
              format="DD/MM/YYYY"
              placeholder="Chọn ngày..."
            />
          </Form.Item>
          <Form.Item name="description" label="Mô tả">
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item name="document_type" label="Nhóm văn bản">
            <Select
              options={["A", "B", "C", "D"].map((v) => ({
                value: v,
                label: v,
              }))}
            />
          </Form.Item>
        </Form>
      </Modal>

      {/* Modal chấm điểm */}
      <Modal
        title={`Đánh giá sản phẩm: ${scoreModal?.userName}`}
        open={!!scoreModal}
        onOk={submitScore}
        onCancel={() => {
          setScoreModal(null);
          scoreForm.resetFields();
        }}
        okText="Lưu đánh giá"
        cancelText="Huỷ"
      >
        <Form layout="vertical" form={scoreForm}>
          <Form.Item
            name="quality_percent"
            label="Mức chất lượng sản phẩm (%)"
            rules={[
              { required: true, message: "Vui lòng nhập tỷ lệ chất lượng" },
            ]}
          >
            <InputNumber
              min={0}
              max={100}
              step={0.5}
              style={{ width: "100%" }}
              size="large"
            />
          </Form.Item>
          <Form.Item
            name="major_error_count"
            label="Số lỗi nghiêm trọng"
            initialValue={0}
          >
            <InputNumber min={0} precision={0} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="late_count" label="Số lần trễ hạn" initialValue={0}>
            <InputNumber min={0} precision={0} style={{ width: "100%" }} />
          </Form.Item>
          <p style={{ color: "#64748b", fontSize: 13 }}>
            Rule Engine trừ 25% thành phần chất lượng cho mỗi lỗi nghiêm trọng
            và 25% thành phần tiến độ cho mỗi lần trễ. LLM không được sửa các tỷ
            lệ này.
          </p>
        </Form>
      </Modal>
    </Space>
  );
}
