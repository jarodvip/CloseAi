import { forwardRef, useEffect, useMemo, useRef, useState } from "react";
import { AIChatBox } from "@/components/AIChatBox";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Streamdown } from "streamdown";
import { trpc } from "@/lib/trpc";
import { cn } from "@/lib/utils";
import { loadLocalRecords, saveLocalRecords, type StoredRecord } from "@/lib/localRecords";
import { buildCustomerProfile, type CustomerProfile } from "@/lib/customerProfile";
import { ArrowRight, Bookmark, BrainCircuit, CheckCircle2, ChevronRight, CircleHelp, Clock3, Download, FileDown, FileText, LayoutGrid, ListChecks, Map, MessageCircle, Search, ShieldCheck, Sparkles, Target, UserRound } from "lucide-react";

const navItems = [
  { id: "diagnose", label: "客户诊断", icon: BrainCircuit },
  { id: "assistant", label: "攻单助手", icon: MessageCircle },
  { id: "types", label: "七大类型", icon: LayoutGrid },
  { id: "objections", label: "异议速查", icon: CircleHelp },
  { id: "records", label: "我的记录", icon: Bookmark },
] as const;

type SectionId = typeof navItems[number]["id"];
type FormState = { industry: string; scale: string; keywords: string; competition: string; goal: string; background: string };
type ChatMessage = { role: "user" | "assistant"; content: string };
type Playbook = { primaryType: string; secondaryType: string; confidence: string; evidence: string[]; diagnosis: string; strategy: string; steps: { name: string; action: string; output: string }[]; breakIce: string; coreTalk: string; objections: { objection: string; concern: string; response: string }[]; nextAction: string; matchedCases: string[] };

function toReviewMarkdown(playbook: Playbook, profile: CustomerProfile) {
  return `## 客户画像：${profile.title}\n\n${profile.summary}\n\n- **发展阶段：** ${profile.customerStage}\n- **决策驱动力：** ${profile.decisionDriver}\n- **市场张力：** ${profile.marketTension}\n- **拜访目标：** ${profile.visitGoal}\n\n## 攻单结论：${playbook.primaryType}\n\n**次类型：** ${playbook.secondaryType}  \n**判断置信度：** ${playbook.confidence}\n\n### 判断依据\n${playbook.evidence.map(item => `- ${item}`).join("\n")}\n\n### 处境点破\n${playbook.diagnosis}\n\n### 攻单策略\n${playbook.strategy}\n\n### 攻单五步\n${playbook.steps.map((step, index) => `${index + 1}. **${step.name}**：${step.action}；产出：${step.output}`).join("\n")}\n\n### 一句话破冰\n> ${playbook.breakIce}\n\n### 核心沟通话术\n> ${playbook.coreTalk}\n\n### 建议下一步\n${playbook.nextAction}\n\n### 匹配案例\n${playbook.matchedCases.map(item => `- ${item}`).join("\n")}`;
}

