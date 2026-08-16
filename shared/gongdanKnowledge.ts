export const CUSTOMER_TYPES = [
  {
    id: "brand_ambition",
    name: "品牌野心型",
    short: "我要做行业老大",
    dimension: "品牌建设",
    signals: ["高频提长期主义、行业标杆、品牌资产", "已有稳定体量，想从活得好走向行业领先", "竞品开始投放，决策层有竞争焦虑"],
    entry: "资产思维",
    taboo: "只谈 CPM，忽视品牌积累",
    breakIce: "老板，我关注你们很久了，我觉得你们有成为行业第一的基因，这种潜力在市场上非常稀缺。",
    coreTalk: "您投入的不是单纯广告费，而是在为企业构建会持续沉淀的品牌资产。",
    strategy: "把投放从费用翻译成长期资产，强调品牌势能与穿越周期的竞争壁垒。",
    caseIds: ["feihe"],
  },
  {
    id: "positioning",
    name: "定位卡位型",
    short: "这个位置我先占",
    dimension: "心智占位",
    signals: ["有明确对标竞品，想占领某个关键词或消费场景", "常说让消费者想到某需求就想到自己", "品牌已有基础但定位边界模糊"],
    entry: "心智货架",
    taboo: "只追求规模，缺乏差异化",
    breakIce: "我发现你们在这个细分领域的体验做得特别好，但消费者还没真正意识到这种价值，这是巨大的机会点。",
    coreTalk: "不需要让所有人喜欢你，只要在关键场景下让消费者第一个想起你。",
    strategy: "围绕单一品类或场景做强关联，推动品类与品牌形成唯一联想。",
    caseIds: ["miaokelando"],
  },
  {
    id: "category_creator",
    name: "品类开创者型",
    short: "这个品类是我发明的",
    dimension: "品牌建设",
    signals: ["产品属于新品类，市场存在认知空白", "产品或技术团队强，市场教育方法论不足", "希望快速建立品类认知，抢占赛道先机"],
    entry: "教育速度",
    taboo: "急功近利，过度强调短期转化",
    breakIce: "你们正在做的这件事，我判断是未来十年的趋势风口，现在布局正好能抢占品类心智制高点。",
    coreTalk: "产品再好，消费者不认识等于零；分众是帮你抢占心智的品类加速器。",
    strategy: "先讲品类教育速度，再讲品类定义权与心智占位，建立从新品类到领导品牌的路径。",
    caseIds: ["yuanqisenlin"],
  },
  {
    id: "competitive_breakthrough",
    name: "竞争突围型",
    short: "我要翻盘，改变格局",
    dimension: "销售增长",
    signals: ["身处同质化红海，流量成本高、价格战激烈", "产品有差异化但未转化为消费者购买理由", "决策层有强烈增长焦虑，期待快速破局"],
    entry: "饱和攻击",
    taboo: "战线过长，空谈长期主义",
    breakIce: "这个赛道竞争看着激烈，但你们有别人没有的差异化优势，只要放大这点就能快速突围。",
    coreTalk: "在红海里突围不是比对手好一点，而是让消费者感知到你根本不一样。",
    strategy: "用高密度场景覆盖换取品牌认知时间，集中火力放大差异化，形成降维打击。",
    caseIds: ["ulike"],
  },
  {
    id: "capital_story",
    name: "资本叙事型",
    short: "我要给投资人讲故事",
    dimension: "资本价值",
    signals: ["处于融资、Pre-IPO 或业绩对赌阶段", "高频提及估值模型、增长曲线、投资人", "不仅看短期 ROI，更关心品牌势能与估值想象力"],
    entry: "估值杠杆",
    taboo: "纠缠细节，只谈即时效果",
    breakIce: "这个阶段其实是品牌势能爆发的关键期，抓住它能直接拉开与对手的差距。",
    coreTalk: "分众投放不仅是曝光，更是给资本故事做的硬核背书，为融资估值加分。",
    strategy: "用品牌资产化和估值杠杆解释投放，连接声量、搜索与资本市场信任。",
    caseIds: ["yuanqisenlin", "feihe"],
  },
  {
    id: "national_expansion",
    name: "全国化扩张型",
    short: "我要出省，打天下",
    dimension: "销售增长",
    signals: ["区域市场强势，但跨省后品牌认知骤降", "正在推进全国渠道、门店或城市布局", "有全国化愿景，但担心品牌认知与资源匹配"],
    entry: "认知先行",
    taboo: "视野受限，只谈区域经验",
    breakIce: "你们在区域市场很强，想听听你们对全国化布局的规划？",
    coreTalk: "从区域走向全国，最大的成本不是开店，而是让新市场消费者先信任你。",
    strategy: "先在北上广深等核心城市打样，品牌造势先行，渠道承接跟进。",
    caseIds: ["laoxiangji", "chayan"],
  },
  {
    id: "brand_refresh",
    name: "品牌焕新型",
    short: "我要变年轻，破圈",
    dimension: "品牌建设",
    signals: ["品牌有知名度但形象老化，核心受众固化", "渴望触达 Z 世代与新中产", "有历史资产，但缺少现代商业语言和新主张"],
    entry: "重新定位",
    taboo: "固步自封，沉湎于历史辉煌",
    breakIce: "品牌底子很好，接下来如何吸引年轻群体，实现品牌年轻化？",
    coreTalk: "老品牌最大的优势是认知基础，最大的问题是认知老化；要用新故事讲给新人听。",
    strategy: "先重塑定位与表达，再用高频场景触达刷新市场刻板印象，完成品牌资产焕新。",
    caseIds: ["bosideng"],
  },
] as const;

