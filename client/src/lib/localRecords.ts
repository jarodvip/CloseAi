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
};

export const RECORDS_KEY = "gongdan-ai-local-records";
export const RECORDS_EXPORT_VERSION = 1;

export type FollowUpState = "逾期" | "今天" | "即将到期" | "已排期" | "未排期";

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
  const parts = [record.visitFeedback, record.objectionOutcome].filter(Boolean);
  if (!parts.length) return "尚未记录拜访反馈，下一次建议先补齐客户反馈与未解决异议。";
  return `下一次攻单提示：${parts.join("；")}。优先围绕下次跟进日期 ${record.followUpDate || "待确定"}，确认一个可执行推进动作。`;
}

export function exportLocalRecords(records: StoredRecord[], exportedAt = new Date()): string {
  return JSON.stringify({ version: RECORDS_EXPORT_VERSION, exportedAt: exportedAt.toISOString(), records }, null, 2);
}

export function importLocalRecords(raw: string): StoredRecord[] {
  const parsed: unknown = JSON.parse(raw);
  const candidate = Array.isArray(parsed) ? parsed : (parsed && typeof parsed === "object" && "records" in parsed ? (parsed as { records?: unknown }).records : null);
  if (!Array.isArray(candidate)) throw new Error("文件格式无效：缺少 records 数组");
  const valid = candidate.filter((item): item is StoredRecord => Boolean(item && typeof item === "object" && typeof (item as StoredRecord).id === "string" && typeof (item as StoredRecord).title === "string" && typeof (item as StoredRecord).primaryType === "string" && typeof (item as StoredRecord).diagnosis === "string" && typeof (item as StoredRecord).playbook === "string" && typeof (item as StoredRecord).createdAt === "string"));
  if (!valid.length && candidate.length) throw new Error("文件格式无效：没有可导入的客户记录");
  return valid;
}

export function loadLocalRecords(storage: Pick<Storage, "getItem">): StoredRecord[] {
  try {
    const raw = storage.getItem(RECORDS_KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed as StoredRecord[] : [];
  } catch {
    return [];
  }
}

export function saveLocalRecords(storage: Pick<Storage, "setItem">, records: StoredRecord[]) {
  storage.setItem(RECORDS_KEY, JSON.stringify(records));
}