export default function Home() {
  const [section, setSection] = useState<SectionId>("diagnose");
  const [form, setForm] = useState<FormState>({ industry: "", scale: "", keywords: "", competition: "", goal: "", background: "" });
  const [playbook, setPlaybook] = useState<Playbook | null>(null);
  const [search, setSearch] = useState("");
  const knowledgeQuery = trpc.gongdan.knowledge.useQuery();
  const diagnose = trpc.gongdan.diagnose.useMutation({ onSuccess: data => { setPlaybook(data as Playbook); setSection("diagnose"); } });
  const chat = trpc.gongdan.chat.useMutation();
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [records, setRecords] = useState<StoredRecord[]>([]);

  useEffect(() => {
    try {
      setRecords(loadLocalRecords(window.localStorage));
    } catch { setRecords([]); }
  }, []);

  const submitDiagnosis = () => diagnose.mutate(form);
  const update = (key: keyof typeof form, value: string) => setForm(prev => ({ ...prev, [key]: value }));
  const filteredTypes = useMemo(() => (knowledgeQuery.data?.customerTypes ?? []).filter(type => `${type.name}${type.short}${type.entry}${type.signals.join("")}`.toLowerCase().includes(search.toLowerCase())), [knowledgeQuery.data, search]);
  const sendChat = (content: string) => {
    const next = [...chatMessages, { role: "user" as const, content }];
    setChatMessages(next);
    chat.mutate({ messages: next }, { onSuccess: result => setChatMessages(prev => [...prev, { role: "assistant", content: result.content }]) });
  };
  const savePlaybook = () => {
    if (!playbook) return;
    const profile = buildCustomerProfile(form, playbook);
    const record: StoredRecord = { id: `${Date.now()}`, title: `${playbook.primaryType} · ${form.industry || "客户诊断"}`, primaryType: playbook.primaryType, diagnosis: playbook.diagnosis, playbook: toReviewMarkdown(playbook, profile), createdAt: new Date().toISOString() };
    setRecords(previous => {
      const next = [record, ...previous];
      saveLocalRecords(window.localStorage, next);
      return next;
    });
  };

  return <div className="min-h-screen bg-[#f7f8fa] text-[#19212d]">
    <header className="sticky top-0 z-30 border-b border-[#e7e9ed] bg-white/90 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-[1500px] items-center justify-between px-4 sm:px-8">
        <div className="flex items-center gap-3"><div className="flex size-9 items-center justify-center rounded-xl bg-[#c90019] text-white shadow-[0_5px_16px_rgba(201,0,25,.22)]"><Target className="size-5" /></div><div><div className="text-[15px] font-black tracking-[.16em] text-[#c90019]">攻单 AI</div><div className="text-[10px] font-semibold tracking-[.18em] text-[#8b929e]">分众销售作战台</div></div></div>
        <div className="hidden items-center gap-2 text-xs text-[#687180] md:flex"><ShieldCheck className="size-4 text-[#c90019]" />基于七大类型与攻单五步法</div>
        <Badge className="border-[#f0d0d4] bg-[#fff7f8] text-[#c90019] hover:bg-[#fff7f8]">免登录可用</Badge>
      </div>
    </header>
    <div className="mx-auto flex max-w-[1500px] flex-col lg:flex-row">
      <aside className="border-b border-[#e7e9ed] bg-white lg:sticky lg:top-16 lg:h-[calc(100vh-4rem)] lg:w-[235px] lg:shrink-0 lg:border-b-0 lg:border-r">
        <div className="flex gap-1 overflow-x-auto p-3 lg:block lg:space-y-1 lg:p-5"><div className="mb-5 hidden px-3 text-[10px] font-bold uppercase tracking-[.2em] text-[#9ca3af] lg:block">Workspace</div>{navItems.map(item => { const Icon = item.icon; return <button key={item.id} onClick={() => setSection(item.id)} className={cn("flex shrink-0 items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold transition-all lg:w-full", section === item.id ? "bg-[#c90019] text-white shadow-[0_8px_18px_rgba(201,0,25,.18)]" : "text-[#687180] hover:bg-[#f7f8fa] hover:text-[#19212d]")}><Icon className="size-4" />{item.label}{item.id === "records" && <span className="ml-auto rounded-full bg-white/20 px-2 py-0.5 text-[10px]">{records.length}</span>}</button> })}</div>
        <div className="mx-5 hidden rounded-2xl bg-[#1f2937] p-4 text-white lg:block"><div className="mb-2 flex items-center gap-2 text-xs font-bold"><Sparkles className="size-4 text-[#ffbcc5]" />销售提示</div><p className="text-[11px] leading-5 text-white/70">前 10 分钟只问不推。先辨类，再选武器上膛。</p></div>
      </aside>
      <main className="min-w-0 flex-1 px-4 py-6 sm:px-8 lg:px-10">
        {section === "diagnose" && <DiagnosePanel form={form} update={update} submit={submitDiagnosis} loading={diagnose.isPending} playbook={playbook} savePlaybook={savePlaybook} saving={false} />}
        {section === "assistant" && <section><PageHeading eyebrow="AI 攻单助手" title="把客户背景，变成下一步动作" description="输入一段客户背景，AI 会基于内置知识库判断类型、匹配案例，并按‘听 / 认 / 比 / 算 / 定’组织建议。" /><AIChatBox messages={chatMessages} onSendMessage={sendChat} isLoading={chat.isPending} height={580} placeholder="例如：一家区域护肤品牌，南方很强，准备进入北上广深……" emptyStateMessage="先描述客户，再开始攻单" suggestedPrompts={["帮我诊断一家准备全国化的区域品牌", "客户说太贵了，怎么继续推进？", "给我一套品类开创者型的首面打法"]} /></section>}
        {section === "types" && <TypesPanel types={filteredTypes} search={search} setSearch={setSearch} />}
        {section === "objections" && <ObjectionsPanel objections={knowledgeQuery.data?.objections ?? []} />}
        {section === "records" && <RecordsPanel records={records} />}
      </main>
    </div>
  </div>;
}

function PageHeading({ eyebrow, title, description }: { eyebrow: string; title: string; description: string }) { return <div className="mb-7"><div className="mb-2 text-[11px] font-black uppercase tracking-[.2em] text-[#c90019]">{eyebrow}</div><h1 className="text-3xl font-black tracking-[-.04em] text-[#18212e] sm:text-4xl">{title}</h1><p className="mt-3 max-w-2xl text-sm leading-6 text-[#687180]">{description}</p></div>; }

