import { useEffect, useMemo, useRef, useState } from "react";
import { trpc } from "@/lib/trpc";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Download, FileDown, RotateCcw, Sparkles } from "lucide-react";
import { buildFollowUpSummary, getFollowUpState, mergeImportedRecords, previewImport, type StoredRecord } from "@/lib/localRecords";
import { downloadCalendar } from "@/lib/calendar";
import { Streamdown } from "streamdown";

type RecapResult = {
  factualSummary: string;
  customerChange: string;
  currentBarrier: string;
  confidence: "高" | "中" | "低";
  nextObjective: string;
  keyQuestions: string[];
  recommendedActions: string[];
  avoidActions: string[];
  materialsToPrepare: string[];
  followUpMessages: { style: "关系维护型" | "专业推进型" | "决策确认型"; message: string }[];
};

export function RecordsPanelV2({ records, onUpdate, onReplace, onExport }: { records: StoredRecord[]; onUpdate: (id: string, patch: Partial<StoredRecord>) => void; onReplace: (records: StoredRecord[]) => void; onExport: () => void }) {
  const [selected, setSelected] = useState<StoredRecord | null>(null);
  const [status, setStatus] = useState<StoredRecord["status"]>("待拜访");
  const [followUpDate, setFollowUpDate] = useState("");
  const [visitFeedback, setVisitFeedback] = useState("");
  const [objectionOutcome, setObjectionOutcome] = useState("");
  const [meetingResult, setMeetingResult] = useState<StoredRecord["meetingResult"]>("继续评估");
  const [newSignals, setNewSignals] = useState("");
  const [nextGoal, setNextGoal] = useState("");
  const [notice, setNotice] = useState("");
  const [recap, setRecap] = useState<RecapResult | null>(null);
  const [pendingImport, setPendingImport] = useState<{ records: StoredRecord[]; invalidCount: number; duplicateCount: number; newCount: number; conflictCount: number } | null>(null);
  const [beforeImport, setBeforeImport] = useState<StoredRecord[] | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const recapMutation = trpc.gongdan.recap.useMutation();
  const dueRecords = useMemo(() => records.filter(record => ["逾期", "今天", "即将到期"].includes(getFollowUpState(record))), [records]);

  useEffect(() => {
    if (!selected) return;
    setStatus(selected.status || "待拜访");
    setFollowUpDate(selected.followUpDate || "");
    setVisitFeedback(selected.visitFeedback || "");
    setObjectionOutcome(selected.objectionOutcome || "");
    setMeetingResult(selected.meetingResult || "继续评估");
    setNewSignals(selected.newSignals || "");
    setNextGoal(selected.nextGoal || "");
    setRecap(null);
  }, [selected?.id]);

  const saveFields = () => {
    if (!selected) return;
    const patch = { status, followUpDate, visitFeedback, objectionOutcome, meetingResult, newSignals, nextGoal };
    onUpdate(selected.id, patch);
    setSelected({ ...selected, ...patch });
    setNotice("已保存复盘信息，可以继续生成下一次攻单");
  };

  const generateRecap = () => {
    if (!selected) return;
    recapMutation.mutate({ brandName: selected.brandName || selected.title, industry: "", primaryType: selected.primaryType, secondaryType: selected.secondaryType || "", diagnosis: selected.diagnosis, strategy: selected.playbook, visitFeedback, objectionOutcome, meetingResult: meetingResult || "继续评估", newSignals, nextGoal }, { onSuccess: result => { setRecap(result as RecapResult); setNotice("已生成下一次攻单作战卡，请确认后回写记录"); } });
  };

  const applyRecap = (message = recap?.followUpMessages[0]?.message) => {
    if (!selected || !recap) return;
    const patch = { recap: recap.factualSummary + "\n\n当前阻力：" + recap.currentBarrier + "\n\n下一步目标：" + recap.nextObjective, followUpMessage: message, nextGoal: recap.nextObjective };
    onUpdate(selected.id, patch);
    setSelected({ ...selected, ...patch });
    setNotice("已将复盘结论与跟进消息写回客户记录");
  };

  const previewFile = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    try { setPendingImport(previewImport(await file.text(), records)); setNotice("导入预览已生成，请选择冲突处理方式"); } catch (error) { setNotice(error instanceof Error ? error.message : "导入失败，请检查 JSON 文件"); }
  };

  const confirmImport = (strategy: "import" | "local") => {
    if (!pendingImport) return;
    setBeforeImport(records);
    onReplace(mergeImportedRecords(records, pendingImport.records, strategy));
    setPendingImport(null);
    setNotice(`已导入 ${pendingImport.records.length} 条记录，${pendingImport.conflictCount} 条冲突按${strategy === "import" ? "导入文件优先" : "本机记录优先"}处理`);
  };

  const undoImport = () => { if (!beforeImport) return; onReplace(beforeImport); setBeforeImport(null); setNotice("已撤销最近一次导入"); };

  return <section><div className="mb-7"><div className="mb-2 text-[11px] font-black uppercase tracking-[.2em] text-[#c90019]">04 / 我的记录</div><h1 className="text-3xl font-black tracking-[-.04em] text-[#18212e] sm:text-4xl">把每一次拜访，变成下一次准备</h1><p className="mt-3 max-w-2xl text-sm leading-6 text-[#687180]">记录保存在当前浏览器。完成拜访复盘后，AI 会把真实反馈整理为下一次问题、动作、材料和可发送消息。</p></div>
    <div className="mb-5 grid gap-3 sm:grid-cols-4"><Card className="border-0 bg-[#202a36] text-white shadow-sm"><CardContent className="p-4"><div className="text-[11px] font-bold text-[#ffb1ba]">待办提醒</div><div className="mt-1 text-2xl font-black">{dueRecords.length}</div><div className="mt-1 text-xs text-white/60">逾期、今天或三天内到期</div></CardContent></Card><Card className="border-0 bg-white shadow-sm"><CardContent className="p-4"><div className="text-[11px] font-bold text-[#9aa1ac]">已排期</div><div className="mt-1 text-2xl font-black text-[#c90019]">{records.filter(record => getFollowUpState(record) === "已排期").length}</div><div className="mt-1 text-xs text-[#89919d]">已有明确下次日期</div></CardContent></Card><Card className="border-0 bg-white shadow-sm"><CardContent className="flex h-full items-center justify-between gap-2 p-4"><div><div className="text-[11px] font-bold text-[#9aa1ac]">日历</div><div className="mt-1 text-xs text-[#687180]">导出全部跟进</div></div><Button size="sm" variant="outline" onClick={() => downloadCalendar(records, `攻单跟进-${new Date().toISOString().slice(0, 10)}.ics`)} disabled={!records.some(record => record.followUpDate)}><Download className="mr-1 size-3" />ICS</Button></CardContent></Card><Card className="border-0 bg-white shadow-sm"><CardContent className="flex h-full items-center justify-between gap-2 p-4"><div><div className="text-[11px] font-bold text-[#9aa1ac]">迁移</div><div className="mt-1 text-xs text-[#687180]">版本 2 JSON</div></div><div className="flex gap-1"><Button size="sm" variant="outline" onClick={onExport} disabled={!records.length}>导出</Button><Button size="sm" variant="outline" onClick={() => fileInputRef.current?.click()}>导入</Button></div></CardContent></Card></div>
    {notice && <div className="mb-4 rounded-lg bg-[#effaf4] px-3 py-2 text-xs text-[#28784f]">{notice}</div>}<input ref={fileInputRef} type="file" accept=".json,application/json" className="hidden" onChange={previewFile} />
    {pendingImport && <Card className="mb-5 border border-[#f1d0d4] bg-[#fff8f8] shadow-none"><CardContent className="p-5"><div className="flex flex-wrap items-center justify-between gap-3"><div><div className="text-sm font-black text-[#c90019]">导入预览</div><p className="mt-1 text-xs text-[#81525a]">新增 {pendingImport.newCount} 条 · 冲突 {pendingImport.conflictCount} 条 · 重复 {pendingImport.duplicateCount} 条 · 无效 {pendingImport.invalidCount} 条</p></div><div className="flex flex-wrap gap-2"><Button size="sm" onClick={() => confirmImport("import")} className="bg-[#c90019] hover:bg-[#a90015]">导入文件优先</Button><Button size="sm" variant="outline" onClick={() => confirmImport("local")}>保留本机优先</Button></div></div></CardContent></Card>}
    {beforeImport && <div className="mb-4 flex items-center justify-between rounded-lg border border-[#e7e9ed] bg-white px-3 py-2 text-xs"><span className="text-[#687180]">最近一次导入可撤销</span><Button size="sm" variant="ghost" onClick={undoImport} className="text-[#c90019]"><RotateCcw className="mr-1 size-3" />撤销导入</Button></div>}
    {selected ? <Card className="border-0 bg-white shadow-sm"><CardContent className="p-6"><button onClick={() => setSelected(null)} className="mb-5 text-xs font-bold text-[#c90019]">← 返回记录列表</button><div className="flex flex-wrap items-center gap-2"><h2 className="text-2xl font-black">{selected.title}</h2><Badge className="bg-[#fff1f3] text-[#c90019] hover:bg-[#fff1f3]">{selected.primaryType}</Badge><Badge variant="outline">{selected.status || "待拜访"}</Badge></div><p className="mt-4 text-sm leading-6 text-[#5f6876]">{selected.diagnosis}</p><div className="mt-4 rounded-xl border border-[#f1d0d4] bg-[#fff8f8] p-4"><div className="mb-1 text-xs font-bold text-[#c90019]">下一次攻单提示</div><p className="text-sm leading-6 text-[#81525a]">{buildFollowUpSummary(selected)}</p></div><Card className="mt-6 border border-[#edf0f3] shadow-none"><CardHeader><CardTitle className="text-base">拜访复盘</CardTitle></CardHeader><CardContent className="grid gap-4 sm:grid-cols-2"><div><label className="mb-2 block text-xs font-bold text-[#384252]">推进状态</label><select value={status} onChange={event => setStatus(event.target.value as StoredRecord["status"])} className="h-11 w-full rounded-md border border-[#e1e5ea] bg-[#fbfcfd] px-3 text-sm"><option>待拜访</option><option>跟进中</option><option>已推进</option><option>暂缓</option></select></div><div><label className="mb-2 block text-xs font-bold text-[#384252]">本次结果</label><select value={meetingResult} onChange={event => setMeetingResult(event.target.value as StoredRecord["meetingResult"])} className="h-11 w-full rounded-md border border-[#e1e5ea] bg-[#fbfcfd] px-3 text-sm"><option>有明确意向</option><option>继续评估</option><option>暂缓</option><option>失联</option></select></div><div><label className="mb-2 block text-xs font-bold text-[#384252]">下次跟进日期</label><Input type="date" value={followUpDate} onChange={event => setFollowUpDate(event.target.value)} className="h-11 border-[#e1e5ea] bg-[#fbfcfd]" /></div><div><label className="mb-2 block text-xs font-bold text-[#384252]">下一次推进目标</label><Input value={nextGoal} onChange={event => setNextGoal(event.target.value)} placeholder="例如：约老板确认试点城市" className="h-11 border-[#e1e5ea] bg-[#fbfcfd]" /></div><div><label className="mb-2 block text-xs font-bold text-[#384252]">新增客户信号</label><Textarea value={newSignals} onChange={event => setNewSignals(event.target.value)} placeholder="预算、关键人、竞品动作或客户原话" className="min-h-[100px] border-[#e1e5ea] bg-[#fbfcfd]" /></div><div><label className="mb-2 block text-xs font-bold text-[#384252]">拜访反馈</label><Textarea value={visitFeedback} onChange={event => setVisitFeedback(event.target.value)} placeholder="只记录事实、客户原话和已达成共识" className="min-h-[100px] border-[#e1e5ea] bg-[#fbfcfd]" /></div><div className="sm:col-span-2"><label className="mb-2 block text-xs font-bold text-[#384252]">异议处理结果</label><Textarea value={objectionOutcome} onChange={event => setObjectionOutcome(event.target.value)} placeholder="记录异议、回应后的变化和仍未解决的顾虑" className="min-h-[100px] border-[#e1e5ea] bg-[#fbfcfd]" /></div><div className="flex flex-wrap gap-2 sm:col-span-2"><Button onClick={saveFields} variant="outline">保存复盘信息</Button><Button onClick={generateRecap} disabled={recapMutation.isPending} className="bg-[#c90019] hover:bg-[#a90015]"><Sparkles className="mr-2 size-4" />{recapMutation.isPending ? "生成中…" : "生成下一次攻单"}</Button>{selected.followUpDate && <Button variant="ghost" onClick={() => downloadCalendar([selected], `跟进-${selected.brandName || selected.title}.ics`)}>导出本条日历</Button>}</div></CardContent></Card>
      {recap && <Card className="mt-6 border border-[#f1d0d4] bg-[#fff8f8] shadow-none"><CardHeader><div className="flex flex-wrap items-center justify-between gap-2"><CardTitle className="text-base text-[#c90019]">下一次攻单作战卡</CardTitle><Badge variant="outline">判断置信度：{recap.confidence}</Badge></div></CardHeader><CardContent className="space-y-4 text-sm"><p className="leading-6 text-[#4c5664]"><b>事实摘要：</b>{recap.factualSummary}</p><p className="leading-6 text-[#4c5664]"><b>客户变化：</b>{recap.customerChange}</p><p className="leading-6 text-[#4c5664]"><b>当前阻力：</b>{recap.currentBarrier}</p><div className="grid gap-4 sm:grid-cols-2"><div><div className="mb-2 text-xs font-bold text-[#c90019]">下一次要问</div><ul className="space-y-1 text-xs leading-5 text-[#687180]">{recap.keyQuestions.map(item => <li key={item}>· {item}</li>)}</ul></div><div><div className="mb-2 text-xs font-bold text-[#c90019]">建议动作</div><ul className="space-y-1 text-xs leading-5 text-[#687180]">{recap.recommendedActions.map(item => <li key={item}>· {item}</li>)}</ul></div></div><div className="rounded-xl bg-white p-4"><div className="mb-2 flex items-center justify-between gap-2"><div className="text-xs font-bold text-[#c90019]">三种跟进消息</div><Button size="sm" variant="outline" onClick={generateRecap} disabled={recapMutation.isPending}>重新生成</Button></div><div className="space-y-3">{recap.followUpMessages.map(item => <div key={item.style} className="rounded-lg border border-[#edf0f3] p-3"><div className="mb-1 flex items-center justify-between gap-2"><Badge variant="outline" className="border-[#f1d0d4] text-[#c90019]">{item.style}</Badge><Button size="sm" variant="ghost" onClick={() => navigator.clipboard?.writeText(item.message)}>复制</Button></div><p className="leading-6 text-[#4c5664]">{item.message}</p><Button size="sm" className="mt-2 bg-[#c90019] hover:bg-[#a90015]" onClick={() => applyRecap(item.message)}>回写并采用</Button></div>)}</div></div></CardContent></Card>}
      <div className="mt-6 rounded-xl bg-[#202a36] p-5 text-sm leading-7 text-white/85"><div className="mb-2 text-xs font-bold text-[#ffb1ba]">已保存攻单方案</div><Streamdown>{selected.playbook}</Streamdown></div></CardContent></Card> : <div className="space-y-3">{records.length ? records.map(record => <button key={record.id} onClick={() => setSelected(record)} className="w-full rounded-xl border border-[#edf0f3] bg-white p-5 text-left shadow-sm transition hover:border-[#e5aab1]"><div className="flex flex-wrap items-center justify-between gap-3"><div><div className="flex items-center gap-2"><h3 className="font-black">{record.title}</h3><Badge variant="outline">{getFollowUpState(record)}</Badge></div><p className="mt-1 text-xs text-[#89919d]">{record.primaryType} · {record.createdAt.slice(0, 10)}</p></div><span className="text-xs font-bold text-[#c90019]">打开复盘 →</span></div></button>) : <Card className="border-0 bg-white shadow-sm"><CardContent className="p-10 text-center text-sm text-[#89919d]">还没有客户记录。完成一次诊断并保存攻单方案后，这里会成为你的销售复盘台。</CardContent></Card>}</div>}</section>;
}
