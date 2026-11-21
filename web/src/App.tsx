import { HashRouter, Route, Routes } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { AuthGate } from "./components/AuthGate";
import { Login } from "./pages/Login";
import { System } from "./pages/System";
import { Welcome } from "./pages/Welcome";

export function App() {
  const { t } = useTranslation();
  return (
    <HashRouter>
      <div className="mx-auto max-w-2xl px-4 py-6">
        <header className="mb-6">
          <h1 className="text-2xl font-bold">{t("app.name")}</h1>
          <p className="text-slate-500">{t("app.tagline")}</p>
        </header>
        <main>
          <Routes>
            <Route path="/welcome" element={<Welcome />} />
            <Route path="/login" element={<Login />} />
            <Route
              path="*"
              element={
                <AuthGate>
                  <Routes>
                    <Route path="/" element={<System />} />
                  </Routes>
                </AuthGate>
              }
            />
          </Routes>
        </main>
      </div>
    </HashRouter>
  );
}
