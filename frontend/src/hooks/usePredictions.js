import { useEffect, useState } from "react";
import { fetchPredictions } from "../api";

const REFRESH_MS = 10_000;

export function usePredictions(stopId) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const controller = new AbortController();

    async function load() {
      try {
        const result = await fetchPredictions(stopId, controller.signal);
        setData(result);
        setError(null);
      } catch (err) {
        if (err.name === "AbortError") return;
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }

    load();
    const timer = setInterval(load, REFRESH_MS);

    return () => {
      controller.abort();
      clearInterval(timer);
    };
  }, [stopId]);

  return { data, error, loading };
}