import { HashRouter, Route, Routes } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { System } from "./pages/System";

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
            <Route path="/" element={<System />} />
          </Routes>
        </main>
      </div>
    </HashRouter>
  );
}
