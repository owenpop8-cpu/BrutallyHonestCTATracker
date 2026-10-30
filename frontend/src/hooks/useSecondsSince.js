import { useEffect, useState } from "react";

export function useSecondsSince(isoTimestamp) {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);

  if (!isoTimestamp) return null;

  const started = Date.parse(isoTimestamp);
  if (Number.isNaN(started)) return null;

  return Math.max(0, Math.floor((now - started) / 1000));
}