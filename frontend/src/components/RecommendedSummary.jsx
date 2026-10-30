import VerdictBadge from "./VerdictBadge";
import { formatClock, formatSlack } from "../format";

export default function RecommendedSummary({ arrivals }) {
  if (arrivals.length === 0) return null;

  const pick = arrivals.find((a) => a.recommended);

  if (!pick) {
    return (
      <section className="summary summary-none">
        <h2>No bus looks safe right now</h2>
        <p className="summary-detail">
          None of the predicted buses is both reliable enough and early enough
          to get you to school on time.
        </p>
      </section>
    );
  }

  const variant = pick.verdict === "Safe" ? "summary-safe" : "summary-tight";

  return (
    <section className={`summary ${variant}`}>
      <h2>
        Take the {pick.route} to {pick.destination}
      </h2>
      <p className="summary-stop-by">Be at the stop by {pick.plan_for}</p>
      <p className="summary-detail">
        CTA predicts {formatClock(pick.arrival_time)} · at school{" "}
        {pick.school_arrival} · {formatSlack(pick.slack_minutes)}
      </p>
      <VerdictBadge verdict={pick.verdict} />
    </section>
  );
}