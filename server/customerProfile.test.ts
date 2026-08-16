import { describe, expect, it } from "vitest";
import { buildCustomerProfile } from "../client/src/lib/customerProfile";

describe("customer profile generator", () => {
  it("summarizes questionnaire inputs and the AI conclusion into a reusable customer profile", () => {
    const profile = buildCustomerProfile(
      { industry: "美妆个护", scale: "区域龙头", keywords: "我要出省", competition: "区域强、出省弱", goal: "拓展全国市场", background: "老板关注北上广深的试点" },
      { primaryType: "全国化扩张型", secondaryType: "品牌野心型", confidence: "高", evidence: ["区域基础稳", "有全国化诉求"], diagnosis: "认知先行", strategy: "先建立城市样板", breakIce: "先谈认知", coreTalk: "再谈样板", objections: [{ objection: "太贵了", concern: "担心试错", response: "先做小范围" }], nextAction: "确定试点城市", matchedCases: ["波司登"] },
    );

    expect(profile.title).toBe("美妆个护客户画像");
    expect(profile.primaryType).toBe("全国化扩张型");
    expect(profile.summary).toContain("北上广深");
    expect(profile.watchouts[0]).toContain("太贵了");
  });
});
