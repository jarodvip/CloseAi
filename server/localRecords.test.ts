import { describe, expect, it } from "vitest";
import { loadLocalRecords, saveLocalRecords } from "../client/src/lib/localRecords";

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
    const records = [{ id: "1", title: "全国化客户", primaryType: "全国化扩张型", diagnosis: "认知先行", playbook: "复习方案", createdAt: "2026-08-16T00:00:00.000Z" }];
    saveLocalRecords(storage, records);
    expect(loadLocalRecords(storage)).toEqual(records);
  });

  it("returns an empty list when browser data is invalid", () => {
    const storage = { getItem: () => "not-json" };
    expect(loadLocalRecords(storage)).toEqual([]);
  });
});
