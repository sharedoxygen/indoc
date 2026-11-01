import { useSyncExternalStore } from "react";
import {
  getResearchDeskState,
  resetStream,
  runResearch,
  stopResearch,
  subscribeResearchDesk,
} from "../research/researchDeskSession";

export type {
  AgentPhase,
  AgentStep,
  AgentStreamState,
  AgentStreamStatus,
} from "../research/researchDeskSession";

export function useResearchDesk() {
  return useSyncExternalStore(
    subscribeResearchDesk,
    getResearchDeskState,
    getResearchDeskState,
  );
}

export function useAgentStream() {
  const stream = useResearchDesk().stream;
  return {
    ...stream,
    run: runResearch,
    reset: resetStream,
    stop: stopResearch,
  };
}
