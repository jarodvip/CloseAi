import { describe, expect, it } from "vitest";
import { appRouter } from "./routers";
import { CUSTOMER_TYPES, CASES, FIVE_STEPS, OBJECTIONS } from "../shared/gongdanKnowledge";
import type { TrpcContext } from "./_core/context";

const publicContext = {
  user: null,
  req: {} as TrpcContext["req"],
  res: {} as TrpcContext["res"],
} satisfies TrpcContext;

describe("gongdan knowledge", () => {
  it("contains the seven customer types and their core sales fields", () => {
    expect(CUSTOMER_TYPES).toHaveLength(7);
    expect(CUSTOMER_TYPES.every(type => type.signals.length > 0 && type.entry && type.taboo && type.breakIce)).toBe(true);
  });

  it("contains the five-step playbook, objection library and benchmark cases", () => {
    expect(FIVE_STEPS.map(step => step.name)).toEqual(["听", "认", "比", "算", "定"]);
    expect(OBJECTIONS.map(item => item.label)).toEqual(["太贵了", "我们再看看", "投过线上，效果不好", "我们品牌太小", "老板不同意"]);
    expect(CASES.map(item => item.name)).toEqual(expect.arrayContaining(["飞鹤奶粉", "妙可蓝多", "元气森林", "Ulike", "波司登"]));
  });

  it("exposes the same curated knowledge to the client", async () => {
    const result = await appRouter.createCaller(publicContext).gongdan.knowledge();
    expect(result.customerTypes).toHaveLength(7);
    expect(result.fiveSteps).toHaveLength(5);
    expect(result.objections).toHaveLength(5);
  });
});
