const LABEL_CLASS = {
  Reliable: "reliable",
  Shaky: "shaky",
  Unreliable: "unreliable",
  "Ghost bus": "ghost",
};

export default function ReliabilityBadge({ label, score }) {
  const variant = LABEL_CLASS[label] ?? "unknown";

  return (
    <span className={`badge badge-${variant}`}>
      {label} · {score}
    </span>
  );
}