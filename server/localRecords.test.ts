import { describe, expect, it } from "vitest";
import { buildFollowUpSummary, exportLocalRecords, getFollowUpState, importLocalRecords, loadLocalRecords, saveLocalRecords } from "../client/src/lib/localRecords";

function memoryStorage() {
  const values = new Map<string, string>();
  return {
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => values.set(key, value),
  };
}

describe("local deal records", () => {
  it("restores saved records after a new page session", () => {
    const storage = memoryStorage();
    const records = [{ id: "1", title: "全国化客户", brandName: "花西子", primaryType: "全国化扩张型", secondaryType: "品牌野心型", diagnosis: "认知先行", playbook: "复习方案", createdAt: "2026-08-16T00:00:00.000Z", status: "跟进中" as const, followUpDate: "2026-08-20", visitFeedback: "老板认可试点城市", objectionOutcome: "预算异议已拆成小范围测试" }];
    saveLocalRecords(storage, records);
    expect(loadLocalRecords(storage)).toEqual(records);
  });

  it("returns an empty list when browser data is invalid", () => {
    const storage = { getItem: () => "not-json" };
    expect(loadLocalRecords(storage)).toEqual([]);
  });

  it("calculates follow-up reminders and feedback summary", () => {
    const record = { id: "2", title: "待跟进客户", primaryType: "品牌野心型", diagnosis: "需要放大声量", playbook: "方案", createdAt: "2026-08-16T00:00:00.000Z", followUpDate: "2026-08-18", visitFeedback: "老板认可试点", objectionOutcome: "预算拆分" };
    expect(getFollowUpState(record, new Date("2026-08-16T12:00:00.000Z"))).toBe("即将到期");
    expect(buildFollowUpSummary(record)).toContain("老板认可试点");
  });

  it("exports and imports a versioned record package", () => {
    const records = [{ id: "3", title: "迁移客户", primaryType: "全国化扩张型", diagnosis: "扩张", playbook: "方案", createdAt: "2026-08-16T00:00:00.000Z" }];
    expect(importLocalRecords(exportLocalRecords(records))).toEqual(records);
    expect(() => importLocalRecords("{\"wrong\":true}")).toThrow("缺少 records 数组");
  });
});
