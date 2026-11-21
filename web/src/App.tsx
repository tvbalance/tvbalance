import { HashRouter, Route, Routes } from "react-router-dom";

import { AuthGate } from "./components/AuthGate";
import { Layout } from "./components/Layout";
import { ToastProvider } from "./components/ui/toast";
import { Activity } from "./pages/Activity";
import { Dashboard } from "./pages/Dashboard";
import { Login } from "./pages/Login";
import { RuleEditor } from "./pages/RuleEditor";
import { Rules } from "./pages/Rules";
import { System } from "./pages/System";
import { TvDetail } from "./pages/TvDetail";
import { Welcome } from "./pages/Welcome";

export function App() {
  return (
    <HashRouter>
      <ToastProvider>
        <Routes>
          <Route path="/welcome" element={<Welcome />} />
          <Route path="/login" element={<Login />} />
          <Route
            element={
              <AuthGate>
                <Layout />
              </AuthGate>
            }
          >
            <Route path="/" element={<Dashboard />} />
            <Route path="/tvs/:id" element={<TvDetail />} />
            <Route path="/activity" element={<Activity />} />
            <Route path="/rules" element={<Rules />} />
            <Route path="/rules/:id" element={<RuleEditor />} />
            <Route path="/system" element={<System />} />
          </Route>
        </Routes>
      </ToastProvider>
    </HashRouter>
  );
}
