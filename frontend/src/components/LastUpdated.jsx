import { useSecondsSince } from "../hooks/useSecondsSince";

const STALE_AFTER_SECONDS = 90;

export default function LastUpdated({ updatedAt }) {
  const seconds = useSecondsSince(updatedAt);

  if (seconds === null) {
    return <p className="last-updated">Waiting for first update…</p>;
  }

  const className =
    seconds > STALE_AFTER_SECONDS
      ? "last-updated last-updated-stale"
      : "last-updated";

  return <p className={className}>Updated {seconds}s ago</p>;
}