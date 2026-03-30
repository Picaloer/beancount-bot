"use client";

import { useEffect, useMemo, useState } from "react";
import useSWR from "swr";

import Card from "@/app/components/Card";
import PageHeader from "@/app/components/PageHeader";
import {
  getRuntimeSettings,
  updateRuntimeSettings,
  type RuntimeSettings,
  type RuntimeSettingsUpdateInput,
  type RuntimeSettingsUpdateResult,
} from "@/lib/api";

const primaryButtonClassName =
  "inline-flex items-center justify-center rounded-2xl bg-[var(--gold-400)] px-5 py-3 text-sm font-medium text-black transition hover:bg-[var(--gold-500)] disabled:cursor-not-allowed disabled:opacity-60";

const inputClassName =
  "w-full rounded-2xl border border-[rgba(212,168,67,0.2)] bg-[var(--bg-elevated)] px-4 py-3.5 text-sm text-[var(--text-primary)] outline-none transition placeholder:text-[var(--text-muted)] focus:border-[var(--gold-400)]";

const labelClassName = "text-sm font-medium text-[var(--text-primary)]";

function isMaskedSecret(value: string) {
  return value.includes("*");
}

function resolveSecretInput(nextValue: string, previousValue: string) {
  const trimmed = nextValue.trim();
  if (!trimmed) {
    return "";
  }
  if (isMaskedSecret(trimmed) && isMaskedSecret(previousValue)) {
    return previousValue;
  }
  return nextValue;
}

function getProviderKey(form: RuntimeSettingsUpdateInput) {
  return form.llm_provider === "claude" ? form.anthropic_api_key : form.deepseek_api_key;
}

function getProviderKeyPlaceholder(provider: RuntimeSettingsUpdateInput["llm_provider"]) {
  return provider === "claude" ? "sk-ant-..." : "sk-...";
}

function getProviderKeyLabel(provider: RuntimeSettingsUpdateInput["llm_provider"]) {
  return provider === "claude" ? "API Key · Claude" : "API Key · DeepSeek";
}

