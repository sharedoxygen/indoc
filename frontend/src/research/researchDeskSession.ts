/**
 * Research Desk session.
 *
 * Opening Documents (or any other route) unmounts the desk page. This store
 * lives outside that page, so the objective, the in-flight run, the corpus
 * scope, and the follow-up conversation stay in place. sessionStorage
 * restores them after a reload. A reload cannot resume an open event stream;
 * that run is left idle and the objective is kept.
 */

import { TokenManager } from "../services/tokenManager";

export interface AgentStep {
  step: number;
  thought: string;
  action: string;
  action_input: Record<string, unknown>;
  observation: string;
}

export type AgentStreamStatus =
  "idle" | "connecting" | "running" | "completed" | "error";
export type AgentPhase =
  "idle" | "connecting" | "planning" | "tool" | "completed" | "error";

export interface AgentStreamState {
  status: AgentStreamStatus;
  phase: AgentPhase;
  goal: string;
  tools: string[];
  steps: AgentStep[];
  finalAnswer: string | null;
  iterations: number;
  stoppedReason: string | null;
  error: string | null;
  maxSteps: number;
  holding: boolean;
  activeAction: string | null;
  activeThought: string | null;
  planningStep: number;
  startedAt: number | null;
}

export interface DeskRunRecord {
  id: string;
  goal: string;
  answer: string;
  at: string;
  steps: number;
}

export type ScopeMode = "all" | "custom";

export interface ResearchDeskState {
  draftGoal: string;
  maxSteps: number;
  documentIds: string[];
  /** `all` tracks the current indexed corpus. `custom` keeps an explicit set. */
  scopeMode: ScopeMode;
  conversationId: string | null;
  followUpBrief: DeskRunRecord | null;
  followUpOpen: boolean;
  followUpDraft: string;
  priorRuns: DeskRunRecord[];
  focusRunId: string | null;
  stream: AgentStreamState;
  lastHandledKey: string | null;
  pendingBriefNotice: DeskRunRecord | null;
  notifiedBriefId: string | null;
}

interface PersistedDesk {
  version: 1;
  draftGoal: string;
  maxSteps: number;
  documentIds: string[];
  scopeMode: ScopeMode;
  conversationId: string | null;
  followUpBrief: DeskRunRecord | null;
  followUpOpen: boolean;
  followUpDraft: string;
  priorRuns: DeskRunRecord[];
  focusRunId: string | null;
  stream: AgentStreamState;
  lastHandledKey: string | null;
}

interface AgentStreamEvent {
  type?: string;
  goal?: string;
  tools_available?: string[];
  step?: number;
  thought?: string;
  action?: string;
  action_input?: Record<string, unknown>;
  observation?: string;
  final_answer?: string;
  iterations?: number;
  stopped_reason?: string;
  message?: string;
}

const STORAGE_KEY = "indoc.research.desk";
const LEGACY_RUNS_KEY = "indoc.agent.runs";
const MAX_STORED_TEXT = 8000;

const listeners = new Set<() => void>();
let abortRef: AbortController | null = null;
let runToken = 0;
let briefSeq = 0;
let mutationsSealed = false;

function freshStream(): AgentStreamState {
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
  };
}

function freshDesk(): ResearchDeskState {
  return {
    draftGoal: "",
    maxSteps: 6,
    documentIds: [],
    scopeMode: "all",
    conversationId: null,
    followUpBrief: null,
    followUpOpen: false,
    followUpDraft: "",
    priorRuns: [],
    focusRunId: null,
    stream: freshStream(),
    lastHandledKey: null,
    pendingBriefNotice: null,
    notifiedBriefId: null,
  };
}

function storage(): Storage | null {
  try {
    if (typeof sessionStorage === "undefined") return null;
    return sessionStorage;
  } catch {
    return null;
  }
}

function clampSteps(value: unknown): number {
  const n = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(n)) return 6;
  return Math.min(12, Math.max(1, Math.round(n)));
}

function sameIds(a: string[], b: string[]): boolean {
  return a.length === b.length && a.every((id, index) => id === b[index]);
}

