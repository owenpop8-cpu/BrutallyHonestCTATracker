const VERDICT_CLASS = {
  Safe: "safe",
  Tight: "tight",
  "Too late": "late",
  "Don't count on it": "ghost",
  "Unknown route": "unknown",
  "Unknown time": "unknown",
};

export default function VerdictBadge({ verdict }) {
  const variant = VERDICT_CLASS[verdict] ?? "unknown";

  return <span className={`badge badge-${variant}`}>{verdict}</span>;
}