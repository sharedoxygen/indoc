/** Plain-language help for the Agent Tower UI (aviation labels → what they mean). */

export const TOOL_HELP: Record<string, { short: string; help: string }> = {
  list_documents: {
    short: 'LIST',
    help: 'Lists documents in your current scope (id, title, type). The agent usually starts here to see what it can work with.',
  },
  search_documents: {
    short: 'SEARCH',
    help: 'Hybrid keyword + semantic search across scoped docs. Finds the most relevant documents and snippets for the goal.',
  },
  read_document: {
    short: 'READ',
    help: 'Reads the full text of one document by id to pull specific facts or quotes.',
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
    help: 'Ends the run with a final answer grounded in what the agent gathered. Lights up when the mission completes.',
  },
}

export const AGENT_HELP = {
  pageTitle:
    'An autonomous research agent that plans steps (search, read, summarize, compare) over the documents you select in Scope, then returns a grounded answer.',
  pageSubtitle: 'Type a goal, pick docs in Scope, then Launch. The radar shows which tools the agent is using as it works.',
  modeAgent: 'Multi-step research agent: plans actions, uses tools, then answers.',
  modeChat: 'Normal Q&A chat over the selected documents (single turn style).',
  history: 'Past chat conversations. Agent mission results also appear on the Arrival Board below.',
  scope:
    'Documents the agent is allowed to use for this run. Check or uncheck items; use search only to find docs — selection can include items not currently shown in the filtered list.',
  scopeMeter:
    'How many of the currently listed (filtered) documents are checked. The count below shows total selected for the run vs how many appear in this list.',
  scopeSelectAll: 'Select or clear all documents currently shown in the filtered list.',
  scopeSearch: "Filter the list to find documents. Does not remove already-selected docs from the agent's scope.",
  missionGoal:
    'What you want the agent to accomplish — e.g. “Summarize key risks across these contracts” or “Compare renewal terms in the selected PDFs.”',
  launch: 'Start the agent. It will plan steps and call tools until it finishes or hits the max-step limit.',
  abort: 'Stop the current agent run immediately.',
  advanced:
    'Max steps caps how many tool calls the agent can make. Scope is the number of documents currently selected.',
  maxSteps:
    'Upper limit on reasoning/tool steps per run. Higher = more thorough but slower and more expensive. Typical: 4–8.',
  controlTower:
    'Live view of the agent run. The center is the planner; outer pads are tools. Planes fly to a pad when that tool is used.',
  status: 'idle = waiting · connecting/running = working · completed = done · error = failed',
  holding: 'The agent is waiting on a tool or model response (holding pattern).',
  progress:
    'Share of the max-step budget used so far (steps taken ÷ max steps). Reaches 100% when the step limit is hit.',
  toolsUsed: 'How many distinct tools the agent has used at least once in this run.',
  steps: 'Completed tool steps vs the max allowed for this run. “iter” is the planner iteration count.',
  towerRadio:
    'Live thought stream from the agent — what it is considering before choosing the next tool.',
  cargo: 'Observation returned by the last tool call (search hits, document text snippet, etc.).',
  arrival: 'Final answer from this run.',
  arrivalBoard:
    'Completed missions for this browser session: goal + final answer, so you can reuse them. Not permanent history.',
  flightStep: 'One tool call in the run: action name plus a short thought or observation preview.',
  atcHub: 'The agent planner (ReAct loop). It decides the next tool, reads the result, then continues until FINISH.',
  radar:
    'Each pad is a tool the agent can call. Yellow = currently using · green = used earlier · grey = unused this run.',
} as const
