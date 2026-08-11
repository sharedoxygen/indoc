/** Plain-language help for Insight Bridge (autonomous research UI). */

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

export const AGENT_HELP = {
  productName: 'Insight Bridge',
  pageTitle:
    'Autonomous research over your corpus: plans, searches, reads, and synthesizes a grounded brief from the documents you scope.',
  pageSubtitle:
    'Defaults to your full indexed corpus. State an objective and Run — refine scope only when you need a subset.',
  modeAgent: 'Multi-step research: plans actions, uses tools, then delivers a brief over the scoped corpus.',
  askFollowUp:
    'Open conversational Q&A over the same scoped documents, with this brief as context. Not a separate research mode.',
  followUpHistory: 'Prior follow-up conversations from Ask follow-up (not Insight runs).',
  history: 'Prior follow-up conversations. Insight briefs stay on the Brief Board.',
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
    'Live research console: step rail, streaming reasoning, and a continuous activity log. Finished answers land on the Brief Board below.',
  status: 'idle = ready · planning = deciding · tool = executing · completed = done · error = failed',
  holding: 'Waiting on the model or an active tool.',
  progress: 'Completed steps vs the max-step budget for this run (soft fill while planning).',
  toolsUsed: 'Distinct tools used at least once in this run.',
  steps: 'Completed tool steps vs max allowed. “iter” is the planner iteration count.',
  towerRadio: 'Live reasoning stream — typewriter feed of planner thoughts.',
  cargo: 'Last tool observation (search hits, document excerpt, etc.).',
  arrival: 'Final brief from this run.',
  arrivalBoard: 'Completed briefs for this browser session. Not permanent history.',
  flightStep: 'One tool call: action name plus a short thought or observation preview.',
  atcHub: 'The planner (ReAct loop). It chooses the next tool, reads the result, then continues until FINISH.',
  radar:
    'Instrument rail left→right. Amber pulse = active · green = done · muted = unused. Edges shimmer while work is in flight.',
} as const