export default function SettingsPage() {
  const { data, mutate, isLoading } = useSWR<RuntimeSettings>("runtime-settings", getRuntimeSettings);
  const [form, setForm] = useState<RuntimeSettingsUpdateInput | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    if (!data) {
      return;
    }
    setForm(buildRuntimeSettingsForm(data));
  }, [data]);

  const providerKeyValue = useMemo(() => (form ? getProviderKey(form) : ""), [form]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!form) {
      return;
    }

    setSaving(true);
    setError(null);
    setNotice(null);

    try {
      const saved = await updateRuntimeSettings({
        ...form,
        anthropic_api_key:
          form.llm_provider === "claude"
            ? resolveSecretInput(form.anthropic_api_key, data?.anthropic_api_key || "")
            : "",
        deepseek_api_key:
          form.llm_provider === "deepseek"
            ? resolveSecretInput(form.deepseek_api_key, data?.deepseek_api_key || "")
            : "",
      });
      setForm(buildRuntimeSettingsForm(saved));
      await mutate(saved, false);
      setNotice("配置已保存，新导入任务会立即使用新的模型设置。");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "保存失败");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mx-auto max-w-5xl space-y-8">
      <PageHeader
        className="p-8 sm:p-9"
        eyebrow="Runtime Control"
        title="配置中心"
        description="只保留当前供应商所需的一组连接参数，让模型切换、Key 管理和吞吐调优更清晰。"
      />

      {error ? <MessageCard tone="error">{error}</MessageCard> : null}
      {notice ? <MessageCard tone="notice">{notice}</MessageCard> : null}

      <div className="grid gap-8 xl:grid-cols-[minmax(0,1.2fr)_360px]">
        <Card variant="surface" className="p-7 sm:p-8 lg:p-10">
          {isLoading || !form ? (
            <div className="space-y-5">
              <div className="h-6 w-40 animate-pulse rounded-full bg-white/6" />
              <div className="h-32 animate-pulse rounded-[28px] bg-white/4" />
              <div className="h-32 animate-pulse rounded-[28px] bg-white/4" />
            </div>
          ) : (
            <form className="space-y-10" onSubmit={handleSubmit}>
              <section className="space-y-6">
                <SectionHeading
                  eyebrow="Connection"
                  title="模型连接"
                  description="先选择供应商，再填写当前供应商对应的一组 API 凭证。"
                />

                <div className="grid gap-5 lg:grid-cols-2">
                  <label className="space-y-2.5">
                    <span className={labelClassName}>模型供应商</span>
                    <select
                      className={inputClassName}
                      value={form.llm_provider}
                      onChange={(event) =>
                        setForm({
                          ...form,
                          llm_provider: event.target.value as RuntimeSettingsUpdateInput["llm_provider"],
                        })
                      }
                    >
                      <option value="claude">Claude</option>
                      <option value="deepseek">DeepSeek</option>
                    </select>
                  </label>

                  <label className="space-y-2.5">
                    <span className={labelClassName}>模型名称</span>
                    <input
                      className={inputClassName}
                      value={form.llm_model}
                      onChange={(event) => setForm({ ...form, llm_model: event.target.value })}
                      placeholder="claude-haiku-4-5-20251001"
                    />
                  </label>
                </div>

                <div className="rounded-[28px] border border-[rgba(212,168,67,0.14)] bg-[rgba(255,255,255,0.02)] p-5 sm:p-6">
                  <label className="space-y-3">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <span className={labelClassName}>{getProviderKeyLabel(form.llm_provider)}</span>
                      <span className="rounded-full border border-[rgba(212,168,67,0.18)] bg-[rgba(212,168,67,0.08)] px-3 py-1 text-[11px] font-medium tracking-[0.16em] text-[var(--gold-400)] uppercase">
                        {form.llm_provider}
                      </span>
                    </div>
                    <input
                      type="password"
                      className={`${inputClassName} tracking-[0.22em] placeholder:tracking-[0.08em]`}
                      value={providerKeyValue}
                      onChange={(event) =>
                        setForm(
                          form.llm_provider === "claude"
                            ? { ...form, anthropic_api_key: event.target.value }
                            : { ...form, deepseek_api_key: event.target.value }
                        )
                      }
                      placeholder={getProviderKeyPlaceholder(form.llm_provider)}
                    />
                    <p className="text-sm leading-7 text-[var(--text-secondary)]">
                      配置中心仅展示当前供应商对应的 API Key。切换供应商后，保存时会只写入当前这一组凭证。
                    </p>
                  </label>
                </div>

                <label className="space-y-2.5">
                  <span className={labelClassName}>Base URL</span>
                  <input
                    className={inputClassName}
                    value={form.llm_base_url}
                    onChange={(event) => setForm({ ...form, llm_base_url: event.target.value })}
                    placeholder="可选，自定义 OpenAI 兼容接口地址"
                  />
                </label>
              </section>

              <section className="space-y-6 border-t border-[var(--border-subtle)] pt-8">
                <SectionHeading
                  eyebrow="Performance"
                  title="吞吐策略"
                  description="把批大小和并发拆成更舒展的双卡布局，便于快速调优。"
                />

                <div className="grid gap-5 lg:grid-cols-2">
                  <MetricField
                    label="单批交易数"
                    hint="每次请求中打包给模型的交易条数。"
                    value={form.llm_batch_size}
                    min={1}
                    max={200}
                    onChange={(value) => setForm({ ...form, llm_batch_size: value })}
                  />

                  <MetricField
                    label="最大并发数"
                    hint="同一导入任务可同时发出的 LLM 请求数。"
                    value={form.llm_max_concurrency}
                    min={1}
                    max={32}
                    onChange={(value) => setForm({ ...form, llm_max_concurrency: value })}
                  />
                </div>
              </section>

              <div className="flex flex-col gap-4 border-t border-[var(--border-subtle)] pt-7 sm:flex-row sm:items-center sm:justify-between">
                <div className="space-y-1 text-sm text-[var(--text-secondary)]">
                  <p>新配置只影响之后发起的导入任务。</p>
                  {data ? <p className="text-[var(--text-muted)]">最近更新：{formatTime(data.updated_at)}</p> : null}
                </div>
                <button type="submit" className={primaryButtonClassName} disabled={saving}>
                  {saving ? "保存中..." : "保存配置"}
                </button>
              </div>
            </form>
          )}
        </Card>

        <aside className="space-y-6 xl:sticky xl:top-8 xl:self-start">
          <Card variant="elevated" className="p-6 sm:p-7">
            <p className="text-xs uppercase tracking-[0.24em] text-[var(--gold-400)]">Current Runtime</p>
            <div className="mt-6 space-y-4 text-sm text-[var(--text-secondary)]">
              <InfoRow label="生效供应商" value={data?.effective_provider || "-"} />
              <InfoRow label="生效模型" value={data?.effective_model || "-"} />
              <InfoRow label="批大小" value={data ? String(data.llm_batch_size) : "-"} />
              <InfoRow label="并发量" value={data ? String(data.llm_max_concurrency) : "-"} />
            </div>
          </Card>

          <Card variant="surface" className="p-6 sm:p-7">
            <p className="text-xs uppercase tracking-[0.24em] text-[var(--gold-400)]">Tuning Notes</p>
            <div className="mt-5 space-y-4 text-sm leading-7 text-[var(--text-secondary)]">
              <p>批大小越高，单次请求覆盖的交易越多，通常更省 token，但响应也会更重。</p>
              <p>并发量越高，整体分类速度越快，但更容易触发 API 限流或配额抖动。</p>
              <p>切换供应商后，建议同步检查模型名称与 Base URL 是否匹配当前平台。</p>
            </div>
          </Card>
        </aside>
      </div>
    </div>
  );
}

