"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import useSWR from "swr";

import { SourceBadge, StatusBadge } from "@/app/components/Badge";
import Card, { cx } from "@/app/components/Card";
import EmptyState from "@/app/components/EmptyState";
import PageHeader from "@/app/components/PageHeader";
import {
  deleteImport,
  getImportStatus,
  importBill,
  listImports,
  type ImportRecord,
  type ImportStatus,
} from "@/lib/api";

const primaryButtonClassName =
  "inline-flex items-center justify-center rounded-xl bg-[var(--gold-400)] px-4 py-2.5 text-sm font-medium text-black transition hover:bg-[var(--gold-500)] disabled:cursor-not-allowed disabled:opacity-60";

const secondaryButtonClassName =
  "inline-flex items-center justify-center rounded-xl border border-[rgba(212,168,67,0.28)] bg-[rgba(255,255,255,0.02)] px-4 py-2.5 text-sm font-medium text-[var(--gold-400)] transition hover:bg-[rgba(212,168,67,0.08)] hover:text-[var(--text-primary)] disabled:cursor-not-allowed disabled:opacity-60";

export default function ImportPage() {
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [importId, setImportId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const { data: statusData } = useSWR(
    importId ? ["import-status", importId] : null,
    () => getImportStatus(importId!),
    {
      refreshInterval: (data) => (data && isTerminalStatus(data.status) ? 0 : 2000),
    }
  );

  const { data: imports = [], mutate: mutateImports } = useSWR<ImportRecord[]>("imports", listImports, {
    refreshInterval: (records) =>
      records?.some((record) => !isTerminalStatus(record.status)) ? 2000 : 0,
  });

  async function handleFile(file: File) {
    const lowerName = file.name.toLowerCase();
    if (!lowerName.endsWith(".csv") && !lowerName.endsWith(".xlsx")) {
      setError("请上传 CSV 或 XLSX 格式的账单文件");
      return;
    }

    setError(null);
    setNotice(null);
    setUploading(true);
    setImportId(null);

    try {
      const result = await importBill(file);
      if (result.import_id) {
        setImportId(result.import_id);
        setNotice("账单已收入账册，系统正在后台解析并分类。 ");
        void mutateImports();
      } else {
        setError(result.detail || "上传失败");
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "上传失败");
    } finally {
      setUploading(false);
      if (fileRef.current) {
        fileRef.current.value = "";
      }
    }
  }

  async function handleDelete(record: ImportRecord) {
    if (!canDeleteImport(record.status)) {
      return;
    }

    const confirmed = window.confirm(
      `确认删除 ${record.file_name} 吗？这会同时删除该次导入产生的交易和分录。`
    );
    if (!confirmed) {
      return;
    }

    setError(null);
    setNotice(null);
    setDeletingId(record.import_id);

    try {
      const result = await deleteImport(record.import_id);
      if (importId === record.import_id) {
        setImportId(null);
      }
      setNotice(`已删除 ${record.file_name}，移除 ${result.deleted_transactions} 条交易，可重新导入。`);
      await mutateImports();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "删除失败");
    } finally {
      setDeletingId(null);
    }
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) {
      void handleFile(file);
    }
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader
        eyebrow="Bill Intake"
        title="导入账单"
        description="把微信、支付宝或招商银行账单拖进这本暗金账册，系统会自动识别来源、解析流水并进入分类流程。"
      >
        <button type="button" className={primaryButtonClassName} onClick={() => fileRef.current?.click()}>
          选择文件
        </button>
      </PageHeader>

      <Card
        variant="bordered"
        className={cx(
          "cursor-pointer p-8 text-center transition-all sm:p-16",
          dragging ? "ring-2 ring-[var(--gold-400)] bg-[rgba(212,168,67,0.05)]" : "hover:bg-[rgba(255,255,255,0.02)]",
          uploading ? "pointer-events-none opacity-70" : ""
        )}
      >
        <button
          type="button"
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          onClick={() => fileRef.current?.click()}
          className="block w-full cursor-pointer text-center"
        >
          <input
            ref={fileRef}
            type="file"
            accept=".csv,.xlsx"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) {
                void handleFile(file);
              }
            }}
          />
          <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-[28px] border border-[rgba(212,168,67,0.2)] bg-[rgba(212,168,67,0.08)] text-[var(--gold-400)]">
            <UploadGlyph className="h-10 w-10" />
          </div>
          <h2 className="mt-6 text-2xl font-bold tracking-[-0.03em] text-[var(--text-primary)]">
            {uploading ? "账单上传中..." : "拖拽账单到此处，或点击选择文件"}
          </h2>
          <p className="mx-auto mt-3 max-w-2xl text-sm leading-7 text-[var(--text-secondary)]">
            支持微信支付 XLSX / CSV、支付宝 CSV，以及系统已接入的招商银行账单。
          </p>
          <div className="mt-6 flex flex-wrap items-center justify-center gap-2 text-xs text-[var(--text-muted)]">
            <span className="rounded-full bg-white/5 px-3 py-1">自动识别来源</span>
            <span className="rounded-full bg-white/5 px-3 py-1">后台解析与分类</span>
            <span className="rounded-full bg-white/5 px-3 py-1">支持重新导入</span>
          </div>
        </button>
      </Card>

      {notice ? <MessageCard tone="notice">{notice}</MessageCard> : null}
      {error ? <MessageCard tone="error">{error}</MessageCard> : null}

      {importId && statusData ? <ImportProgress status={statusData} /> : null}

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_340px]">
        <section className="space-y-4">
          <div>
            <h2 className="text-xl font-bold tracking-[-0.02em] text-[var(--text-primary)]">导入历史</h2>
            <p className="mt-1 text-sm text-[var(--text-secondary)]">
              删除错误导入后，可以重新上传同一份账单，重新触发解析与分类流程。
            </p>
          </div>

          {imports.length === 0 ? (
            <EmptyState
              title="还没有导入记录"
              description="上传第一份账单后，这里会以卡片列表显示文件来源、状态、时间和交易条数。"
            />
          ) : (
            <div className="space-y-3">
              {imports.map((record) => {
                const deleting = deletingId === record.import_id;
                const canDelete = canDeleteImport(record.status);

                return (
                  <Card key={record.import_id} variant="surface" className="p-5">
                    <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <p className="truncate text-base font-semibold text-[var(--text-primary)]">
                            {record.file_name}
                          </p>
                          <SourceBadge source={record.source} />
                          <StatusBadge status={record.status} />
                        </div>
                        <p className="mt-3 text-sm text-[var(--text-secondary)]">
                          {formatImportTime(record.imported_at)}
                          <span className="mx-2 text-[var(--text-muted)]">/</span>
                          <span className="tabular">{record.row_count} 条交易</span>
                        </p>
                        {record.error_message && record.status === "failed" ? (
                          <p className="mt-2 text-sm text-rose-300">{record.error_message}</p>
                        ) : null}
                      </div>

                      <div className="flex flex-wrap items-center gap-3">
                        {record.status === "done" ? (
                          <Link href="/transactions" className={secondaryButtonClassName}>
                            查看交易
                          </Link>
                        ) : null}
                        {canDelete ? (
                          <button
                            type="button"
                            onClick={() => void handleDelete(record)}
                            disabled={deleting}
                            className="inline-flex items-center justify-center rounded-xl border border-rose-400/20 bg-rose-400/10 px-4 py-2 text-sm font-medium text-rose-300 transition hover:bg-rose-400/16 disabled:cursor-not-allowed disabled:opacity-60"
                          >
                            {deleting ? "删除中..." : "删除导入"}
                          </button>
                        ) : (
                          <span className="rounded-full bg-white/5 px-3 py-1 text-xs text-[var(--text-muted)]">
                            处理中不可删除
                          </span>
                        )}
                      </div>
                    </div>
                  </Card>
                );
              })}
            </div>
          )}
        </section>

        <aside className="xl:sticky xl:top-8 xl:self-start">
          <Card variant="elevated" className="p-5">
            <p className="text-xs uppercase tracking-[0.24em] text-[var(--gold-400)]">Export Guide</p>
            <h2 className="mt-4 text-xl font-bold tracking-[-0.02em] text-[var(--text-primary)]">如何导出账单</h2>
            <div className="mt-5 space-y-4 text-sm leading-7 text-[var(--text-secondary)]">
              <div className="rounded-[22px] border border-[var(--border-subtle)] bg-[rgba(255,255,255,0.03)] p-4">
                <p className="font-semibold text-[var(--text-primary)]">微信支付</p>
                <p className="mt-2">
                  微信 → 我 → 服务 → 钱包 → 账单 → 右上角下载图标 → 用于个人对账下载 XLSX / CSV。
                </p>
              </div>
              <div className="rounded-[22px] border border-[var(--border-subtle)] bg-[rgba(255,255,255,0.03)] p-4">
                <p className="font-semibold text-[var(--text-primary)]">支付宝</p>
                <p className="mt-2">
                  支付宝 PC 端 → 账单 → 下载账单 → 交易明细 → 全部类型 → CSV 格式。
                </p>
              </div>
            </div>
          </Card>
        </aside>
      </div>
    </div>
  );
}