function isRun(value: unknown): value is DeskRunRecord {
  if (!value || typeof value !== "object") return false;
  const run = value as Partial<DeskRunRecord>;
  return (
    typeof run.id === "string" &&
    typeof run.goal === "string" &&
    typeof run.answer === "string" &&
    typeof run.at === "string" &&
    typeof run.steps === "number"
  );
}

function asSteps(value: unknown): AgentStep[] {
  if (!Array.isArray(value)) return [];
  const steps: AgentStep[] = [];
  for (const item of value) {
    if (!item || typeof item !== "object") continue;
    const step = item as Partial<AgentStep>;
    steps.push({
      step: typeof step.step === "number" ? step.step : 0,
      thought: typeof step.thought === "string" ? step.thought : "",
      action: typeof step.action === "string" ? step.action : "",
      action_input:
        step.action_input && typeof step.action_input === "object"
          ? (step.action_input as Record<string, unknown>)
          : {},
      observation: typeof step.observation === "string" ? step.observation : "",
    });
  }
  return steps;
}

function asStringList(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is string => typeof item === "string");
}

const STATUSES: AgentStreamStatus[] = [
  "idle",
  "connecting",
  "running",
  "completed",
  "error",
];
const PHASES: AgentPhase[] = [
  "idle",
  "connecting",
  "planning",
  "tool",
  "completed",
  "error",
];

function calmStream(raw: unknown): AgentStreamState {
  const blank = freshStream();
  if (!raw || typeof raw !== "object") return blank;
  const saved = raw as Partial<AgentStreamState>;
  const status = STATUSES.includes(saved.status as AgentStreamStatus)
    ? (saved.status as AgentStreamStatus)
    : "idle";
  const interrupted = status === "running" || status === "connecting";
  const phase = PHASES.includes(saved.phase as AgentPhase)
    ? (saved.phase as AgentPhase)
    : "idle";
  return {
    status: interrupted ? "idle" : status,
    phase: interrupted ? "idle" : phase,
    goal: typeof saved.goal === "string" ? saved.goal : "",
    tools: asStringList(saved.tools),
    steps: asSteps(saved.steps),
    finalAnswer:
      typeof saved.finalAnswer === "string" ? saved.finalAnswer : null,
    iterations: typeof saved.iterations === "number" ? saved.iterations : 0,
    stoppedReason:
      typeof saved.stoppedReason === "string" ? saved.stoppedReason : null,
    error: interrupted
      ? null
      : typeof saved.error === "string"
        ? saved.error
        : null,
    maxSteps: clampSteps(saved.maxSteps),
    holding: false,
    activeAction: interrupted
      ? null
      : typeof saved.activeAction === "string"
        ? saved.activeAction
        : null,
    activeThought: interrupted
      ? null
      : typeof saved.activeThought === "string"
        ? saved.activeThought
        : null,
    planningStep:
      typeof saved.planningStep === "number" ? saved.planningStep : 0,
    startedAt: typeof saved.startedAt === "number" ? saved.startedAt : null,
  };
}

export function hydratePersistedDesk(
  saved: PersistedDesk | null,
  legacyRuns: DeskRunRecord[],
): ResearchDeskState {
  const blank = freshDesk();
  if (!saved) {
    return { ...blank, priorRuns: legacyRuns.slice(0, 20) };
  }
  const documentIds = asStringList(saved.documentIds);
  const scopeMode: ScopeMode =
    saved.scopeMode === "custom" || saved.scopeMode === "all"
      ? saved.scopeMode
      : documentIds.length > 0
        ? "custom"
        : "all";
  return {
    ...blank,
    draftGoal: typeof saved.draftGoal === "string" ? saved.draftGoal : "",
    maxSteps: clampSteps(saved.maxSteps),
    documentIds,
    scopeMode,
    conversationId:
      typeof saved.conversationId === "string" ? saved.conversationId : null,
    followUpBrief: isRun(saved.followUpBrief) ? saved.followUpBrief : null,
    followUpOpen: Boolean(saved.followUpOpen),
    followUpDraft:
      typeof saved.followUpDraft === "string" ? saved.followUpDraft : "",
    priorRuns: Array.isArray(saved.priorRuns)
      ? saved.priorRuns.filter(isRun).slice(0, 20)
      : legacyRuns.slice(0, 20),
    focusRunId: typeof saved.focusRunId === "string" ? saved.focusRunId : null,
    stream: calmStream(saved.stream),
    lastHandledKey:
      typeof saved.lastHandledKey === "string" ? saved.lastHandledKey : null,
  };
}

