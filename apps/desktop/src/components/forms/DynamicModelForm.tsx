import { useEffect, useRef, useState, type RefObject } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../ui/Button";
import { Input } from "../ui/Input";
import { ParamFieldLabel, paramOptionLabel } from "../ui/ParamFieldLabel";
import { Slider } from "../ui/Slider";
import { Switch } from "../ui/Switch";
import { api, ApiError } from "../../lib/api";
import type { ModelParameter } from "../../lib/api";

function matchesCondition(
  values: Record<string, unknown>,
  condition?: Record<string, unknown>,
): boolean {
  if (!condition) return true;
  for (const [key, expected] of Object.entries(condition)) {
    const actual = values[key];
    if (typeof expected === "boolean") {
      if (Boolean(actual) !== expected) return false;
    } else if (actual !== expected) {
      return false;
    }
  }
  return true;
}

function isParamVisible(param: ModelParameter, values: Record<string, unknown>): boolean {
  return matchesCondition(values, param.visible_when);
}

function isParamRequired(param: ModelParameter, values: Record<string, unknown>): boolean {
  if (param.required_when) {
    return matchesCondition(values, param.required_when);
  }
  return Boolean(param.required);
}

function defaultValue(param: ModelParameter): unknown {
  if (param.default !== undefined && param.default !== null) {
    return param.default;
  }
  if (param.type === "switch") return false;
  if (param.type === "image_urls") return [];
  if (param.type === "select" && param.options?.length) return param.options[0];
  return "";
}

