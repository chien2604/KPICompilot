import { Avatar, Tag, Tooltip } from "antd";
import {
  BankOutlined,
  SafetyCertificateOutlined,
  TeamOutlined,
  UserOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { riskColor } from "../utils/formatters";

const ROLE_LABELS = {
  LEADERSHIP: "Lãnh đạo xã",
  UNIT_HEAD: "Trưởng đơn vị",
  UNIT_DEPUTY: "Phó trưởng đơn vị",
  SPECIALIST: "Chuyên môn",
  OUT_OF_SCOPE: "Chưa áp dụng KPI",
};

const ROLE_ORDER = {
  LEADERSHIP: 1,
  UNIT_HEAD: 2,
  UNIT_DEPUTY: 3,
  SPECIALIST: 4,
  OUT_OF_SCOPE: 5,
};

/** Render all personnel as a compact, non-scrolling organization matrix. */
export default function OrgHeatmap({
  data = [],
  departments = [],
  users = [],
  ranking = [],
  compact = false,
}) {
  const navigate = useNavigate();
  const scores = Object.fromEntries(
    ranking.map((item) => [item.user_id, item.score]),
  );
  const heatmap = Object.fromEntries(
    data.map((item) => [item.department_id, item]),
  );
  const units = departments.filter((department) =>
    ["LEADERSHIP", "UNIT"].includes(department.unit_type),
  );
  const personnel = users.filter((user) => !user.is_admin);

  if (compact) {
    return (
      <div className="commune-org-summary">
        {units.map((department) => {
          const unitData = heatmap[department.id];
          const unitUsers = personnel.filter(
            (user) => user.department_id === department.id,
          );
          const color =
            unitData?.avg_kpi == null ? "#94a3b8" : riskColor(unitData.avg_kpi);

          return (
            <button
              type="button"
              className="commune-org-summary__unit"
              key={department.id}
              onClick={() => navigate("/heatmap")}
            >
              <span
                className="commune-org-summary__icon"
                style={{ color, backgroundColor: `${color}14` }}
              >
                {department.unit_type === "LEADERSHIP" ? (
                  <BankOutlined />
                ) : (
                  <TeamOutlined />
                )}
              </span>
              <span className="commune-org-summary__body">
                <strong>{department.name}</strong>
                <small>
                  {unitUsers.length} người · {unitData?.kpi_eligible_count ?? 0}{" "}
                  thuộc KPI
                </small>
              </span>
              <span className="commune-org-summary__score" style={{ color }}>
                {unitData?.avg_kpi == null ? "—" : unitData.avg_kpi}
              </span>
            </button>
          );
        })}
      </div>
    );
  }

  return (
    <div className="commune-org-chart">
      <div className="commune-org-chart__root">
        <span className="commune-org-chart__seal">
          <SafetyCertificateOutlined />
        </span>
        <div>
          <strong>ỦY BAN NHÂN DÂN XÃ NGHĨA LÂM</strong>
          <span>
            Tỉnh Nghệ An · {personnel.length} cán bộ, công chức, viên chức
          </span>
        </div>
      </div>

      <div className="commune-org-chart__units">
        {units.map((department) => {
          const unitData = heatmap[department.id];
          const unitUsers = users
            .filter(
              (user) => user.department_id === department.id && !user.is_admin,
            )
            .sort((left, right) => {
              const roleDifference =
                (ROLE_ORDER[left.organization_role] || 99) -
                (ROLE_ORDER[right.organization_role] || 99);
              return (
                roleDifference ||
                left.full_name.localeCompare(right.full_name, "vi")
              );
            });
          const color =
            unitData?.avg_kpi == null ? "#94a3b8" : riskColor(unitData.avg_kpi);

          return (
            <section className="commune-unit" key={department.id}>
              <header
                className="commune-unit__header"
                style={{ borderColor: color }}
              >
                <div>
                  <h3>{department.name}</h3>
                  <span>
                    {unitUsers.length} người ·{" "}
                    {unitData?.kpi_eligible_count ?? 0} thuộc KPI
                  </span>
                </div>
                <strong style={{ color }}>
                  {unitData?.avg_kpi == null ? "—" : unitData.avg_kpi}
                </strong>
              </header>

              <div className="commune-unit__people">
                {unitUsers.map((person) => (
                  <Tooltip
                    key={person.id}
                    title={`${person.position_title} · ${ROLE_LABELS[person.organization_role] || person.organization_role}`}
                  >
                    <button
                      type="button"
                      className="commune-person"
                      onClick={() => navigate(`/employees/${person.id}`)}
                    >
                      <Avatar
                        size={26}
                        src={person.avatar_url}
                        icon={<UserOutlined />}
                      />
                      <span className="commune-person__identity">
                        <strong>{person.full_name}</strong>
                        <small>{person.position_title}</small>
                      </span>
                      {person.is_kpi_eligible ? (
                        <span
                          className="commune-person__score"
                          style={{
                            color:
                              scores[person.id] == null
                                ? "#94a3b8"
                                : riskColor(scores[person.id]),
                          }}
                        >
                          {scores[person.id] ?? "—"}
                        </span>
                      ) : (
                        <Tag bordered={false}>Ngoài KPI</Tag>
                      )}
                    </button>
                  </Tooltip>
                ))}
              </div>
            </section>
          );
        })}
      </div>
    </div>
  );
}
