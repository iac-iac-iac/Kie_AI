import { useTranslation } from "react-i18next";
import { Card, CardTitle } from "../../components/ui/Card";
import { openExternal } from "../../lib/openExternal";

const REPO_URL = "https://github.com/iac-iac-iac/Kie_AI";
const AUTHOR_EMAIL = "i@iac-iac.ru";

export function CreditsTab() {
  const { t } = useTranslation();

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardTitle>{t("credits.title")}</CardTitle>
        <p className="mt-2 text-sm text-muted">{t("credits.description")}</p>

        <dl className="mt-4 flex flex-col gap-4 text-sm">
          <div>
            <dt className="text-muted">{t("credits.author")}</dt>
            <dd className="mt-1 font-medium text-primary">iac</dd>
          </div>

          <div>
            <dt className="text-muted">{t("credits.email")}</dt>
            <dd className="mt-1">
              <button
                type="button"
                className="text-accent underline-offset-2 hover:underline"
                onClick={() => void openExternal(`mailto:${AUTHOR_EMAIL}`)}
              >
                {AUTHOR_EMAIL}
              </button>
            </dd>
          </div>

          <div>
            <dt className="text-muted">{t("credits.repository")}</dt>
            <dd className="mt-1">
              <button
                type="button"
                className="text-accent break-all underline-offset-2 hover:underline"
                onClick={() => void openExternal(REPO_URL)}
              >
                {REPO_URL}
              </button>
            </dd>
          </div>
        </dl>
      </Card>

      <Card>
        <CardTitle>{t("credits.stack")}</CardTitle>
        <p className="mt-2 text-sm text-muted">{t("credits.stackBody")}</p>
      </Card>
    </div>
  );
}
