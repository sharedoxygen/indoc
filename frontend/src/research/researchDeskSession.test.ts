import assert from "node:assert/strict";
import { afterEach, beforeEach, describe, it } from "node:test";
import {
  acknowledgeBriefNotice,
  getResearchDeskState,
  hydratePersistedDesk,
  resetResearchDesk,
  runResearch,
  setCorpus,
  setDraftGoal,
  setFollowUpDraft,
  subscribeResearchDesk,
  testingReset,
  unsealResearchDesk,
  type AgentStreamState,
} from "./researchDeskSession.ts";

function freshStream(
  partial: Partial<AgentStreamState> = {},
): AgentStreamState {
  return {
    status: "idle",
    phase: "idle",
    goal: "",
    tools: [],
    steps: [],
    finalAnswer: null,
    iterations: 0,
    stoppedReason: null,
    error: null,
    maxSteps: 6,
    holding: false,
    activeAction: null,
    activeThought: null,
    planningStep: 0,
    startedAt: null,
    ...partial,
  };
}

describe("research desk session", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    testingReset();
  });

  afterEach(() => {
    testingReset();
    globalThis.fetch = originalFetch;
  });

  it("restores a saved objective, custom scope, and follow-up after reload", () => {
    const desk = hydratePersistedDesk(
      {
        version: 1,
        draftGoal: "Summarize contract risks",
        maxSteps: 8,
        documentIds: ["doc-1", "doc-2"],
        scopeMode: "custom",
        conversationId: "conv-9",
        followUpBrief: null,
        followUpOpen: true,
        followUpDraft: "What about liability?",
        priorRuns: [],
        focusRunId: null,
        lastHandledKey: null,
        stream: freshStream({
          status: "completed",
          phase: "completed",
          goal: "Summarize contract risks",
          finalAnswer: "Liability is capped.",
          iterations: 2,
        }),
      },
      [],
    );

    assert.equal(desk.draftGoal, "Summarize contract risks");
    assert.equal(desk.scopeMode, "custom");
    assert.deepEqual(desk.documentIds, ["doc-1", "doc-2"]);
    assert.equal(desk.conversationId, "conv-9");
    assert.equal(desk.followUpOpen, true);
    assert.equal(desk.followUpDraft, "What about liability?");
    assert.equal(desk.stream.finalAnswer, "Liability is capped.");
    assert.equal(desk.stream.status, "completed");
  });

  it("does not leave a reloaded run spinning", () => {
    const desk = hydratePersistedDesk(
      {
        version: 1,
        draftGoal: "Find renewal dates",
        maxSteps: 6,
        documentIds: ["doc-1"],
        scopeMode: "all",
        conversationId: null,
        followUpBrief: null,
        followUpOpen: false,
        followUpDraft: "",
        priorRuns: [],
        focusRunId: null,
        lastHandledKey: null,
        stream: freshStream({
          status: "running",
          phase: "tool",
          goal: "Find renewal dates",
          holding: true,
          steps: [
            {
              step: 1,
              thought: "search",
              action: "search_documents",
              action_input: {},
              observation: "two contracts",
            },
          ],
        }),
      },
      [],
    );

    assert.equal(desk.draftGoal, "Find renewal dates");
    assert.equal(desk.stream.status, "idle");
    assert.equal(desk.stream.holding, false);
    assert.equal(desk.stream.steps.length, 1);
    assert.equal(desk.stream.error, null);
  });

  it("keeps legacy briefs when the desk key is missing", () => {
    const desk = hydratePersistedDesk(null, [
      {
        id: "old",
        goal: "Prior question",
        answer: "Prior answer",
        at: "2026-01-01T00:00:00.000Z",
        steps: 3,
      },
    ]);
    assert.equal(desk.priorRuns.length, 1);
    assert.equal(desk.priorRuns[0].id, "old");
  });

  it("keeps the objective after the page unsubscribes", () => {
    const seen: string[] = [];
    const unsubscribe = subscribeResearchDesk(() => {
      seen.push(getResearchDeskState().draftGoal);
    });
    setDraftGoal("Open question");
    unsubscribe();
    setDraftGoal("Open question, still here");
    setFollowUpDraft("and the follow-up");
    assert.equal(getResearchDeskState().draftGoal, "Open question, still here");
    assert.equal(getResearchDeskState().followUpDraft, "and the follow-up");
    assert.deepEqual(seen, ["Open question"]);
  });

  it("finishes a run and saves the brief with no page mounted", async () => {
    let push: (chunk: string) => void = () => {};
    let close: () => void = () => {};
    const encoder = new TextEncoder();
    globalThis.fetch = async () => {
      const stream = new ReadableStream<Uint8Array>({
        start(controller) {
          push = (chunk: string) => controller.enqueue(encoder.encode(chunk));
          close = () => controller.close();
        },
      });
      return new Response(stream, { status: 200 });
    };

    setDraftGoal("Summarize risks");
    setCorpus(["doc-1"], "custom");
    const pending = runResearch({
      goal: "Summarize risks",
      documentIds: ["doc-1"],
      maxSteps: 4,
    });

    await new Promise((resolve) => setTimeout(resolve, 0));
    push(
      'data: {"type":"start","goal":"Summarize risks","tools_available":["search_documents"]}\n\n',
    );

    for (
      let i = 0;
      i < 20 && getResearchDeskState().stream.status !== "running";
      i += 1
    ) {
      await new Promise((resolve) => setTimeout(resolve, 10));
    }
    assert.equal(getResearchDeskState().stream.status, "running");

    push(
      'data: {"type":"final","final_answer":"The risks are low.","iterations":2,"stopped_reason":"completed"}\n\n',
    );
    close();
    await pending;

    const desk = getResearchDeskState();
    assert.equal(desk.draftGoal, "Summarize risks");
    assert.deepEqual(desk.documentIds, ["doc-1"]);
    assert.equal(desk.scopeMode, "custom");
    assert.equal(desk.stream.status, "completed");
    assert.equal(desk.stream.finalAnswer, "The risks are low.");
    assert.equal(desk.priorRuns.length, 1);
    assert.equal(desk.priorRuns[0].goal, "Summarize risks");
    assert.equal(desk.pendingBriefNotice?.answer, "The risks are low.");
    assert.equal(acknowledgeBriefNotice(desk.pendingBriefNotice!.id), true);
    assert.equal(getResearchDeskState().pendingBriefNotice, null);
    assert.equal(acknowledgeBriefNotice(desk.pendingBriefNotice!.id), false);
  });

  it("drops the session on logout and ignores late writes until the desk opens again", () => {
    setDraftGoal("secret objective");
    setCorpus(["doc-1"], "custom");
    resetResearchDesk();
    setDraftGoal("should not stick");
    setCorpus(["doc-2"], "custom");
    assert.equal(getResearchDeskState().draftGoal, "");
    assert.deepEqual(getResearchDeskState().documentIds, []);
    unsealResearchDesk();
    setDraftGoal("next session");
    assert.equal(getResearchDeskState().draftGoal, "next session");
  });
});
