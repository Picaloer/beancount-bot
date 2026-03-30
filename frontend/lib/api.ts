const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export type ImportLifecycleStatus = "pending" | "processing" | "classifying" | "done" | "failed";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  return res.json();
}

// Bills
export function importBill(file: File) {
  const form = new FormData();
  form.append("file", file);
  return fetch(`${API_BASE}/bills/import`, { method: "POST", body: form }).then(
    (r) => r.json()
  );
}

export function getImportStatus(importId: string) {
  return request<ImportStatus>(`/bills/import/${importId}`);
}

export function getImportDetail(importId: string) {
  return request<ImportDetail>(`/bills/import/${importId}/detail`);
}

export function listImports() {
  return request<ImportRecord[]>("/bills/imports");
}

export function deleteImport(importId: string) {
  return request<DeleteImportResult>(`/bills/import/${importId}`, { method: "DELETE" });
}

// Settings
export function getRuntimeSettings() {
  return request<RuntimeSettings>("/settings/runtime");
}

export function updateRuntimeSettings(payload: RuntimeSettingsUpdateInput) {
  return request<RuntimeSettingsUpdateResult>("/settings/runtime", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

// Transactions
export function listTransactions(params: {
  year_month?: string;
  category_l1?: string;
  direction?: string;
  page?: number;
  page_size?: number;
}) {
  const q = new URLSearchParams(
    Object.fromEntries(
      Object.entries(params)
        .filter(([, v]) => v !== undefined)
        .map(([k, v]) => [k, String(v)])
    )
  );
  return request<TransactionList>(`/transactions?${q}`);
}

export function updateCategory(
  txId: string,
  category_l1: string,
  category_l2: string | null
) {
  return request(`/transactions/${txId}/category`, {
    method: "PATCH",
    body: JSON.stringify({ category_l1, category_l2 }),
  });
}

export function getTransactionSummary() {
  return request<Record<string, { total: number; count: number }>>("/transactions/summary");
}

// Reports
export function getMonthlyReport(yearMonth: string, regenerate = false) {
  const q = regenerate ? "?regenerate=true" : "";
  return request<MonthlyReport>(`/reports/monthly/${yearMonth}${q}`);
}

export function listMonths() {
  return request<{ months: string[] }>("/reports/months");
}

export function getMerchantRanking(yearMonth?: string, limit = 10) {
  const q = new URLSearchParams({ limit: String(limit) });
  if (yearMonth) q.set("year_month", yearMonth);
  return request<MerchantRank[]>(`/reports/ranking/merchants?${q}`);
}

export function getCategoryTrends(yearMonth: string, months = 6, limit = 5) {
  const q = new URLSearchParams({ months: String(months), limit: String(limit) });
  return request<CategoryTrendResponse>(`/reports/trends/categories/${yearMonth}?${q}`);
}

export function getBudgetPlan(yearMonth: string, regenerate = false) {
  const q = regenerate ? "?regenerate=true" : "";
  return request<BudgetPlan>(`/budgets/${yearMonth}${q}`);
}

export function askFinanceQuestion(question: string) {
  return request<QueryAnswer>("/query", {
    method: "POST",
    body: JSON.stringify({ question }),
  });
}

// Categories
export function getCategoryTree() {
  return request<{
    tree: { category_l1: string; subcategories: string[] }[];
  }>("/categories");
}

export function listRules() {
  return request<CategoryRule[]>("/categories/rules");
}

export function createRule(rule: {
  match_value: string;
  category_l1: string;
  category_l2?: string;
  match_field?: "merchant" | "description" | "any";
  priority?: number;
}) {
  return request<CategoryRule>("/categories/rules", {
    method: "POST",
    body: JSON.stringify(rule),
  });
}

export function deleteRule(ruleId: string) {
  return request(`/categories/rules/${ruleId}`, { method: "DELETE" });
}

// Types
export interface ImportStatus {
  import_id: string;
  source: string;
  file_name: string;
  status: ImportLifecycleStatus;
  row_count: number;
  total_rows: number;
  processed_rows: number;
  llm_total_batches: number;
  llm_completed_batches: number;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  stage_message: string | null;
  error_message?: string | null;
  imported_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface ImportStage {
  stage_key: "parse" | "dedupe" | "classify" | "beancount" | string;
  stage_label: string;
  status: "pending" | "processing" | "done" | "failed" | string;
  message: string | null;
  started_at: string | null;
  finished_at: string | null;
}

export interface ImportSummary {
  inserted_count: number;
  duplicate_count: number;
  beancount_entry_count: number;
  rule_based_count: number;
  llm_based_count: number;
  fallback_count: number;
  low_confidence_count: number;
}

export interface ImportDetail extends ImportStatus {
  stages: ImportStage[];
  summary: ImportSummary;
}

export interface DeleteImportResult {
  import_id: string;
  deleted_transactions: number;
  affected_months: string[];
}

export type ImportRecord = ImportStatus;

export interface RuntimeSettings {
  llm_provider: "claude" | "deepseek";
  llm_model: string;
  anthropic_api_key: string;
  deepseek_api_key: string;
  llm_base_url: string;
  llm_batch_size: number;
  llm_max_concurrency: number;
  created_at: string;
  updated_at: string;
  effective_provider: string;
  effective_model: string;
}

export interface RuntimeSettingsUpdateResult extends RuntimeSettings {}

export interface RuntimeSettingsUpdateInput {
  llm_provider: "claude" | "deepseek";
  llm_model: string;
  anthropic_api_key: string;
  deepseek_api_key: string;
  llm_base_url: string;
  llm_batch_size: number;
  llm_max_concurrency: number;
}

export interface Transaction {
  id: string;
  source: string;
  direction: "expense" | "income" | "transfer";
  amount: number;
  currency: string;
  merchant: string;
  description: string;
  category_l1: string;
  category_l2: string | null;
  category_source: string;
  transaction_at: string;
}

export interface TransactionList {
  total: number;
  page: number;
  page_size: number;
  items: Transaction[];
}

export interface CategoryBreakdown {
  category_l1: string;
  amount: number;
  percentage: number;
}

export interface MerchantRank {
  merchant: string;
  total: number;
  count: number;
}

export interface WeeklyExpense {
  week: number;
  amount: number;
}

export interface CategoryTrendPoint {
  year_month: string;
  [category: string]: string | number;
}

export interface CategoryTrendSummary {
  category_l1: string;
  total: number;
}

export interface CategoryTrendResponse {
  year_month: string;
  months: string[];
  categories: string[];
  points: CategoryTrendPoint[];
  top_categories: CategoryTrendSummary[];
}

export interface BudgetCategory {
  id: string;
  category_l1: string;
  budget: number;
  spent: number;
  remaining: number;
  usage_ratio: number;
  usage_percentage: number;
  source: string;
  status: "healthy" | "warning" | "overspent";
}

export interface BudgetPlan {
  year_month: string;
  generated: boolean;
  total_budget: number;
  total_spent: number;
  remaining: number;
  usage_ratio: number;
  usage_percentage: number;
  categories: BudgetCategory[];
}

export interface QueryAnswer {
  question: string;
  intent: string;
  year_month: string;
  answer: string;
  data: Record<string, string | number | null>;
}

export interface MonthlyReport {
  year_month: string;
  total_expense: number;
  total_income: number;
  net: number;
  transaction_count: number;
  category_breakdown: CategoryBreakdown[];
  top_merchants: { merchant: string; amount: number; count: number }[];
  weekly_expense: WeeklyExpense[];
  ai_insight: string | null;
  cached: boolean;
}

export interface CategoryRule {
  id: string;
  match_field: "merchant" | "description" | "any";
  match_value: string;
  category_l1: string;
  category_l2: string | null;
  priority: number;
}
