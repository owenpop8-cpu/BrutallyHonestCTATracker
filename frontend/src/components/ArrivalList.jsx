import ReliabilityBadge from "./ReliabilityBadge";
import VerdictBadge from "./VerdictBadge";
import { formatClock, formatSlack } from "../format";

const DIMMED_VERDICTS = new Set(["Too late", "Don't count on it"]);

function formatCountdown(minutesAway) {
  if (minutesAway === "DUE") return "Due";
  return `${minutesAway} min`;
}

function rowClass(arrival) {
  const classes = ["arrival"];
  if (arrival.recommended) classes.push("arrival-recommended");
  if (DIMMED_VERDICTS.has(arrival.verdict)) classes.push("arrival-dimmed");
  return classes.join(" ");
}

export default function ArrivalList({ arrivals }) {
  if (arrivals.length === 0) {
    return <p className="empty">No buses predicted right now.</p>;
  }

  return (
    <ul className="arrivals">
      {arrivals.map((a) => (
        <li key={a.vehicle_id} className={rowClass(a)}>
          {a.recommended && <span className="recommended-tag">Recommended</span>}

          <div className="arrival-main">
            <span className="route">{a.route}</span>
            <span className="destination">{a.destination}</span>
            <span className="countdown">{formatCountdown(a.minutes_away)}</span>
            <span className="clock">{formatClock(a.arrival_time)}</span>
          </div>

          <div className="arrival-details">
            <div className="badges">
              <ReliabilityBadge label={a.label} score={a.score} />
              <VerdictBadge verdict={a.verdict} />
            </div>

            {a.plan_for !== null && (
              <p className="timing">
                Plan for {a.plan_for} · at school {a.school_arrival} ·{" "}
                {formatSlack(a.slack_minutes)}
              </p>
            )}

            {a.flags.length > 0 ? (
              <ul className="flags">
                {a.flags.map((flag) => (
                  <li key={flag}>{flag}</li>
                ))}
              </ul>
            ) : (
              <p className="no-flags">No problems detected</p>
            )}
          </div>
        </li>
      ))}
    </ul>
  );
}