import { z } from "zod";
import { invokeLLM } from "./_core/llm";
import { COOKIE_NAME } from "@shared/const";
import { CUSTOMER_TYPES, CASES, FIVE_STEPS, KNOWLEDGE_BASE, OBJECTIONS, getMatchedCases } from "@shared/gongdanKnowledge";
import { createDealSession, getDealSession, listDealSessions } from "./db";
import { getSessionCookieOptions } from "./_core/cookies";
import { systemRouter } from "./_core/systemRouter";
import { protectedProcedure, publicProcedure, router } from "./_core/trpc";

const chatMessageSchema = z.object({ role: z.enum(["user", "assistant"]), content: z.string().min(1).max(12000) });
const clientInputSchema = z.object({
  industry: z.string().max(1200).optional().default(""),
  scale: z.string().max(1200).optional().default(""),
  keywords: z.string().max(1200).optional().default(""),
  competition: z.string().max(1200).optional().default(""),
  goal: z.string().max(1200).optional().default(""),
  background: z.string().max(8000).optional().default(""),
});

const playbookSchema = {
  type: "object",
  properties: {
    primaryType: { type: "string" },
    secondaryType: { type: "string" },
    confidence: { type: "string" },
    evidence: { type: "array", items: { type: "string" } },
    diagnosis: { type: "string" },
    strategy: { type: "string" },
    steps: { type: "array", items: { type: "object", properties: { name: { type: "string" }, action: { type: "string" }, output: { type: "string" } }, required: ["name", "action", "output"], additionalProperties: false } },
    breakIce: { type: "string" },
    coreTalk: { type: "string" },
    objections: { type: "array", items: { type: "object", properties: { objection: { type: "string" }, concern: { type: "string" }, response: { type: "string" } }, required: ["objection", "concern", "response"], additionalProperties: false } },
    nextAction: { type: "string" },
    matchedCases: { type: "array", items: { type: "string" } },
  },
  required: ["primaryType", "secondaryType", "confidence", "evidence", "diagnosis", "strategy", "steps", "breakIce", "coreTalk", "objections", "nextAction", "matchedCases"],
  additionalProperties: false,
} as const;

function textContent(content: unknown) {
  if (typeof content === "string") return content;
  if (Array.isArray(content)) return content.map(item => typeof item === "string" ? item : (item as { text?: string }).text ?? "").join("\n");
  return "";
}

const SYSTEM_PROMPT = `你是“攻单 AI”，面向分众传媒销售团队。你只能依据下面的内置知识库回答，不得虚构案例、数据、客户事实或文档外的分众能力。若信息不足，请明确指出缺口，并优先提出补充问题。你的任务是：根据客户背景判断七大客户类型的主类型与次类型，使用攻单五步法“听、认、比、算、定”给出下一步行动，自动匹配同类型案例，生成一句话破冰、核心沟通话术和异议应对。输出要具体、克制、可执行；涉及案例数据时只能使用知识库中的原文数字，并标注“文档案例数据”。\n\n内置知识库：\n${KNOWLEDGE_BASE}`;

export const appRouter = router({
  system: systemRouter,
  auth: router({
    me: publicProcedure.query(opts => opts.ctx.user),
    logout: publicProcedure.mutation(({ ctx }) => {
      const cookieOptions = getSessionCookieOptions(ctx.req);
      ctx.res.clearCookie(COOKIE_NAME, { ...cookieOptions, maxAge: -1 });
      return { success: true } as const;
    }),
  }),
  gongdan: router({
    diagnose: publicProcedure.input(clientInputSchema).mutation(async ({ input }) => {
      const response = await invokeLLM({
        model: "gpt-5-mini",
        messages: [
          { role: "system", content: SYSTEM_PROMPT },
          { role: "user", content: `请诊断以下客户，并严格按 JSON Schema 输出。客户信息：\n行业：${input.industry}\n规模：${input.scale}\n老板关键词：${input.keywords}\n竞争状态：${input.competition}\n当前目标：${input.goal}\n补充背景：${input.background}` },
        ],
        response_format: { type: "json_schema", json_schema: { name: "gongdan_playbook", strict: true, schema: playbookSchema } },
        reasoning: { effort: "low" },
      });
      const raw = textContent(response.choices?.[0]?.message?.content);
      try {
        const parsed = JSON.parse(raw) as Record<string, unknown>;
        const primaryType = String(parsed.primaryType ?? "");
        const secondaryType = String(parsed.secondaryType ?? "");
        return { ...parsed, matchedCases: getMatchedCases(primaryType, secondaryType) };
      } catch { throw new Error("AI 返回格式异常，请重试"); }
    }),
    chat: publicProcedure.input(z.object({ messages: z.array(chatMessageSchema).min(1).max(20) })).mutation(async ({ input }) => {
      const response = await invokeLLM({
        model: "gpt-5-mini",
        messages: [{ role: "system", content: SYSTEM_PROMPT }, ...input.messages],
        reasoning: { effort: "low" },
      });
      return { content: textContent(response.choices?.[0]?.message?.content) };
    }),
    knowledge: publicProcedure.query(() => ({ customerTypes: CUSTOMER_TYPES, cases: CASES, fiveSteps: FIVE_STEPS, objections: OBJECTIONS })),
    save: protectedProcedure.input(z.object({ title: z.string().min(1).max(180), clientSummary: z.string().min(1), primaryType: z.string().min(1), secondaryType: z.string().optional(), diagnosis: z.string().min(1), playbook: z.string().min(1) })).mutation(async ({ ctx, input }) => createDealSession({ ...input, userId: ctx.user.id })),
    list: protectedProcedure.query(({ ctx }) => listDealSessions(ctx.user.id)),
    get: protectedProcedure.input(z.object({ id: z.number().int().positive() })).query(({ ctx, input }) => getDealSession(ctx.user.id, input.id)),
  }),
});

export type AppRouter = typeof appRouter;
