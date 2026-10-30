export async function fetchPredictions(stopId, signal) {
  const res = await fetch(`/api/stops/${encodeURIComponent(stopId)}/predictions`, { signal });

  if (!res.ok) {
    throw new Error(
      res.status === 404
        ? "That stop isn't being tracked"
        : `Server returned ${res.status}`
    );
  }

  return res.json();
}