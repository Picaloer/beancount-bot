"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import useSWR from "swr";
import {
  deleteImport,
  getImportStatus,
  importBill,
  listImports,
  type ImportRecord,
  type ImportStatus,
} from "@/lib/api";

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

  const { data: imports = [], mutate: mutateImports } = useSWR<ImportRecord[]>(
    "imports",
    listImports,
    {
      refreshInterval: (records) =>
        records?.some((record) => !isTerminalStatus(record.status)) ? 2000 : 0,
    }
  );

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
        setNotice("账单已上传，系统正在后台处理");
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
    <div className="mx-auto max-w-3xl space-y-8">
      <div>
        <h1 className="text-2xl font-bold">导入账单</h1>
        <p className="mt-1 text-sm text-gray-500">支持微信支付 XLSX/CSV、支付宝 CSV，自动识别来源</p>
      </div>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => fileRef.current?.click()}
        className={`
          cursor-pointer rounded-2xl border-2 border-dashed p-16 text-center transition-all
          ${dragging ? "border-indigo-500 bg-indigo-50" : "border-gray-300 hover:border-indigo-400 hover:bg-gray-50"}
          ${uploading ? "pointer-events-none opacity-60" : ""}
        `}
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
        <div className="mb-4 text-5xl">{uploading ? "⏳" : "📂"}</div>
        <p className="font-medium text-gray-700">
          {uploading ? "上传中..." : "拖拽 CSV / XLSX 文件到此处，或点击选择文件"}
        </p>
        <p className="mt-2 text-sm text-gray-400">支持微信支付账单、支付宝账单</p>
      </div>

      {notice && (
        <div className="rounded-xl border border-green-200 bg-green-50 p-4 text-sm text-green-700">
          {notice}
        </div>
      )}

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {importId && statusData && <ImportProgress status={statusData} />}

      <section className="space-y-4">
        <div className="flex items-end justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">导入历史</h2>
            <p className="mt-1 text-sm text-gray-500">删除错误导入后，可以重新上传同一份账单触发新的分类流程</p>
          </div>
        </div>

        <div className="space-y-3">
          {imports.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-gray-200 bg-white p-8 text-center text-sm text-gray-400">
              暂无导入记录
            </div>
          ) : (
            imports.map((record) => {
              const deleting = deletingId === record.import_id;
              const canDelete = canDeleteImport(record.status);

              return (
                <div key={record.import_id} className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
                  <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="truncate font-semibold text-gray-900">{record.file_name}</p>
                        <SourceBadge source={record.source} />
                        <StatusBadge status={record.status} />
                      </div>
                      <p className="mt-2 text-sm text-gray-500">
                        {formatImportTime(record.imported_at)}
                        {` · ${record.row_count} 条交易`}
                      </p>
                      {record.error_message && record.status === "failed" && (
                        <p className="mt-2 text-sm text-red-600">{record.error_message}</p>
                      )}
                    </div>

                    <div className="flex items-center gap-3">
                      {record.status === "done" && (
                        <Link
                          href="/transactions"
                          className="text-sm font-medium text-indigo-600 transition-colors hover:text-indigo-700"
                        >
                          查看交易
                        </Link>
                      )}
                      {canDelete ? (
                        <button
                          type="button"
                          onClick={() => void handleDelete(record)}
                          disabled={deleting}
                          className="rounded-lg border border-red-200 px-3 py-1.5 text-sm font-medium text-red-600 transition-colors hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                          {deleting ? "删除中..." : "删除导入"}
                        </button>
                      ) : (
                        <span className="text-xs text-gray-400">处理中不可删除</span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </section>

      <div className="space-y-3 rounded-xl bg-blue-50 p-5 text-sm text-blue-800">
        <p className="font-semibold">如何导出账单？</p>
        <div>
          <p className="font-medium">微信支付：</p>
          <p className="mt-0.5 text-blue-700">微信 → 我 → 服务 → 钱包 → 账单 → 右上角下载图标 → 用于个人对账下载 XLSX/CSV</p>
        </div>
        <div>
          <p className="font-medium">支付宝：</p>
          <p className="mt-0.5 text-blue-700">支付宝 PC 端 → 账单 → 下载账单 → 交易明细 → 全部类型 → CSV 格式</p>
        </div>
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
  ];
  const stepOrder = ["pending", "processing", "classifying", "done"];
  const currentIdx = stepOrder.indexOf(status.status);

  return (
    <div className={`rounded-xl border p-5 ${isFailed ? "border-red-200 bg-red-50" : "border-gray-200 bg-white"}`}>
      <div className="mb-4 flex items-center justify-between gap-4">
        <div>
          <p className="truncate font-semibold text-gray-900">{status.file_name}</p>
          <p className="mt-0.5 text-xs text-gray-400">
            来源: {status.source === "wechat" ? "微信支付" : "支付宝"}
            {status.row_count > 0 && ` · ${status.row_count} 条交易`}
          </p>
        </div>
        {isDone && (
          <Link
            href="/transactions"
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm text-white transition-colors hover:bg-indigo-700"
          >
            查看交易 →
          </Link>
        )}
      </div>

      {isFailed ? (
        <p className="text-sm text-red-600">{status.error_message || "处理失败，请重试"}</p>
      ) : (
        <div className="flex items-center gap-2">
          {steps.map((step, index) => (
            <div key={step.key} className="flex flex-1 items-center gap-2">
              <div className="flex flex-1 flex-col items-center gap-1">
                <div
                  className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold
                    ${index <= currentIdx ? "bg-indigo-600 text-white" : "bg-gray-200 text-gray-400"}`}
                >
                  {index < currentIdx ? "✓" : index + 1}
                </div>
                <span className={`text-xs ${index <= currentIdx ? "font-medium text-indigo-700" : "text-gray-400"}`}>
                  {step.label}
                </span>
              </div>
              {index < steps.length - 1 && (
                <div className={`-mt-4 h-0.5 flex-1 ${index < currentIdx ? "bg-indigo-500" : "bg-gray-200"}`} />
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function SourceBadge({ source }: { source: string }) {
  const map: Record<string, string> = { wechat: "微信", alipay: "支付宝" };
  return (
    <span className="rounded-full bg-blue-100 px-2 py-0.5 text-xs text-blue-700">
      {map[source] ?? source}
    </span>
  );
}

function StatusBadge({ status }: { status: ImportStatus["status"] }) {
  const map: Record<ImportStatus["status"], { label: string; cls: string }> = {
    done: { label: "完成", cls: "bg-green-100 text-green-700" },
    pending: { label: "等待中", cls: "bg-yellow-100 text-yellow-700" },
    processing: { label: "处理中", cls: "bg-blue-100 text-blue-700" },
    classifying: { label: "分类中", cls: "bg-purple-100 text-purple-700" },
    failed: { label: "失败", cls: "bg-red-100 text-red-700" },
  };
  const { label, cls } = map[status];
  return <span className={`rounded-full px-2 py-0.5 text-xs ${cls}`}>{label}</span>;
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
  });
}
