import { describe, expect, it } from "vitest";
import { buildFollowUpCalendar } from "../client/src/lib/calendar";
import { exportLocalRecords, mergeImportedRecords, previewImport, type StoredRecord } from "../client/src/lib/localRecords";

const record: StoredRecord = {
  id: "r-1",
  title: "花西子 · 品类开创者型",
  brandName: "花西子",
  primaryType: "品类开创者型",
  secondaryType: "品牌焕新型",
  diagnosis: "需要建立新品类认知",
  playbook: "方案",
  createdAt: "2026-08-16T00:00:00.000Z",
  followUpDate: "2026-08-22",
  nextGoal: "约老板确认试点城市",
  followUpMessage: "下周一起确认试点城市和复盘材料。",
};

describe("P1 local-first iteration", () => {
  it("previews version 2 imports and counts conflicts", () => {
    const preview = previewImport(exportLocalRecords([record]), [record]);
    expect(preview.records).toHaveLength(1);
    expect(preview.conflictCount).toBe(1);
    expect(preview.newCount).toBe(0);
  });

  it("merges with selectable conflict precedence", () => {
    const local = { ...record, title: "本机版本" };
    const incoming = { ...record, title: "导入版本" };
    expect(mergeImportedRecords([local], [incoming], "import")[0].title).toBe("导入版本");
    expect(mergeImportedRecords([local], [incoming], "local")[0].title).toBe("本机版本");
  });

  it("builds a parseable all-day ICS event", () => {
    const ics = buildFollowUpCalendar([record], new Date("2026-08-16T12:00:00Z"));
    expect(ics).toContain("BEGIN:VCALENDAR");
    expect(ics).toContain("DTSTART;VALUE=DATE:20260822");
    expect(ics).toContain("SUMMARY:跟进：花西子");
    expect(ics).toContain("约老板确认试点城市");
    expect(ics).toContain("END:VCALENDAR");
  });
});