function ImportProgress({ status }: { status: ImportStatus }) {
  const isDone = status.status === "done";
  const isFailed = status.status === "failed";

  const steps = [
    { key: "pending", label: "等待处理" },
    { key: "processing", label: "解析账单" },
    { key: "classifying", label: "AI 分类" },
    { key: "done", label: "完成" },
  ] as const;
  const stepOrder = ["pending", "processing", "classifying", "done"] as const;
  const currentIdx = stepOrder.indexOf(status.status as (typeof stepOrder)[number]);

  return (
    <Card variant={isFailed ? "bordered" : "surface"} className="p-5 sm:p-6">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-lg font-semibold text-[var(--text-primary)]">{status.file_name}</p>
            <SourceBadge source={status.source} />
            <StatusBadge status={status.status} />
          </div>
          <p className="mt-3 text-sm text-[var(--text-secondary)]">
            来源：{sourceLabel(status.source)}
            {status.row_count > 0 ? ` / ${status.row_count} 条交易` : ""}
          </p>
        </div>

        {isDone ? (
          <Link href="/transactions" className={primaryButtonClassName}>
            查看交易
          </Link>
        ) : null}
      </div>

      {isFailed ? (
        <div className="mt-5 rounded-[22px] border border-rose-400/20 bg-rose-400/8 px-4 py-4 text-sm leading-7 text-rose-200">
          {status.error_message || "处理失败，请重试"}
        </div>
      ) : (
        <div className="mt-6 flex items-start gap-0 overflow-x-auto pb-2">
          {steps.map((step, index) => {
            const isCurrent = index === currentIdx;
            const isComplete = index < currentIdx || (isDone && index === steps.length - 1);

            return (
              <div key={step.key} className="flex min-w-[120px] flex-1 items-start gap-3">
                <div className="flex flex-col items-center">
                  <div
                    className={cx(
                      "flex h-10 w-10 items-center justify-center rounded-full border text-sm font-semibold transition-all",
                      isComplete
                        ? "border-[var(--gold-400)] bg-[var(--gold-400)] text-black"
                        : isCurrent
                          ? "border-[var(--gold-400)] bg-transparent text-[var(--gold-400)] ring-2 ring-[rgba(212,168,67,0.2)] animate-pulse"
                          : "border-white/8 bg-[var(--bg-muted)] text-[var(--text-muted)]"
                    )}
                  >
                    {isComplete ? "✓" : index + 1}
                  </div>
                  <span
                    className={cx(
                      "mt-3 text-center text-xs leading-5",
                      isComplete || isCurrent ? "text-[var(--text-primary)]" : "text-[var(--text-muted)]"
                    )}
                  >
                    {step.label}
                  </span>
                </div>
                {index < steps.length - 1 ? (
                  <div
                    className={cx(
                      "mt-5 h-0.5 flex-1 rounded-full",
                      index < currentIdx ? "bg-[var(--gold-400)]" : "bg-[var(--bg-muted)]"
                    )}
                  />
                ) : null}
              </div>
            );
          })}
        </div>
      )}
    </Card>
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

  return <div className={cx("rounded-[24px] border px-4 py-3 text-sm", toneClassName)}>{children}</div>;
}

function UploadGlyph({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
      <path d="M24 9V28" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" />
      <path d="M16.5 20.5L24 28L31.5 20.5" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M10 36.5H38" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" />
    </svg>
  );
}

function canDeleteImport(status: ImportStatus["status"]) {
  return status === "done" || status === "failed";
}

function isTerminalStatus(status: ImportStatus["status"]) {
  return status === "done" || status === "failed";
}

function formatImportTime(value: string) {
  return new Date(value).toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Asia/Shanghai",
  });
}

function sourceLabel(source: string) {
  if (source === "wechat") {
    return "微信支付";
  }
  if (source === "alipay") {
    return "支付宝";
  }
  if (source === "cmb") {
    return "招商银行";
  }
  return source;
}