function clip(value: string): string {
  return value.length > MAX_STORED_TEXT
    ? value.slice(0, MAX_STORED_TEXT)
    : value;
}

function persistable(desk: ResearchDeskState): PersistedDesk {
  return {
    version: 1,
    draftGoal: desk.draftGoal,
    maxSteps: desk.maxSteps,
    documentIds: desk.documentIds,
    scopeMode: desk.scopeMode,
    conversationId: desk.conversationId,
    followUpBrief: desk.followUpBrief
      ? { ...desk.followUpBrief, answer: clip(desk.followUpBrief.answer) }
      : null,
    followUpOpen: desk.followUpOpen,
    followUpDraft: desk.followUpDraft,
    priorRuns: desk.priorRuns.slice(0, 20).map((run) => ({
      ...run,
      answer: clip(run.answer),
    })),
    focusRunId: desk.focusRunId,
    lastHandledKey: desk.lastHandledKey,
    stream: {
      ...desk.stream,
      goal: clip(desk.stream.goal),
      error: desk.stream.error ? clip(desk.stream.error) : null,
      finalAnswer: desk.stream.finalAnswer
        ? clip(desk.stream.finalAnswer)
        : null,
      activeThought: desk.stream.activeThought
        ? clip(desk.stream.activeThought)
        : null,
      steps: desk.stream.steps.map((step) => ({
        ...step,
        thought: clip(step.thought),
        observation: clip(step.observation),
      })),
    },
  };
}

function writeStorage(desk: ResearchDeskState) {
  const store = storage();
  if (!store) return;
  const payload = persistable(desk);
  try {
    store.setItem(STORAGE_KEY, JSON.stringify(payload));
  } catch {
    try {
      store.setItem(
        STORAGE_KEY,
        JSON.stringify({
          ...payload,
          stream: { ...payload.stream, steps: [] },
          priorRuns: payload.priorRuns.map((run) => ({
            ...run,
            answer: run.answer.slice(0, 2000),
          })),
        }),
      );
    } catch {
      // The in-memory session still stands if this tab cannot store it.
    }
  }
}

function readSaved(): PersistedDesk | null {
  const raw = storage()?.getItem(STORAGE_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as PersistedDesk;
    if (!parsed || parsed.version !== 1) return null;
    return parsed;
  } catch {
    return null;
  }
}

function readLegacyRuns(): DeskRunRecord[] {
  const raw = storage()?.getItem(LEGACY_RUNS_KEY);
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter(isRun) : [];
  } catch {
    return [];
  }
}

let state: ResearchDeskState = hydratePersistedDesk(
  readSaved(),
  readLegacyRuns(),
);

function emit(options?: { persist?: boolean }) {
  if (options?.persist !== false && !mutationsSealed) writeStorage(state);
  for (const listener of [...listeners]) listener();
}

