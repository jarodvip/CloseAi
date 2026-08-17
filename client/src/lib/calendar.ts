import type { StoredRecord } from "./localRecords";

function escapeIcs(value: string) {
  return value.replace(/\\/g, "\\\\").replace(/;/g, "\\;").replace(/,/g, "\\,").replace(/\r?\n/g, "\\n");
}

function dateStamp(date: string) {
  return date.replace(/-/g, "");
}

export function buildFollowUpCalendar(records: StoredRecord[], now = new Date()) {
  const events = records.filter(record => record.followUpDate).map(record => {
    const date = record.followUpDate as string;
    const nextDay = new Date(`${date}T00:00:00`);
    nextDay.setDate(nextDay.getDate() + 1);
    const description = [
      `客户类型：${record.primaryType}${record.secondaryType ? ` / ${record.secondaryType}` : ""}`,
      `下一步提示：${buildCalendarSummary(record)}`,
      record.followUpMessage ? `跟进消息：${record.followUpMessage}` : "",
    ].filter(Boolean).join("\\n");
    return [
      "BEGIN:VEVENT",
      `UID:gongdan-${record.id}@fenous-sales`,
      `DTSTAMP:${formatUtc(now)}`,
      `DTSTART;VALUE=DATE:${dateStamp(date)}`,
      `DTEND;VALUE=DATE:${dateStamp(nextDay.toISOString().slice(0, 10))}`,
      `SUMMARY:${escapeIcs(`跟进：${record.brandName || record.title}`)}`,
      `DESCRIPTION:${escapeIcs(description)}`,
      "END:VEVENT",
    ].join("\r\n");
  });
  return ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Fenous//Gongdan AI//CN", "CALSCALE:GREGORIAN", ...events, "END:VCALENDAR", ""].join("\r\n");
}

function formatUtc(date: Date) {
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${date.getUTCFullYear()}${pad(date.getUTCMonth() + 1)}${pad(date.getUTCDate())}T${pad(date.getUTCHours())}${pad(date.getUTCMinutes())}${pad(date.getUTCSeconds())}Z`;
}

function buildCalendarSummary(record: StoredRecord) {
  if (record.nextGoal) return record.nextGoal;
  if (record.recap) return record.recap;
  return record.visitFeedback || record.objectionOutcome || "确认客户下一步推进动作";
}

export function downloadCalendar(records: StoredRecord[], filename: string) {
  const blob = new Blob([buildFollowUpCalendar(records)], { type: "text/calendar;charset=utf-8" });
  const href = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = href;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(href), 1000);
}