export function DynamicModelForm({
  parameters,
  onChange,
  initialValues,
  promptRef,
  promptPlaceholderKey = "images.promptPlaceholder",
  uploadLabelsKey = "images",
}: {
  parameters: ModelParameter[];
  onChange: (values: Record<string, unknown>) => void;
  initialValues?: Record<string, unknown>;
  promptRef?: RefObject<HTMLTextAreaElement | null>;
  promptPlaceholderKey?: string;
  uploadLabelsKey?: "images" | "video" | "audio";
}) {
  const { t } = useTranslation();
  const [values, setValues] = useState<Record<string, unknown>>({});
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [activeUploadParam, setActiveUploadParam] = useState<string | null>(null);
  const [singleUpload, setSingleUpload] = useState(false);

  useEffect(() => {
    const initial: Record<string, unknown> = {};
    for (const param of parameters) {
      initial[param.name] = defaultValue(param);
    }
    const merged = { ...initial, ...initialValues };
    setValues(merged);
    onChange(merged);
  }, [parameters, initialValues]);

  const update = (name: string, value: unknown) => {
    setValues((prev) => {
      const next = { ...prev, [name]: value };
      onChange(next);
      return next;
    });
  };

  const handleImageUpload = async (param: ModelParameter, files: FileList | null) => {
    if (!files?.length) return;

    setUploading(true);
    setUploadError(null);
    try {
      const file = files[0];
      const url = await api.uploadChatImage(file);

      if (param.type === "image_url") {
        update(param.name, url);
        return;
      }

      const maxItems = param.max_items ?? 2;
      const current = (values[param.name] as string[] | undefined) ?? [];
      const remaining = maxItems - current.length;
      if (remaining <= 0) return;

      const uploaded: string[] = [];
      for (const item of Array.from(files).slice(0, remaining)) {
        const itemUrl = item === file ? url : await api.uploadChatImage(item);
        uploaded.push(itemUrl);
      }
      update(param.name, [...current, ...uploaded]);
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : t(`${uploadLabelsKey}.uploadError`);
      setUploadError(message);
    } finally {
      setUploading(false);
    }
  };

  const removeImageUrl = (paramName: string, url: string) => {
    const current = (values[paramName] as string[] | undefined) ?? [];
    update(
      paramName,
      current.filter((item) => item !== url),
    );
  };

  const openUpload = (param: ModelParameter, single: boolean) => {
    setActiveUploadParam(param.name);
    setSingleUpload(single);
    fileInputRef.current?.click();
  };

  return (
    <div className="flex flex-col gap-4">
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        multiple={!singleUpload}
        className="hidden"
        onChange={(e) => {
          const targetParam = parameters.find((p) => p.name === activeUploadParam);
          if (targetParam) {
            void handleImageUpload(targetParam, e.target.files);
          }
          e.target.value = "";
        }}
      />
      {parameters.filter((param) => isParamVisible(param, values)).map((param) => (
        <div
          key={param.name}
          className="group/field relative z-0 flex flex-col gap-1.5 hover:z-40 focus-within:z-40"
        >
          <ParamFieldLabel
            name={param.name}
            required={isParamRequired(param, values)}
          />

          {param.type === "textarea" && (
            <textarea
              ref={param.name === "prompt" ? promptRef : undefined}
              className="input-field min-h-28 resize-y"
              value={String(values[param.name] ?? "")}
              maxLength={param.max_length}
              onChange={(e) => update(param.name, e.target.value)}
              placeholder={
                param.name === "prompt"
                  ? t(promptPlaceholderKey)
                  : param.name === "style"
                    ? t("audio.stylePlaceholder", { defaultValue: "" }) || undefined
                    : undefined
              }
            />
          )}

          {param.type === "text" && (
            <Input
              value={String(values[param.name] ?? "")}
              maxLength={param.max_length}
              onChange={(e) => update(param.name, e.target.value)}
            />
          )}

          {param.type === "select" && (
            <select
              className="input-field"
              value={String(values[param.name] ?? "")}
              onChange={(e) => update(param.name, e.target.value)}
            >
              {(param.options ?? []).map((opt) => (
                <option key={opt} value={opt}>
                  {paramOptionLabel(t, param.name, opt)}
                </option>
              ))}
            </select>
          )}

          {param.type === "switch" && (
            <Switch
              checked={Boolean(values[param.name])}
              onChange={(v) => update(param.name, v)}
            />
          )}

          {param.type === "number" && param.name === "cfg_scale" && (
            <Slider
              value={Number(values[param.name] ?? 0.5)}
              min={0}
              max={1}
              step={0.05}
              onChange={(v) => update(param.name, v)}
            />
          )}

          {param.type === "number" && param.name !== "cfg_scale" && (
            <Input
              type="number"
              value={String(values[param.name] ?? "")}
              onChange={(e) => update(param.name, Number(e.target.value))}
            />
          )}

          {param.type === "image_url" && (
            <div className="flex flex-col gap-2">
              <Input
                value={String(values[param.name] ?? "")}
                onChange={(e) => update(param.name, e.target.value)}
                placeholder={t(`${uploadLabelsKey}.urlPlaceholder`)}
              />
              <Button
                type="button"
                variant="outline"
                disabled={uploading}
                onClick={() => openUpload(param, true)}
              >
                {uploading ? t(`${uploadLabelsKey}.uploading`) : t(`${uploadLabelsKey}.addReference`)}
              </Button>
              {uploadError && (
                <p className="text-sm text-status-error">{uploadError}</p>
              )}
            </div>
          )}

          {param.type === "image_urls" && (
            <div className="flex flex-col gap-2">
              <div className="flex flex-wrap gap-2">
                {((values[param.name] as string[] | undefined) ?? []).map((url) => (
                  <div
                    key={url}
                    className="flex items-center gap-2 rounded-lg border border-[var(--glass-border)] px-2 py-1 text-xs"
                  >
                    <span className="max-w-40 truncate">{url}</span>
                    <button
                      type="button"
                      className="text-status-error"
                      onClick={() => removeImageUrl(param.name, url)}
                    >
                      {t(`${uploadLabelsKey}.removeReference`)}
                    </button>
                  </div>
                ))}
              </div>
              <Button
                type="button"
                variant="outline"
                disabled={
                  uploading ||
                  ((values[param.name] as string[] | undefined) ?? []).length >=
                    (param.max_items ?? 2)
                }
                onClick={() => openUpload(param, false)}
              >
                {uploading ? t(`${uploadLabelsKey}.uploading`) : t(`${uploadLabelsKey}.addReference`)}
              </Button>
              {uploadError && (
                <p className="text-sm text-status-error">{uploadError}</p>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