export const CASES = [
  { id: "feihe", name: "飞鹤奶粉", type: "品牌野心型", summary: "围绕‘更适合中国宝宝体质’建立差异化定位，从区域品牌走向全国领军品牌，文档案例记录营收从 35 亿到 200 亿+。", metric: "35亿 → 200亿+", fit: "适合需要建立长期品牌资产、对抗强势竞品的客户。" },
  { id: "miaokelando", name: "妙可蓝多", type: "定位卡位型", summary: "通过‘奶酪就选妙可蓝多’强化品类与品牌的唯一联想，文档案例记录首年营收从 1.7 亿到 8 亿、市场份额从 3.9% 到 30.9%。", metric: "1.7亿 → 8亿；3.9% → 30.9%", fit: "适合希望占领品类词、场景词或建立心智货架的客户。" },
  { id: "yuanqisenlin", name: "元气森林", type: "品类开创者型", summary: "以 0 糖 0 脂 0 卡教育无糖气泡水品类，文档案例记录连续饱和投放 4 个月后单月营收 2.6 亿。", metric: "4个月；单月营收2.6亿", fit: "适合新品类、新物种或需要快速完成市场教育的客户。" },
  { id: "ulike", name: "Ulike", type: "竞争突围型", summary: "用‘蓝宝石冰点脱毛’差异化认知跳出红海竞争，文档案例记录营收从 10 亿级向 45 亿级增长。", metric: "10亿 → 45亿", fit: "适合红海赛道、增长遇到瓶颈、需要集中火力翻盘的客户。" },
  { id: "bosideng", name: "波司登", type: "品牌焕新型", summary: "通过定位、产品与表达升级，撕掉‘爸妈穿的羽绒服’标签，完成从国民老牌到高端户外时尚品牌的认知重构。", metric: "认知重构与年轻化破圈", fit: "适合老品牌年轻化、重塑定位、触达新消费人群的客户。" },
  { id: "laoxiangji", name: "老乡鸡", type: "全国化扩张型", summary: "从安徽本土快餐龙头出发，以标准化运营与品牌升级逐步推进全国多城布局。", metric: "区域龙头 → 全国化布局", fit: "适合区域强势、准备以核心城市为突破口拓展全国的客户。" },
  { id: "chayan", name: "茶颜悦色", type: "全国化扩张型", summary: "深耕长沙本土建立口碑与品牌壁垒，以直营模式稳步推进全国化布局。", metric: "区域网红 → 跨区扩张", fit: "适合需要品牌认知先行、配合渠道扩张的区域品牌。" },
] as const;

export const OBJECTIONS = [
  { label: "太贵了", concern: "对效果存疑，不确定投入能否带来回报", response: "先拆解单次触达成本，再用同类案例说明投入逻辑；必要时把预算拆成核心城市或区域测试，降低试错成本。" },
  { label: "我们再看看", concern: "决策链条长，或内部关键人存在意见分歧", response: "不要急着重复介绍产品，先梳理决策流程、关键决策人和每个人的核心诉求，再约定下一步共同评审动作。" },
  { label: "投过线上，效果不好", concern: "过往投放体验不佳，对线上渠道失去信心", response: "承认线上单点效果的局限，解释线上让人知道、内容让人信任、分众让人记住的互补关系，重新设计组合策略。" },
  { label: "我们品牌太小", concern: "担心预算浪费，认为资源与体量不匹配", response: "建议以小预算区域化测试开始，明确测试周期、目标人群、记忆指标与复盘门槛，把大决策拆成可验证的小动作。" },
  { label: "老板不同意", concern: "还没有击中核心决策人的经营指标与利益点", response: "追问老板最关心的经营指标，再将品牌势能、增长目标、估值或全国化计划翻译成老板能判断的业务语言。" },
] as const;

export const FIVE_STEPS = [
  { id: "listen", name: "听", title: "辨类问诊", text: "前 10 分钟只问不推，用开放式问题深挖需求，判断客户类型与核心痛点。" },
  { id: "recognize", name: "认", title: "点破处境", text: "用一句话总结客户困境，让客户感受到被理解，建立专业信任。" },
  { id: "compare", name: "比", title: "案例佐证", text: "引入同行业或同体量案例，用真实结果证明方案落地性。" },
  { id: "calculate", name: "算", title: "量化价值", text: "把投入、周期与预期收益转化为可衡量指标，避免价值停留在口号。" },
  { id: "decide", name: "定", title: "锚定行动", text: "锁定测试方案、试点城市或关键人，把意向转化为下一步动作。" },
] as const;

export const KNOWLEDGE_BASE = JSON.stringify({ customerTypes: CUSTOMER_TYPES, cases: CASES, objections: OBJECTIONS, fiveSteps: FIVE_STEPS }, null, 2);

export type CustomerTypeId = (typeof CUSTOMER_TYPES)[number]["id"];

export function getMatchedCases(primaryType: string, secondaryType = "") {
  const names = new Set([primaryType, secondaryType].filter(Boolean));
  const matched = CASES.filter(item => names.has(item.type));
  return (matched.length ? matched : CASES.slice(0, 2)).map(item => item.name);
}