function buildRuntimeSettingsForm(
  settings: Pick<
    RuntimeSettings | RuntimeSettingsUpdateResult,
    | "llm_provider"
    | "llm_model"
    | "anthropic_api_key"
    | "deepseek_api_key"
    | "llm_base_url"
    | "llm_batch_size"
    | "llm_max_concurrency"
  >
): RuntimeSettingsUpdateInput {
  return {
    llm_provider: settings.llm_provider,
    llm_model: settings.llm_model,
    anthropic_api_key: settings.anthropic_api_key,
    deepseek_api_key: settings.deepseek_api_key,
    llm_base_url: settings.llm_base_url,
    llm_batch_size: settings.llm_batch_size,
    llm_max_concurrency: settings.llm_max_concurrency,
  };
}

function SectionHeading({
  eyebrow,
  title,
  description,
}: {
  eyebrow: string;
  title: string;
  description: string;
}) {
  return (
    <div className="space-y-3">
      <p className="text-xs uppercase tracking-[0.24em] text-[var(--gold-400)]">{eyebrow}</p>
      <div className="space-y-2">
        <h2 className="text-2xl font-bold tracking-[-0.03em] text-[var(--text-primary)]">{title}</h2>
        <p className="max-w-2xl text-sm leading-7 text-[var(--text-secondary)]">{description}</p>
      </div>
    </div>
  );
}

function MetricField({
  hint,
  label,
  max,
  min,
  onChange,
  value,
}: {
  hint: string;
  label: string;
  max: number;
  min: number;
  onChange: (value: number) => void;
  value: number;
}) {
  return (
    <div className="rounded-[28px] border border-[rgba(212,168,67,0.14)] bg-[rgba(255,255,255,0.02)] p-5 sm:p-6">
      <label className="space-y-3">
        <span className={labelClassName}>{label}</span>
        <input
          type="number"
          min={min}
          max={max}
          className={`${inputClassName} text-lg tabular-nums`}
          value={value}
          onChange={(event) => onChange(Number(event.target.value) || min)}
        />
        <p className="text-sm leading-7 text-[var(--text-secondary)]">{hint}</p>
      </label>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[22px] border border-[var(--border-subtle)] bg-[rgba(255,255,255,0.03)] px-4 py-3.5">
      <p className="text-xs uppercase tracking-[0.18em] text-[var(--text-muted)]">{label}</p>
      <p className="mt-2 break-all text-sm font-medium leading-7 text-[var(--text-primary)]">{value}</p>
    </div>
  );
}

function MessageCard({
  children,
  tone,
}: {
  children: React.ReactNode;
  tone: "error" | "notice";
}) {
  const toneClassName =
    tone === "error"
      ? "border-rose-400/20 bg-rose-400/8 text-rose-200"
      : "border-emerald-400/20 bg-emerald-400/8 text-emerald-200";

  return <div className={`rounded-[24px] border px-5 py-4 text-sm ${toneClassName}`}>{children}</div>;
}

function formatTime(value: string) {
  return new Date(value).toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Asia/Shanghai",
  });
}
