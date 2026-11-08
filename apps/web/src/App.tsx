import { Navigate, Route, Routes } from "react-router-dom";
import { RequireAuth } from "./components/RequireAuth";
import { GlobalHeader } from "./components/GlobalHeader";
import { LoginPage } from "./routes/LoginPage";
import { OnlineWorkspacePage } from "./routes/OnlineWorkspacePage";
import { ProjectWorkspacePage } from "./routes/ProjectWorkspacePage";

export default function App() {
  return (
    <div className="app">
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/*"
          element={
            <RequireAuth>
              <GlobalHeader />
              <Routes>
                <Route path="/" element={<OnlineWorkspacePage />} />
                <Route path="/projects/:projectId" element={<ProjectWorkspacePage />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </RequireAuth>
          }
        />
      </Routes>
    </div>
  );
}
