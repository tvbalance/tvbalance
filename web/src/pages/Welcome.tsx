import { useTranslation } from "react-i18next";

export function Welcome() {
  const { t } = useTranslation();
  return <h2 className="text-xl font-semibold">{t("welcome.title")}</h2>;
}
