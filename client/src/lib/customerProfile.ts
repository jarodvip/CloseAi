export type CustomerProfileInput = {
  industry: string;
  scale: string;
  keywords: string;
  competition: string;
  goal: string;
  background: string;
};

export type CustomerProfilePlaybook = {
  primaryType: string;
  secondaryType: string;
  confidence: string;
  evidence: string[];
  diagnosis: string;
  strategy: string;
  breakIce: string;
  coreTalk: string;
  objections: { objection: string; concern: string; response: string }[];
  nextAction: string;
  matchedCases: string[];
};

export type CustomerProfile = {
  title: string;
  summary: string;
  customerStage: string;
  decisionDriver: string;
  marketTension: string;
  visitGoal: string;
  primaryType: string;
  secondaryType: string;
  evidence: string[];
  communicationFocus: string;
  watchouts: string[];
};

const fallback = (value: string, placeholder: string) => value.trim() || placeholder;

export function buildCustomerProfile(input: CustomerProfileInput, playbook: CustomerProfilePlaybook): CustomerProfile {
  const industry = fallback(input.industry, "待补充行业");
  const stage = fallback(input.scale, "待确认发展阶段");
  const driver = fallback(input.keywords, "待确认老板核心诉求");
  const tension = fallback(input.competition, "待确认竞争与市场压力");
  const goal = fallback(input.goal, "待确认本次拜访目标");
  const background = input.background.trim();

  return {
    title: `${industry}客户画像`,
    summary: `${industry}客户当前处于“${stage}”阶段，呈现出${playbook.primaryType}特征；本次优先围绕“${goal}”建立共识。${background ? `已补充背景：${background}` : ""}`,
    customerStage: stage,
    decisionDriver: driver,
    marketTension: tension,
    visitGoal: goal,
    primaryType: playbook.primaryType,
    secondaryType: playbook.secondaryType,
    evidence: playbook.evidence.slice(0, 4),
    communicationFocus: playbook.strategy,
    watchouts: playbook.objections.slice(0, 3).map(item => `${item.objection}：${item.concern}`),
  };
}
