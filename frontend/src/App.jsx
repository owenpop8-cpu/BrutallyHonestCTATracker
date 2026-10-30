import { usePredictions } from "./hooks/usePredictions";
import LastUpdated from "./components/LastUpdated";
import RecommendedSummary from "./components/RecommendedSummary";
import ArrivalList from "./components/ArrivalList";
import "./App.css";

const STOP_ID = "8187";

export default function App() {
  const { data, error, loading } = usePredictions(STOP_ID);

  return (
    <main>
      <h1>BrutallyHonestCTATracker</h1>
      <LastUpdated updatedAt={data?.updated_at} />

      {loading && <p>Loading…</p>}
      {error && <p className="error">Couldn't reach the server: {error}</p>}

      {data && !data.polling_now && (
        <p className="notice">Outside the polling window, so these results may be old.</p>
      )}

      {data && data.polling_now && <RecommendedSummary arrivals={data.arrivals} />}
      {data && <ArrivalList arrivals={data.arrivals} />}
    </main>
  );
}