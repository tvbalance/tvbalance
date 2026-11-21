import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { NavLink, Outlet } from "react-router-dom";

import { useSettings } from "../api/hooks";
import i18n from "../i18n";
import { cn } from "../lib";

const ITEMS = [
  { to: "/", key: "nav.dashboard", end: true },
  { to: "/system", key: "nav.system", end: false },
] as const;

/** A sidebar on wide screens and a bottom bar on phones, around the routed page. */
export function Layout() {
  const { t } = useTranslation();
  const settings = useSettings();
  const saved = settings.data?.language;
  // The saved language is the family's choice; it wins over what the browser reported.
  useEffect(() => {
    if (saved && i18n.language.slice(0, 2) !== saved) void i18n.changeLanguage(saved);
  }, [saved]);
  const links = (
    <ul className="flex md:flex-col md:gap-1">
      {ITEMS.map((item) => (
        <li key={item.to} className="flex-1">
          <NavLink
            to={item.to}
            end={item.end}
            className={({ isActive }) =>
              cn(
                "flex min-h-14 items-center justify-center rounded-lg px-3 text-sm font-medium md:min-h-11 md:justify-start",
                isActive ? "bg-brand text-brand-ink" : "text-ink hover:bg-page",
              )
            }
          >
            {t(item.key)}
          </NavLink>
        </li>
      ))}
    </ul>
  );
  return (
    <div className="mx-auto min-h-screen max-w-5xl md:grid md:grid-cols-[12rem_1fr] md:gap-6 md:px-4 md:py-6">
      <div className="px-4 pt-4 md:px-0 md:pt-0">
        <p className="text-xl font-bold">{t("app.name")}</p>
        <nav
          aria-label={t("nav.label")}
          className="fixed inset-x-0 bottom-0 z-30 border-t border-line bg-card p-1 md:static md:mt-6 md:border-0 md:bg-transparent md:p-0"
        >
          {links}
        </nav>
      </div>
      <main className="px-4 pb-24 pt-4 md:px-0 md:pb-0 md:pt-0">
        <Outlet />
      </main>
    </div>
  );
}