export function subscribeResearchDesk(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function getResearchDeskState(): ResearchDeskState {
  return state;
}

export function unsealResearchDesk() {
  mutationsSealed = false;
}

function canMutate(): boolean {
  return !mutationsSealed;
}

export function setDraftGoal(draftGoal: string) {
  if (!canMutate() || state.draftGoal === draftGoal) return;
  state = { ...state, draftGoal };
  emit();
}

export function setMaxSteps(maxSteps: number) {
  if (!canMutate()) return;
  const next = clampSteps(maxSteps);
  if (state.maxSteps === next) return;
  state = { ...state, maxSteps: next };
  emit();
}

export function setCorpus(documentIds: string[], scopeMode: ScopeMode) {
  if (!canMutate()) return;
  if (
    state.scopeMode === scopeMode &&
    sameIds(state.documentIds, documentIds)
  ) {
    return;
  }
  state = { ...state, documentIds, scopeMode };
  emit();
}

export function setConversationId(conversationId: string | null) {
  if (!canMutate() || state.conversationId === conversationId) return;
  state = { ...state, conversationId };
  emit();
}

export function setFollowUpBrief(followUpBrief: DeskRunRecord | null) {
  if (!canMutate() || state.followUpBrief === followUpBrief) return;
  state = { ...state, followUpBrief };
  emit();
}

export function setFollowUpOpen(followUpOpen: boolean) {
  if (!canMutate() || state.followUpOpen === followUpOpen) return;
  state = { ...state, followUpOpen };
  emit();
}

export function setFollowUpDraft(followUpDraft: string) {
  if (!canMutate() || state.followUpDraft === followUpDraft) return;
  state = { ...state, followUpDraft };
  emit();
}

export function clearBriefs() {
  if (!canMutate()) return;
  if (state.priorRuns.length === 0 && state.focusRunId === null) return;
  state = { ...state, priorRuns: [], focusRunId: null };
  storage()?.removeItem(LEGACY_RUNS_KEY);
  emit();
}

export function commitBriefInto(
  desk: ResearchDeskState,
  stream: AgentStreamState,
): ResearchDeskState {
  const base = { ...desk, stream };
  if (stream.status !== "completed" || !stream.finalAnswer) return base;
  const dedupeKey = `${stream.goal}::${stream.finalAnswer.slice(0, 80)}::${stream.iterations}`;
  if (desk.lastHandledKey === dedupeKey) return base;
  const run: DeskRunRecord = {
    id: `${Date.now().toString(36)}-${++briefSeq}`,
    goal: stream.goal,
    answer: stream.finalAnswer,
    at: new Date().toISOString(),
    steps: stream.steps.length || stream.iterations,
  };
  return {
    ...base,
    lastHandledKey: dedupeKey,
    priorRuns: [run, ...desk.priorRuns].slice(0, 20),
    focusRunId: run.id,
    followUpBrief: run,
    pendingBriefNotice: run,
  };
}

export function acknowledgeBriefNotice(id: string): boolean {
  if (!canMutate()) return false;
  if (state.notifiedBriefId === id) return false;
  if (state.pendingBriefNotice?.id !== id) return false;
  state = { ...state, notifiedBriefId: id, pendingBriefNotice: null };
  emit();
  return true;
}

export function reduceStreamEvent(
  prev: AgentStreamState,
  event: AgentStreamEvent,
): AgentStreamState {
  if (event.type === "start") {
    return {
      ...prev,
      status: "running",
      phase: "planning",
      tools: event.tools_available || [],
      goal: event.goal || prev.goal,
      holding: true,
      planningStep: 1,
    };
  }
  if (event.type === "planning") {
    return {
      ...prev,
      status: "running",
      phase: "planning",
      holding: true,
      planningStep: event.step || prev.planningStep + 1,
      activeAction: null,
      activeThought: null,
    };
  }
  if (event.type === "tool_start") {
    return {
      ...prev,
      status: "running",
      phase: "tool",
      holding: true,
      planningStep: event.step || prev.planningStep,
      activeAction: event.action || null,
      activeThought: event.thought || null,
    };
  }
  if (event.type === "step") {
    const step: AgentStep = {
      step: event.step || prev.steps.length + 1,
      thought: event.thought || "",
      action: event.action || "",
      action_input: event.action_input || {},
      observation: event.observation || "",
    };
    return {
      ...prev,
      steps: [...prev.steps, step],
      holding: true,
      phase: "planning",
      activeAction: step.action,
      activeThought: step.thought,
    };
  }
  if (event.type === "final") {
    return {
      ...prev,
      status: "completed",
      phase: "completed",
      finalAnswer: event.final_answer || "",
      iterations: event.iterations || prev.steps.length,
      stoppedReason: event.stopped_reason || "completed",
      holding: false,
      activeAction: "finish",
    };
  }
  if (event.type === "error") {
    return {
      ...prev,
      status: "error",
      phase: "error",
      error: event.message || "Agent error",
      holding: false,
    };
  }
  return prev;
}

function authHeaders(): Record<string, string> {
  if (typeof localStorage === "undefined") return {};
  const token = TokenManager.getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function isAbortError(err: unknown): boolean {
  return Boolean(
    err &&
    typeof err === "object" &&
    (err as { name?: string }).name === "AbortError",
  );
}

function applyStream(next: AgentStreamState, commit: boolean) {
  state = commit ? commitBriefInto(state, next) : { ...state, stream: next };
  emit();
}

export async function runResearch(params: {
  goal: string;
  documentIds?: string[];
  maxSteps?: number;
}) {
  if (!canMutate()) return;
  abortRef?.abort();
  const token = ++runToken;
  const controller = new AbortController();
  abortRef = controller;
  const maxSteps = clampSteps(params.maxSteps ?? state.maxSteps);
  const alive = () => token === runToken && !mutationsSealed;

  state = {
    ...state,
    lastHandledKey: null,
    stream: {
      ...freshStream(),
      status: "connecting",
      phase: "connecting",
      goal: params.goal,
      maxSteps,
      holding: true,
      startedAt: Date.now(),
    },
  };
  emit();

  try {
    const response = await fetch("/api/v1/agent/stream", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
        ...authHeaders(),
      },
      body: JSON.stringify({
        goal: params.goal,
        document_ids: params.documentIds?.length ? params.documentIds : null,
        max_steps: maxSteps,
      }),
      signal: controller.signal,
    });

    if (!alive()) return;
    if (!response.ok || !response.body) {
      const text = await response.text().catch(() => "");
      throw new Error(text || `Agent stream failed (${response.status})`);
    }

    applyStream(
      {
        ...state.stream,
        status: "running",
        phase: "planning",
        holding: true,
      },
      false,
    );

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (alive()) {
      const { done, value } = await reader.read();
      if (!alive()) return;
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const chunks = buffer.split("\n\n");
      buffer = chunks.pop() || "";

      for (const chunk of chunks) {
        if (!alive()) return;
        for (const line of chunk.split("\n")) {
          if (!line.startsWith("data:")) continue;
          const payload = line.slice(5).trim();
          if (!payload) continue;
          let event: AgentStreamEvent;
          try {
            event = JSON.parse(payload) as AgentStreamEvent;
          } catch {
            continue;
          }
          const next = reduceStreamEvent(state.stream, event);
          if (next === state.stream) continue;
          applyStream(next, event.type === "final");
        }
      }
    }

    if (!alive()) return;
    if (state.stream.status === "running") {
      applyStream(
        {
          ...state.stream,
          status: "completed",
          phase: "completed",
          holding: false,
          stoppedReason: state.stream.stoppedReason || "stream_ended",
        },
        false,
      );
    } else if (state.stream.holding) {
      applyStream({ ...state.stream, holding: false }, false);
    }
  } catch (err: unknown) {
    if (isAbortError(err) || !alive()) return;
    const message = err instanceof Error ? err.message : "Failed to run agent";
    applyStream(
      {
        ...state.stream,
        status: "error",
        phase: "error",
        error: message,
        holding: false,
      },
      false,
    );
  }
}

export function stopResearch() {
  if (!canMutate()) return;
  runToken += 1;
  abortRef?.abort();
  abortRef = null;
  const done = Boolean(state.stream.finalAnswer);
  applyStream(
    {
      ...state.stream,
      status: done ? "completed" : "idle",
      phase: done ? "completed" : "idle",
      holding: false,
    },
    false,
  );
}

export function resetStream() {
  if (!canMutate()) return;
  runToken += 1;
  abortRef?.abort();
  abortRef = null;
  applyStream(freshStream(), false);
}

export function resetResearchDesk() {
  runToken += 1;
  abortRef?.abort();
  abortRef = null;
  mutationsSealed = true;
  state = freshDesk();
  const store = storage();
  store?.removeItem(STORAGE_KEY);
  store?.removeItem(LEGACY_RUNS_KEY);
  emit({ persist: false });
}

/** Test-only. Drops listeners and starts from an empty unsealed desk. */
export function testingReset() {
  runToken += 1;
  abortRef?.abort();
  abortRef = null;
  mutationsSealed = false;
  listeners.clear();
  state = freshDesk();
}