function DiagnosePanel({ form, update, submit, loading, playbook, savePlaybook, saving }: { form: FormState; update: (key: keyof FormState, value: string) => void; submit: () => void; loading: boolean; playbook: Playbook | null; savePlaybook: () => void; saving: boolean }) {
  const [step, setStep] = useState(0);
  const [showIntel, setShowIntel] = useState(false);
  const [multiMode, setMultiMode] = useState<Record<keyof FormState, boolean>>({ industry: false, scale: false, keywords: true, competition: true, goal: true, background: true });
  const questions: { key: keyof FormState; label: string; hint: string; chips: string[] }[] = [
    { key: "industry", label: "先说说客户属于哪个行业？", hint: "例如：国产护肤、鲜炖燕窝、智能家电", chips: ["食品饮料", "美妆个护", "母婴营养", "服饰鞋服", "家居家电", "智能硬件", "汽车出行", "新零售连锁", "健康医疗", "金融服务"] },
    { key: "scale", label: "客户目前处在什么规模？", hint: "营收、城市覆盖、渠道体量都可以", chips: ["初创 0-1 亿", "成长 1-10 亿", "规模 10-50 亿", "行业龙头 50 亿+", "区域龙头", "全国布局", "融资早期", "融资后期", "上市公司", "拟上市阶段"] },
    { key: "keywords", label: "老板最近最常说哪句话？", hint: "长期主义、翻盘、全国化、估值等原话最有价值", chips: ["我要做行业第一", "我要翻盘", "我要出省", "我要变年轻", "要抢占用户心智", "要做新品类", "要提高客单", "要讲资本故事", "要降低获客成本", "要打爆一个市场"] },
    { key: "competition", label: "客户正在面对什么竞争状态？", hint: "红海、竞品动作、区域优势、新品类空白……", chips: ["红海同质化", "区域强、出省弱", "新品类教育", "竞品已先投", "价格战激烈", "头部品牌挤压", "渠道增长放缓", "线上流量变贵", "线下认知不足", "暂无直接竞品"] },
    { key: "goal", label: "这次拜访最想推进什么目标？", hint: "品牌、增长、融资、扩张或年轻化", chips: ["建立品牌资产", "抢占品类心智", "核心城市打样", "降低试错成本", "拓展全国市场", "提升高端认知", "新品上市破圈", "招商赋能", "融资估值支撑", "品牌年轻化"] },
    { key: "background", label: "还有什么关键原话或背景？", hint: "可选。写下已投渠道、当前卡点或决策链信息", chips: ["预算敏感", "老板未到场", "线上效果不好", "品牌认知偏弱", "已有投放经验", "决策周期较长", "需要内部汇报", "竞品正在加投", "希望先小范围测试", "暂无补充"] },
  ];
  const current = questions[step];
  const completed = questions.filter(question => form[question.key].trim()).length;
  const goNext = () => step < questions.length - 1 ? setStep(step + 1) : submit();
  const labels: Record<keyof FormState, string> = { industry: "行业", scale: "规模", keywords: "老板关键词", competition: "竞争状态", goal: "本次目标", background: "补充背景" };
  const selectedOptions = form[current.key].split("、").filter(Boolean);
  const toggleChoice = (choice: string) => {
    const exists = selectedOptions.includes(choice);
    const next = multiMode[current.key]
      ? (exists ? selectedOptions.filter(item => item !== choice) : [...selectedOptions, choice])
      : (exists ? [] : [choice]);
    update(current.key, next.join("、"));
  };
  return <section><PageHeading eyebrow="01 / 客户诊断工作台" title="先辨类，再攻单" description="像真实拜访一样，一问一问补齐客户线索。AI 会在最后一步给出客户画像、主次类型、案例、攻单结论和具体推进计划。" /><div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(420px,.92fr)]"><Card className="border-0 bg-white shadow-[0_12px_35px_rgba(20,30,45,.06)]"><CardHeader className="border-b border-[#eef0f3] pb-5"><div className="flex items-center justify-between"><div><CardTitle className="text-lg">客户问诊 · {String(step + 1).padStart(2, "0")}</CardTitle><p className="mt-1 text-xs text-[#89919d]">每次只聚焦一个问题，先听再判断</p></div><Badge className="bg-[#fff1f3] text-[#c90019] hover:bg-[#fff1f3]">已采集 {completed} / {questions.length}</Badge></div><div className="mt-5 flex gap-1.5">{questions.map((_, index) => <button key={index} onClick={() => index <= step && setStep(index)} aria-label={`查看第 ${index + 1} 个问题`} className={cn("h-1 flex-1 rounded-full transition-colors", index <= step ? "bg-[#c90019]" : "bg-[#edf0f3]")} />)}</div></CardHeader><CardContent className="space-y-6 pt-8"><div className="flex items-start justify-between gap-4"><div><div className="mb-3 text-[11px] font-bold uppercase tracking-[.15em] text-[#c90019]">AI 正在问</div><h2 className="text-2xl font-black tracking-[-.03em]">{current.label}</h2><p className="mt-2 text-sm text-[#89919d]">{current.hint}</p></div><button onClick={() => setShowIntel(!showIntel)} className="shrink-0 rounded-lg border border-[#e6e9ed] px-2.5 py-2 text-[11px] font-bold text-[#687180] hover:border-[#e5aab1] hover:text-[#c90019]">{showIntel ? "收起情报" : "已采集情报"}</button></div>{showIntel && <div className="grid gap-2 rounded-xl bg-[#f8f9fb] p-3 sm:grid-cols-2">{questions.map(question => <div key={question.key} className="flex items-center gap-2 text-xs"><CheckCircle2 className={cn("size-3.5", form[question.key] ? "text-[#c90019]" : "text-[#cfd4da]")} /><span className="font-semibold text-[#687180]">{labels[question.key]}：</span><span className="truncate text-[#9aa1ac]">{form[question.key] || "待补充"}</span></div>)}</div>}<div className="flex items-center justify-between gap-3"><div className="text-xs font-bold text-[#687180]">预设线索 <span className="ml-1 font-normal text-[#9aa1ac]">{multiMode[current.key] ? "可选择多项" : "每次只能选择一项"}</span></div><div className="flex rounded-lg bg-[#f3f5f7] p-1 text-[11px] font-bold"><button onClick={() => setMultiMode(previous => ({ ...previous, [current.key]: false }))} className={cn("rounded-md px-2.5 py-1.5", !multiMode[current.key] ? "bg-white text-[#c90019] shadow-sm" : "text-[#89919d]")}>单选</button><button onClick={() => setMultiMode(previous => ({ ...previous, [current.key]: true }))} className={cn("rounded-md px-2.5 py-1.5", multiMode[current.key] ? "bg-white text-[#c90019] shadow-sm" : "text-[#89919d]")}>多选</button></div></div><div className="flex flex-wrap gap-2">{current.chips.map(chip => <button key={chip} onClick={() => toggleChoice(chip)} className={cn("rounded-full border px-3 py-2 text-xs transition-all", selectedOptions.includes(chip) ? "border-[#c90019] bg-[#fff1f3] font-bold text-[#c90019]" : "border-[#e4e7eb] text-[#687180] hover:border-[#e5aab1] hover:text-[#c90019]")}>{selectedOptions.includes(chip) && <CheckCircle2 className="mr-1 inline size-3" />}{chip}</button>)}</div>{current.key === "background" ? <Textarea autoFocus value={form[current.key]} onChange={e => update(current.key, e.target.value)} placeholder={current.hint} className="min-h-[125px] resize-none border-[#e1e5ea] bg-[#fbfcfd] text-sm focus-visible:ring-[#c90019]" /> : <Input autoFocus value={form[current.key]} onChange={e => update(current.key, e.target.value)} placeholder={current.hint} className="h-12 border-[#e1e5ea] bg-[#fbfcfd] text-sm focus-visible:ring-[#c90019]" />}<div className={cn("flex items-center gap-2 rounded-lg px-3 py-2 text-xs", form[current.key] ? "bg-[#effaf4] text-[#28784f]" : "bg-[#fff8f8] text-[#a4585f]")}><CheckCircle2 className="size-3.5" />{form[current.key] ? `已记录：${form[current.key]}` : "可选择预设线索，也可手动补充自己的描述"}</div><div className="flex gap-3"><Button variant="outline" onClick={() => setStep(Math.max(0, step - 1))} disabled={step === 0} className="h-12 flex-1 border-[#e1e5ea]">上一步</Button><Button onClick={goNext} disabled={loading} className="h-12 flex-[2] bg-[#c90019] font-bold hover:bg-[#a90015]">{loading ? <><Sparkles className="mr-2 size-4 animate-pulse" />正在组装策略…</> : step === questions.length - 1 ? <><BrainCircuit className="mr-2 size-4" />生成攻单结论</> : <>保存并进入下一问 <ArrowRight className="ml-2 size-4" /></>}</Button></div></CardContent></Card>{playbook ? <ProfileResult playbook={playbook} form={form} savePlaybook={savePlaybook} saving={saving} /> : <EmptyResult />}</div></section>;
}

