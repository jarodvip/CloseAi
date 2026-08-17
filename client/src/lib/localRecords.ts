export type StoredRecord = {
  id: string;
  title: string;
  brandName?: string;
  primaryType: string;
  secondaryType?: string;
  diagnosis: string;
  playbook: string;
  createdAt: string;
  status?: "待拜访" | "跟进中" | "已推进" | "暂缓";
  followUpDate?: string;
  visitFeedback?: string;
  objectionOutcome?: string;
  meetingResult?: "有明确意向" | "继续评估" | "暂缓" | "失联";
  newSignals?: string;
  nextGoal?: string;
  recap?: string;
  followUpMessage?: string;
};

export const RECORDS_KEY = "gongdan-ai-local-records";
export const RECORDS_EXPORT_VERSION = 2;

export type FollowUpState = "逾期" | "今天" | "即将到期" | "已排期" | "未排期";

export type ImportPreview = {
  records: StoredRecord[];
  invalidCount: number;
  duplicateCount: number;
  newCount: number;
  conflictCount: number;
};

export function getFollowUpState(record: StoredRecord, now = new Date()): FollowUpState {
  if (!record.followUpDate) return "未排期";
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const due = new Date(`${record.followUpDate}T00:00:00`);
  const days = Math.round((due.getTime() - today.getTime()) / 86400000);
  if (days < 0) return "逾期";
  if (days === 0) return "今天";
  if (days <= 3) return "即将到期";
  return "已排期";
}

export function buildFollowUpSummary(record: StoredRecord): string {
  if (record.recap?.trim()) return record.recap;
  const parts = [record.visitFeedback, record.objectionOutcome].filter(Boolean);
  if (!parts.length) return "尚未记录拜访反馈，下一次建议先补齐客户反馈与未解决异议。";
  return `下一次攻单提示：${parts.join("；")}。优先围绕下次跟进日期 ${record.followUpDate || "待确定"}，确认一个可执行推进动作。`;
}

export function exportLocalRecords(records: StoredRecord[], exportedAt = new Date()): string {
  return JSON.stringify({ version: RECORDS_EXPORT_VERSION, exportedAt: exportedAt.toISOString(), records }, null, 2);
}

function isValidRecord(item: unknown): item is StoredRecord {
  if (!item || typeof item !== "object") return false;
  const record = item as StoredRecord;
  return typeof record.id === "string" && typeof record.title === "string" && typeof record.primaryType === "string" && typeof record.diagnosis === "string" && typeof record.playbook === "string" && typeof record.createdAt === "string";
}

export function previewImport(raw: string, existing: StoredRecord[] = []): ImportPreview {
  const parsed: unknown = JSON.parse(raw);
  const candidate = Array.isArray(parsed) ? parsed : parsed && typeof parsed === "object" && "records" in parsed ? (parsed as { records?: unknown }).records : null;
  if (!Array.isArray(candidate)) throw new Error("文件格式无效：缺少 records 数组");
  const records = candidate.filter(isValidRecord);
  const invalidCount = candidate.length - records.length;
  if (!records.length && candidate.length) throw new Error("文件格式无效：没有可导入的客户记录");
  const ids = new Set<string>();
  const unique = records.filter(record => {
    if (ids.has(record.id)) return false;
    ids.add(record.id);
    return true;
  });
  const duplicateCount = records.length - unique.length;
  const existingIds = new Set(existing.map(record => record.id));
  const conflictCount = unique.filter(record => existingIds.has(record.id)).length;
  return { records: unique, invalidCount, duplicateCount, newCount: unique.length - conflictCount, conflictCount };
}

export function importLocalRecords(raw: string): StoredRecord[] {
  return previewImport(raw).records;
}

export function mergeImportedRecords(existing: StoredRecord[], incoming: StoredRecord[], strategy: "import" | "local" = "import") {
  const incomingIds = new Set(incoming.map(record => record.id));
  if (strategy === "local") return [...existing, ...incoming.filter(record => !existing.some(item => item.id === record.id))];
  return [...incoming, ...existing.filter(record => !incomingIds.has(record.id))];
}

export function loadLocalRecords(storage: Pick<Storage, "getItem">): StoredRecord[] {
  try {
    const raw = storage.getItem(RECORDS_KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter(isValidRecord) : [];
  } catch {
    return [];
  }
}

export function saveLocalRecords(storage: Pick<Storage, "setItem">, records: StoredRecord[]) {
  storage.setItem(RECORDS_KEY, JSON.stringify(records));
}
