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
  pageSubtitle: 'State an objective, confirm corpus scope, then Run. Live orchestration shows each tool as it fires.',
  modeAgent: 'Multi-step research: plans actions, uses tools, then delivers a brief.',
  modeChat: 'Conversational Q&A over the selected documents.',
  history: 'Past chat conversations. Completed briefs also appear on the Brief board below.',
  scope:
    'Corpus the agent may use. Defaults to all indexed documents. Open “Refine corpus” only when you need a subset.',
  scopeMeter: 'Share of the filtered list currently included in scope.',
  scopeSelectAll: 'Include or clear all documents currently shown in the refine list.',
  scopeSearch: 'Filter the refine list. Does not drop already-scoped documents outside the filter.',
  missionGoal:
    'Your research objective — e.g. “Summarize key risks across these contracts” or “Compare renewal terms in the selected PDFs.”',
  launch: 'Start research. The agent plans steps and calls tools until it finishes or hits the step limit.',
  abort: 'Stop the current run immediately.',
  advanced: 'Max steps caps tool calls. Scope is the number of documents currently included.',
  maxSteps:
    'Upper limit on reasoning/tool steps per run. Higher = more thorough but slower. Typical: 4–8.',
  controlTower:
    'Live research console: horizontal instrument rail, streaming reasoning, and a continuous activity log so the run never feels idle.',
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