function Field({ label, hint, value, onChange }: { label: string; hint: string; value: string; onChange: (value: string) => void }) { return <div><label className="mb-2 block text-xs font-bold text-[#384252]">{label}</label><Input value={value} onChange={e => onChange(e.target.value)} placeholder={hint} className="h-11 border-[#e1e5ea] bg-[#fbfcfd] text-sm focus-visible:ring-[#c90019]" /></div>; }

function EmptyResult() { return <div className="flex min-h-[620px] flex-col justify-between rounded-2xl bg-[#202a36] p-7 text-white shadow-[0_18px_40px_rgba(20,30,45,.12)]"><div><div className="mb-5 flex size-12 items-center justify-center rounded-2xl bg-white/10"><Target className="size-6 text-[#ffb1ba]" /></div><div className="mb-3 text-[10px] font-bold uppercase tracking-[.18em] text-[#ff9faa]">AI Conclusion</div><h2 className="text-2xl font-black tracking-[-.03em]">你的攻单结论<br /><span className="text-[#ffb1ba]">会出现在这里</span></h2><p className="mt-4 max-w-sm text-sm leading-6 text-white/60">完成问诊后，AI 会把客户的表达翻译成销售可执行的类型判断、核心矛盾、案例佐证和下一步动作。</p></div><div className="space-y-3 text-xs text-white/60"><div className="flex items-center gap-3"><span className="flex size-7 items-center justify-center rounded-full bg-white/10 text-white">01</span>判断：主类型 + 次类型 + 识别依据</div><div className="flex items-center gap-3"><span className="flex size-7 items-center justify-center rounded-full bg-white/10 text-white">02</span>结论：最该优先点破的客户矛盾</div><div className="flex items-center gap-3"><span className="flex size-7 items-center justify-center rounded-full bg-white/10 text-white">03</span>计划：拜访中与拜访后的推进动作</div></div></div>; }

