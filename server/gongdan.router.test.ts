import { describe, expect, it, vi } from "vitest";
import type { TrpcContext } from "./_core/context";

vi.mock("./db", () => ({
  createDealSession: vi.fn(async () => ({ id: 42 })),
  listDealSessions: vi.fn(async () => [{ id: 42, title: "区域护肤客户", primaryType: "全国化扩张型" }]),
  getDealSession: vi.fn(async (_userId: number, id: number) => id === 42 ? { id: 42, title: "区域护肤客户", playbook: "复习方案" } : undefined),
}));

import { appRouter } from "./routers";

const user = { id: 7, openId: "sales-user", name: "Sales", email: "sales@example.com", loginMethod: "manus", role: "user" as const, createdAt: new Date(), updatedAt: new Date(), lastSignedIn: new Date() };
const context = { user, req: {} as TrpcContext["req"], res: {} as TrpcContext["res"] } satisfies TrpcContext;

describe("gongdan protected records", () => {
  it("saves a playbook for the authenticated user", async () => {
    const result = await appRouter.createCaller(context).gongdan.save({ title: "区域护肤客户", clientSummary: "区域强，准备出省", primaryType: "全国化扩张型", secondaryType: "品牌野心型", diagnosis: "认知先行", playbook: "完整方案" });
    expect(result).toEqual({ id: 42 });
  });

  it("lists and reopens a saved playbook", async () => {
    const caller = appRouter.createCaller(context);
    expect((await caller.gongdan.list())[0]?.title).toBe("区域护肤客户");
    expect((await caller.gongdan.get({ id: 42 }))?.playbook).toBe("复习方案");
  });
});
