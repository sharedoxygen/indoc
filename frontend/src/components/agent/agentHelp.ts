/** Plain-language help for Research Desk (autonomous research UI). */

export const TOOL_HELP: Record<string, { short: string; help: string }> = {
  list_documents: {
    short: 'LIST',
    help: 'Lists documents in your current corpus (id, title, type). Often the first move to survey what is available.',
  },
  search_documents: {
    short: 'SEARCH',
    help: 'Hybrid keyword + semantic search across scoped docs. Surfaces the most relevant passages for the brief.',
  },
  read_document: {
    short: 'READ',
    help: 'Reads the full text of one document by id to extract specific facts or quotes.',
  },
  summarize_document: {
    short: 'SUM',
    help: 'Produces a concise summary of one document. Prefer this over READ when you only need the gist.',
  },
  compare_documents: {
    short: 'CMP',
    help: 'Compares two or more documents and returns key similarities and differences.',
  },
  finish: {
    short: 'FINISH',
    help: 'Closes the brief with a grounded final answer. Activates when synthesis is complete.',
  },
}

/** Hover copy for live instrument cluster gauges. */
export const INSTRUMENT_HELP = {
  cluster:
    'Live instrument cluster for this research run. Budget, tempo, coverage, and the tool chronograph update as the agent plans and executes.',
  budget: {
    title: 'Budget dial',
    body: 'How much of the step budget this run has consumed. At 100% the agent must finish or stop — it cannot take further tool steps.',
    footer: 'Driven by completed steps ÷ max steps. Soft pulse while the planner is thinking between tools.',
  },
  tempo: {
    title: 'Tempo gauge',
    body: 'How fast the agent is working, in tool steps per minute. Higher means denser tool calls; low or “—” means idle or just starting.',
    footer: 'Needle maps relative pace. The readout is the live steps/min rate.',
  },
  coverage: {
    title: 'Coverage meter',
    body: 'Share of the available instrument catalog used at least once in this run (LIST, SEARCH, READ, SUM, CMP, FINISH).',
    footer: 'Low coverage early is normal. Broad research often mixes SEARCH with a few deep dives — not every tool.',
  },
  stageRing: {
    title: 'Instrument chronograph',
    body: 'Pipeline of research instruments. Thin arcs light as each tool fires. Center count = completed tool steps so far.',
    footer: 'Colors: amber = active · green = done · red = failed · muted = not used yet. Hover a stage label for that tool’s role.',
  },
  phase: {
    title: 'Phase',
    body: 'Current ReAct loop state: PLANNING (choosing next action), EXECUTING (tool in flight), COMPLETED, ERROR, or IDLE.',
  },
  elapsed: {
    title: 'Elapsed',
    body: 'Wall-clock time since this research run started (m:ss). Resets when you launch a new run.',
  },
  steps: {
    title: 'Steps',
    body: 'Completed tool steps versus the max-steps cap for this run. When the numerator hits the denominator, the agent must synthesize and finish.',
  },
} as const

export const AGENT_HELP = {
  productName: 'Research Desk',
  pageTitle:
    'Autonomous research over your corpus: plans, searches, reads, and synthesizes a grounded brief from the documents you scope.',
  pageSubtitle:
    'Defaults to your full indexed corpus. State an objective and Run — refine scope only when you need a subset.',
  modeAgent: 'Multi-step research: plans actions, uses tools, then delivers a brief over the scoped corpus.',
  askFollowUp:
    'Open conversational Q&A over the same scoped documents, with this brief as context. Not a separate research mode.',
  followUpHistory: 'Prior follow-up conversations from Ask follow-up (not Research Desk runs).',
  history: 'Prior follow-up conversations. Research Desk briefs stay on the Brief Board.',
  scope:
    'What the agent can read. By default: all indexed documents. Open Refine only to narrow the set.',
  scopeMeter: 'How much of the indexed corpus is included in this run.',
  scopeSelectAll: 'Select or clear documents currently shown in Refine.',
  scopeSearch: 'Search within Refine. Already-selected docs outside the filter stay selected until you clear them.',
  missionGoal:
    'Your research objective — e.g. “Summarize key risks across these contracts” or “Compare renewal terms in the selected PDFs.”',
  launch: 'Start research. The agent plans steps and calls tools until it finishes or hits the step limit.',
  abort: 'Stop the current run immediately.',
  advanced: 'Max steps caps tool calls. Scope is the number of documents currently included.',
  maxSteps:
    'Upper limit on reasoning/tool steps per run. Higher = more thorough but slower. Typical: 4–8.',
  controlTower:
    'Live research console: precision instrument cluster (budget, tempo, coverage, tool ring), streaming reasoning, and activity. Hover any dial for a full readout. Briefs land on the Brief Board.',
  status: 'idle = ready · planning = deciding · tool = executing · completed = done · error = failed',
  holding: 'Waiting on the model or an active tool.',
  progress:
    'Budget = step budget used. Tempo = steps/min. Coverage = distinct tools fired. Ring = instrument pipeline. Hover each for live reading + details.',
  toolsUsed: 'Distinct tools used at least once in this run.',
  steps: 'Completed tool steps vs max allowed. “iter” is the planner iteration count.',
  towerRadio: 'Live reasoning stream — typewriter feed of planner thoughts.',
  cargo: 'Last tool observation (search hits, document excerpt, etc.).',
  arrival: 'Final brief from this run.',
  arrivalBoard:
    'Session briefs sit beside the console. Pick a run in the list, read the full answer, then follow up, copy, or reuse the objective. Cleared when you clear the board or close the tab.',
  briefFilter:
    'Narrow the brief list by objective text and status (Complete / Partial). The reader stays on the selected brief even if it is temporarily filtered out.',
  flightStep: 'One tool call: action name plus a short thought or observation preview.',
  atcHub: 'The planner (ReAct loop). It chooses the next tool, reads the result, then continues until FINISH.',
  radar:
    'Instrument rail left→right. Amber pulse = active · green = done · muted = unused. Edges shimmer while work is in flight.',
} as const