function ProfileResult({ playbook, form, savePlaybook, saving }: { playbook: Playbook; form: FormState; savePlaybook: () => void; saving: boolean }) {
  const profile = useMemo(() => buildCustomerProfile(form, playbook), [form, playbook]);
  const reportRef = useRef<HTMLDivElement>(null);
  const [exporting, setExporting] = useState(false);

  const exportPdf = async () => {
    if (!reportRef.current) return;
    setExporting(true);
    try {
      const [{ default: html2canvas }, { jsPDF }] = await Promise.all([import("html2canvas"), import("jspdf")]);
      await document.fonts?.ready;
      const frame = document.createElement("iframe");
      frame.setAttribute("aria-hidden", "true");
      Object.assign(frame.style, { position: "fixed", left: "-12000px", top: "0", width: "794px", height: "2000px", border: "0", opacity: "0" });
      document.body.appendChild(frame);
      const frameDocument = frame.contentDocument;
      if (!frameDocument) throw new Error("无法初始化报告渲染文档");
      frameDocument.open();
      frameDocument.write("<!doctype html><html><head><meta charset=\"utf-8\"><style>html,body{margin:0;background:#fff;color:#18212e}*{box-sizing:border-box}</style></head><body></body></html>");
      frameDocument.close();
      const reportClone = frameDocument.importNode(reportRef.current, true) as HTMLDivElement;
      Object.assign(reportClone.style, { position: "static", left: "0", top: "0", width: "794px", minHeight: "auto", opacity: "1" });
      frameDocument.body.appendChild(reportClone);
      const canvas = await html2canvas(reportClone, { scale: 2, backgroundColor: "#ffffff", useCORS: true, windowWidth: 794, windowHeight: reportClone.scrollHeight });
      frame.remove();
      const image = canvas.toDataURL("image/png");
      const pdf = new jsPDF("p", "pt", "a4");
      const pageWidth = pdf.internal.pageSize.getWidth();
      const pageHeight = pdf.internal.pageSize.getHeight();
      const imageHeight = (canvas.height * pageWidth) / canvas.width;
      let remaining = imageHeight;
      let position = 0;
      pdf.addImage(image, "PNG", 0, position, pageWidth, imageHeight);
      remaining -= pageHeight;
      while (remaining > 0) {
        position = remaining - imageHeight;
        pdf.addPage();
        pdf.addImage(image, "PNG", 0, position, pageWidth, imageHeight);
        remaining -= pageHeight;
      }
      const stamp = new Date().toISOString().slice(0, 10);
      const filename = `攻单报告-${profile.title.replace(/[\\/:*?"<>|]/g, "")}-${stamp}.pdf`;
      const href = URL.createObjectURL(pdf.output("blob"));
      const link = document.createElement("a");
      link.href = href;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(href), 30000);
    } finally {
      setExporting(false);
    }
  };

  return <div className="space-y-4"><Card className="border-0 bg-white shadow-[0_12px_35px_rgba(20,30,45,.06)]"><CardContent className="p-6"><div className="flex flex-wrap items-start justify-between gap-4"><div className="flex items-start gap-3"><div className="flex size-11 items-center justify-center rounded-2xl bg-[#fff1f3] text-[#c90019]"><UserRound className="size-5" /></div><div><div className="text-[10px] font-bold uppercase tracking-[.18em] text-[#c90019]">Auto Profile</div><h2 className="mt-1 text-xl font-black">{profile.title}</h2><p className="mt-1 text-xs text-[#89919d]">由本次问诊与 AI 诊断自动归纳</p></div></div><Button onClick={exportPdf} disabled={exporting} size="sm" className="bg-[#c90019] hover:bg-[#a90015]">{exporting ? <><Sparkles className="mr-2 size-4 animate-pulse" />生成中</> : <><FileDown className="mr-2 size-4" />导出 PDF</>}</Button></div><p className="mt-5 text-sm leading-6 text-[#4c5664]">{profile.summary}</p><div className="mt-5 grid gap-3 sm:grid-cols-2"><ProfileField label="发展阶段" value={profile.customerStage} /><ProfileField label="决策驱动力" value={profile.decisionDriver} /><ProfileField label="市场张力" value={profile.marketTension} /><ProfileField label="本次拜访目标" value={profile.visitGoal} /></div><div className="mt-5 rounded-xl bg-[#f8f9fb] p-4"><div className="mb-2 text-[11px] font-bold text-[#9aa1ac]">画像判断依据</div><div className="flex flex-wrap gap-2">{profile.evidence.map(item => <span key={item} className="rounded-full bg-white px-3 py-1.5 text-xs font-semibold text-[#5f6876] shadow-sm">{item}</span>)}</div></div>{profile.watchouts.length > 0 && <div className="mt-4 rounded-xl border border-[#f3dedf] bg-[#fff9f9] p-4"><div className="mb-2 text-xs font-bold text-[#c90019]">沟通风险提醒</div><div className="space-y-1.5">{profile.watchouts.map(item => <p key={item} className="text-xs leading-5 text-[#81525a]">• {item}</p>)}</div></div>}</CardContent></Card><PlaybookResult playbook={playbook} savePlaybook={savePlaybook} saving={saving} /><PdfReportDocument ref={reportRef} profile={profile} playbook={playbook} /></div>;
}

function ProfileField({ label, value }: { label: string; value: string }) { return <div className="rounded-xl border border-[#edf0f3] p-3"><div className="text-[11px] font-bold text-[#9aa1ac]">{label}</div><p className="mt-1 text-sm font-bold text-[#384252]">{value}</p></div>; }

