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
