import { Card } from "antd";

/** Render the stat card interface. */
export default function StatCard({
  title,
  value,
  suffix,
  precision,
  icon,
  subtext,
  tone = "blue",
}) {
  const displayValue =
    precision != null ? Number(value).toFixed(precision) : value;

  return (
    <Card className={`stat-card stat-card--${tone}`}>
      <div className="stat-card__icon">{icon}</div>
      <div className="stat-card__body">
        <div className="stat-card__title">{title}</div>
        <div className="stat-card__value-row">
          <span className="stat-card__value">{displayValue}</span>
          {suffix && <span className="stat-card__suffix">{suffix}</span>}
        </div>
        {subtext && <div className="stat-card__subtext">{subtext}</div>}
      </div>
    </Card>
  );
}
