import { Navigate, Route, Routes } from "react-router-dom";
import { TopNav } from "./components/nav/TopNav";
import { OverviewPage } from "./pages/OverviewPage";
import { HistoryPage } from "./pages/HistoryPage";
import { ReportsPage } from "./pages/ReportsPage";

export default function App() {
  return (
    <>
      <TopNav />
      <main className="app-shell">
        <Routes>
          <Route path="/" element={<OverviewPage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/reports" element={<ReportsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </>
  );
}
