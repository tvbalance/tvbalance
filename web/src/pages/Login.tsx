import { useTranslation } from "react-i18next";

export function Login() {
  const { t } = useTranslation();
  return <h2 className="text-xl font-semibold">{t("login.title")}</h2>;
}