const PdfReportDocument = forwardRef<HTMLDivElement, { profile: CustomerProfile; playbook: Playbook }>(({ profile, playbook }, ref) => {
  const plan = [
    { phase: "会前", text: `带着“${playbook.primaryType}”判断，验证客户是否认同当前处境。` },
    { phase: "会中", text: "先点破矛盾，再引用匹配案例建立共识，避免先讲资源。" },
    { phase: "会后", text: playbook.nextAction },
  ];
  return <div ref={ref} style={{ position: "fixed", left: "-10000px", top: 0, width: "794px", background: "#ffffff", color: "#18212e", padding: "46px", fontFamily: "Arial, 'Microsoft YaHei', sans-serif" }}><div style={{ borderBottom: "3px solid #c90019", paddingBottom: "18px" }}><div style={{ color: "#c90019", fontSize: "11px", fontWeight: 700, letterSpacing: "2px" }}>FENZHONG SALES INTELLIGENCE</div><h1 style={{ margin: "8px 0 4px", fontSize: "28px" }}>攻单 AI · 客户拜访报告</h1><p style={{ margin: 0, color: "#687180", fontSize: "12px" }}>生成时间：{new Date().toLocaleString("zh-CN")}</p></div><section style={{ marginTop: "26px" }}><h2 style={{ color: "#c90019", fontSize: "16px" }}>01 / 客户画像</h2><h3 style={{ fontSize: "22px", margin: "8px 0" }}>{profile.title}</h3><p style={{ color: "#4c5664", fontSize: "13px", lineHeight: 1.8 }}>{profile.summary}</p><div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", marginTop: "14px" }}>{[["发展阶段", profile.customerStage], ["决策驱动力", profile.decisionDriver], ["市场张力", profile.marketTension], ["拜访目标", profile.visitGoal]].map(([label, value]) => <div key={label} style={{ background: "#f7f8fa", padding: "12px", borderRadius: "8px" }}><div style={{ color: "#89919d", fontSize: "11px" }}>{label}</div><div style={{ marginTop: "5px", fontSize: "13px", fontWeight: 700 }}>{value}</div></div>)}</div></section><section style={{ marginTop: "26px" }}><h2 style={{ color: "#c90019", fontSize: "16px" }}>02 / 攻单结论</h2><p style={{ fontSize: "18px", fontWeight: 700, margin: "8px 0" }}>{playbook.primaryType} <span style={{ color: "#687180", fontSize: "12px" }}>· 次类型：{playbook.secondaryType} · {playbook.confidence}</span></p><p style={{ color: "#4c5664", fontSize: "13px", lineHeight: 1.8 }}>{playbook.diagnosis}</p><div style={{ marginTop: "12px", background: "#fff8f8", padding: "12px", borderRadius: "8px" }}><div style={{ color: "#c90019", fontSize: "11px", fontWeight: 700 }}>判断依据</div><div style={{ marginTop: "6px", color: "#5f6876", fontSize: "12px" }}>{playbook.evidence.join(" · ")}</div></div></section><section style={{ marginTop: "26px" }}><h2 style={{ color: "#c90019", fontSize: "16px" }}>03 / 攻单策略与沟通话术</h2><p style={{ color: "#4c5664", fontSize: "13px", lineHeight: 1.8 }}>{playbook.strategy}</p><div style={{ borderLeft: "3px solid #c90019", paddingLeft: "12px", marginTop: "12px" }}><div style={{ fontSize: "11px", color: "#c90019", fontWeight: 700 }}>一句话破冰</div><p style={{ margin: "5px 0 0", fontSize: "13px" }}>“{playbook.breakIce}”</p></div><div style={{ borderLeft: "3px solid #c90019", paddingLeft: "12px", marginTop: "12px" }}><div style={{ fontSize: "11px", color: "#c90019", fontWeight: 700 }}>核心沟通话术</div><p style={{ margin: "5px 0 0", fontSize: "13px" }}>“{playbook.coreTalk}”</p></div></section><section style={{ marginTop: "26px" }}><h2 style={{ color: "#c90019", fontSize: "16px" }}>04 / 案例与下一步计划</h2><p style={{ fontSize: "13px", color: "#4c5664" }}><b>匹配案例：</b>{playbook.matchedCases.join("、")}</p><ol style={{ paddingLeft: "20px", color: "#4c5664", fontSize: "13px", lineHeight: 1.8 }}>{plan.map(item => <li key={item.phase}><b>{item.phase}：</b>{item.text}</li>)}</ol></section><div style={{ marginTop: "34px", paddingTop: "12px", borderTop: "1px solid #e7e9ed", color: "#9aa1ac", fontSize: "10px" }}>本报告由攻单 AI 根据分众七大类型、攻单五步法及本次客户问诊自动生成，仅用于销售拜访准备与复盘。</div></div>;
});

function PlaybookResult({ playbook, savePlaybook, saving }: { playbook: Playbook; savePlaybook: () => void; saving: boolean }) { const plan = [{ phase: "会前", title: "确认关键假设", text: `带着“${playbook.primaryType}”判断，向客户验证是否认同当前处境。` }, { phase: "会中", title: "点破矛盾再佐证", text: "先用处境点破建立理解，再引用自动匹配案例，避免一开始就讲资源。" }, { phase: "会后", title: "锚定一个可执行动作", text: playbook.nextAction }]; return <div className="space-y-4"><Card className="border-0 bg-[#202a36] text-white shadow-[0_18px_40px_rgba(20,30,45,.12)]"><CardContent className="p-6"><div className="flex items-start justify-between gap-4"><div><div className="mb-2 text-[10px] font-bold uppercase tracking-[.2em] text-[#ff9faa]">AI Conclusion</div><h2 className="text-2xl font-black">结论：{playbook.primaryType}</h2><p className="mt-1 text-sm text-white/60">次类型：{playbook.secondaryType} · 判断置信度：{playbook.confidence}</p></div><Button onClick={savePlaybook} disabled={saving} size="sm" className="bg-white/10 text-white hover:bg-white/20">{saving ? "保存中" : <><Bookmark className="mr-2 size-4" />保存方案</>}</Button></div><div className="mt-5 flex flex-wrap gap-2">{playbook.evidence.map(item => <span key={item} className="rounded-full bg-white/10 px-3 py-1.5 text-xs text-white/80">{item}</span>)}</div><div className="mt-5 border-t border-white/10 pt-5"><div className="mb-2 text-xs font-bold text-[#ffb1ba]">最该优先点破的矛盾</div><p className="text-sm leading-6 text-white/80">{playbook.diagnosis}</p></div></CardContent></Card><Card className="border-0 bg-white shadow-[0_12px_35px_rgba(20,30,45,.06)]"><CardHeader><CardTitle className="flex items-center gap-2 text-base"><Sparkles className="size-4 text-[#c90019]" />定制攻单策略</CardTitle></CardHeader><CardContent className="space-y-5"><p className="text-sm leading-6 text-[#4c5664]">{playbook.strategy}</p><div className="rounded-xl border border-[#f1d0d4] bg-[#fff8f8] p-4"><div className="mb-3 flex items-center gap-2 text-xs font-bold text-[#c90019]"><FileText className="size-4" />自动匹配案例</div><div className="flex flex-wrap gap-2">{playbook.matchedCases.map(item => <span key={item} className="rounded-full bg-white px-3 py-2 text-xs font-bold text-[#5f6876] shadow-sm">{item}</span>)}</div><p className="mt-3 text-[11px] leading-5 text-[#a4585f]">案例匹配由客户主类型与次类型自动关联，具体数据仅引用内置文档案例。</p></div><div className="grid gap-3 sm:grid-cols-2">{playbook.steps.map((step, index) => <div key={step.name} className="rounded-xl bg-[#f8f9fb] p-4"><div className="mb-2 flex items-center gap-2"><span className="text-xs font-black text-[#c90019]">0{index + 1}</span><span className="text-sm font-bold">{step.name}</span></div><p className="text-xs leading-5 text-[#687180]">{step.action}</p><div className="mt-2 text-[11px] font-semibold text-[#a4585f]">产出：{step.output}</div></div>)}</div><div className="grid gap-4 border-t border-[#edf0f3] pt-5 sm:grid-cols-2"><Quote label="一句话破冰" text={playbook.breakIce} /><Quote label="核心沟通话术" text={playbook.coreTalk} /></div><div className="rounded-xl bg-[#202a36] p-5 text-white"><div className="mb-4 flex items-center gap-2 text-xs font-bold text-[#ffb1ba]"><ListChecks className="size-4" />下一步推进计划</div><div className="space-y-4">{plan.map((item, index) => <div key={item.phase} className="flex gap-3"><span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-white/10 text-[10px] font-black">0{index + 1}</span><div><div className="text-xs font-bold">{item.phase} · {item.title}</div><p className="mt-1 text-xs leading-5 text-white/65">{item.text}</p></div></div>)}</div></div><div className="flex items-start gap-3 rounded-xl border border-[#f1d0d4] bg-[#fff8f8] p-4"><Map className="mt-0.5 size-4 shrink-0 text-[#c90019]" /><div><div className="text-xs font-bold text-[#c90019]">本次推进的成败标准</div><p className="mt-1 text-sm font-semibold leading-6 text-[#4c5664]">不是“讲完方案”，而是和客户共同确认一个下一步：测试范围、试点城市、关键决策人或复盘时间。</p></div></div></CardContent></Card></div>; }

function Quote({ label, text }: { label: string; text: string }) { return <div><div className="mb-2 text-[11px] font-bold uppercase tracking-[.1em] text-[#c90019]">{label}</div><p className="border-l-2 border-[#c90019] pl-3 text-sm italic leading-6 text-[#4c5664]">“{text}”</p></div>; }

function TypesPanel({ types, search, setSearch }: { types: readonly any[]; search: string; setSearch: (v: string) => void }) { return <section><PageHeading eyebrow="02 / 七大类型速查卡" title="见客户先对号入座" description="七种典型动机，七套沟通武器。先识别客户在为什么买，再决定你要讲什么。" /><div className="mb-6 flex max-w-xl items-center gap-3 rounded-xl bg-white px-4 shadow-sm"><Search className="size-4 text-[#9aa1ac]" /><Input value={search} onChange={e => setSearch(e.target.value)} placeholder="搜索客户类型、识别信号或切入点" className="h-12 border-0 bg-transparent px-0 text-sm shadow-none focus-visible:ring-0" /></div><div className="grid gap-4 xl:grid-cols-2">{types.map((type: any, index: number) => <Card key={type.id} className="border-0 bg-white shadow-[0_10px_30px_rgba(20,30,45,.05)]"><CardContent className="p-5"><div className="flex items-start justify-between gap-3"><div className="flex items-center gap-3"><span className="flex size-9 items-center justify-center rounded-xl bg-[#fff1f3] text-xs font-black text-[#c90019]">0{index + 1}</span><div><h3 className="font-black">{type.name}</h3><p className="mt-0.5 text-xs text-[#9aa1ac]">{type.dimension} · “{type.short}”</p></div></div><Badge variant="outline" className="border-[#f0d0d4] text-[#c90019]">{type.entry}</Badge></div><div className="mt-5 grid gap-4 text-sm sm:grid-cols-2"><div><div className="mb-2 text-[11px] font-bold text-[#9aa1ac]">识别信号</div><ul className="space-y-1.5 text-xs leading-5 text-[#5f6876]">{type.signals.map((signal: string) => <li key={signal} className="flex gap-2"><span className="mt-2 size-1.5 shrink-0 rounded-full bg-[#c90019]" />{signal}</li>)}</ul></div><div><div className="mb-2 text-[11px] font-bold text-[#9aa1ac]">核心沟通</div><p className="text-xs leading-5 text-[#5f6876]">{type.coreTalk}</p><div className="mt-3 rounded-lg bg-[#fff8f8] p-3 text-[11px] leading-5 text-[#a4585f]"><span className="font-bold">忌讳：</span>{type.taboo}</div></div></div></CardContent></Card>)}</div></section>; }

function ObjectionsPanel({ objections }: { objections: readonly any[] }) { const [active, setActive] = useState(0); const item = objections[active]; return <section><PageHeading eyebrow="03 / 异议速查" title="拒绝不是结束，是探需入口" description="先听懂表面理由背后的真实顾虑，再用降低风险、补齐决策链和量化价值的方式推进。" /><div className="grid gap-6 lg:grid-cols-[250px_1fr]"><div className="space-y-2">{objections.map((objection, index) => <button key={objection.label} onClick={() => setActive(index)} className={cn("w-full rounded-xl px-4 py-3 text-left text-sm font-bold transition-all", index === active ? "bg-[#c90019] text-white shadow-[0_8px_18px_rgba(201,0,25,.18)]" : "bg-white text-[#687180] hover:bg-[#fff4f5]")}>{objection.label}<ChevronRight className="float-right mt-0.5 size-4" /></button>)}</div>{item && <Card className="border-0 bg-white shadow-[0_12px_35px_rgba(20,30,45,.06)]"><CardContent className="p-7"><div className="mb-8 flex size-14 items-center justify-center rounded-2xl bg-[#fff1f3] text-[#c90019]"><CircleHelp className="size-7" /></div><div className="text-sm font-bold text-[#c90019]">客户说</div><h2 className="mt-1 text-3xl font-black tracking-[-.04em]">“{item.label}”</h2><div className="my-8 grid gap-6 sm:grid-cols-2"><div><div className="mb-2 text-[11px] font-bold uppercase tracking-[.15em] text-[#9aa1ac]">真实顾虑</div><p className="text-sm leading-6 text-[#5f6876]">{item.concern}</p></div><div><div className="mb-2 text-[11px] font-bold uppercase tracking-[.15em] text-[#9aa1ac]">应对策略</div><p className="text-sm leading-6 text-[#5f6876]">{item.response}</p></div></div><div className="rounded-xl bg-[#202a36] p-5 text-sm leading-7 text-white/85"><span className="mr-2 font-bold text-[#ffb1ba]">推进提醒</span>不要马上反驳。先用问题确认顾虑，再把下一步动作拆小，让客户能低风险地继续。</div></CardContent></Card>}</div></section>; }

function RecordsPanel({ records }: { records: StoredRecord[] }) { const [selected, setSelected] = useState<StoredRecord | null>(null); return <section><PageHeading eyebrow="04 / 我的记录" title="把每一次拜访，变成下一次准备" description="无需登录。记录保存在当前浏览器中，刷新后仍可在这台设备上复习。" />{selected ? <Card className="border-0 bg-white shadow-sm"><CardContent className="p-6"><button onClick={() => setSelected(null)} className="mb-5 text-xs font-bold text-[#c90019]">← 返回记录列表</button><div className="flex flex-wrap items-center gap-2"><h2 className="text-2xl font-black">{selected.title}</h2><Badge className="bg-[#fff1f3] text-[#c90019] hover:bg-[#fff1f3]">{selected.primaryType}</Badge></div><p className="mt-4 text-sm leading-6 text-[#5f6876]">{selected.diagnosis}</p><div className="mt-6 rounded-xl bg-[#202a36] p-5 text-sm leading-7 text-white/85"><div className="mb-2 text-xs font-bold text-[#ffb1ba]">已保存攻单方案</div><Streamdown>{selected.playbook}</Streamdown></div></CardContent></Card> : <div className="space-y-3">{records.length ? records.map(record => <button key={record.id} onClick={() => setSelected(record)} className="block w-full text-left"><Card className="border-0 bg-white shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md"><CardContent className="flex items-center justify-between gap-4 p-5"><div><div className="flex flex-wrap items-center gap-2"><h3 className="font-bold">{record.title}</h3><Badge className="bg-[#fff1f3] text-[#c90019] hover:bg-[#fff1f3]">{record.primaryType}</Badge></div><p className="mt-2 line-clamp-1 text-xs text-[#89919d]">{record.diagnosis}</p></div><div className="hidden items-center gap-2 text-xs text-[#9aa1ac] sm:flex"><Clock3 className="size-4" />{new Date(record.createdAt).toLocaleDateString()}<ChevronRight className="size-4" /></div></CardContent></Card></button>) : <Card className="border-0 bg-white shadow-sm"><CardContent className="flex flex-col items-center p-12 text-center"><Bookmark className="mb-4 size-10 text-[#c90019]" /><h2 className="text-xl font-black">还没有攻单记录</h2><p className="mt-2 max-w-md text-sm leading-6 text-[#687180]">完成一次客户诊断后，点击“保存方案”，记录将保存在当前浏览器中，无需登录。</p></CardContent></Card>}</div>}</section>; }
