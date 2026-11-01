import React, { useEffect, useState } from "react";
import { Box, Button, Collapse, Paper, Typography } from "@mui/material";
import { ExpandMore as ExpandMoreIcon } from "@mui/icons-material";
import AgentTheaterScene from "./AgentTheaterScene";
import AgentInstrumentCluster from "./AgentInstrumentCluster";
import type {
  AgentPhase,
  AgentStep,
  AgentStreamStatus,
} from "../../hooks/useAgentStream";

interface AgentTheaterProps {
  status: AgentStreamStatus;
  phase: AgentPhase;
  tools: string[];
  steps: AgentStep[];
  holding: boolean;
  finalAnswer: string | null;
  maxSteps: number;
  iterations: number;
  stoppedReason: string | null;
  error: string | null;
  goal?: string;
  activeAction?: string | null;
  activeThought?: string | null;
  startedAt?: number | null;
  /** `dock` sits under the brief. `console` is the full instrument view on a narrow screen. */
  presentation?: "dock" | "console";
  reasoningOpen?: boolean;
  onToggleReasoning?: () => void;
}

export function useConsoleClock(
  status: AgentStreamStatus,
  startedAt: number | null | undefined,
  maxSteps: number,
  stepCount: number,
  phase: AgentPhase,
) {
  const [elapsed, setElapsed] = useState(0);
  const isLive = status === "running" || status === "connecting";

  useEffect(() => {
    if (!isLive || !startedAt) {
      setElapsed(0);
      return;
    }
    const tick = () =>
      setElapsed(Math.max(0, Math.floor((Date.now() - startedAt) / 1000)));
    tick();
    const id = window.setInterval(tick, 200);
    return () => window.clearInterval(id);
  }, [isLive, startedAt]);

  const hardProgress =
    maxSteps > 0 ? Math.min(100, (stepCount / maxSteps) * 100) : 0;
  const softBoost =
    isLive && stepCount === 0
      ? Math.min(16, elapsed * 1.8)
      : isLive && phase === "planning"
        ? Math.min(9, 2 + (elapsed % 10))
        : 0;
  const progress =
    status === "completed" ? 100 : Math.min(99, hardProgress + softBoost);

  return { elapsed, progress, isLive };
}

export const AgentTheater: React.FC<AgentTheaterProps> = ({
  status,
  phase,
  tools,
  steps,
  holding,
  finalAnswer,
  maxSteps,
  error,
  activeAction,
  activeThought,
  startedAt,
  presentation = "dock",
  reasoningOpen = false,
  onToggleReasoning,
}) => {
  const { elapsed, progress, isLive } = useConsoleClock(
    status,
    startedAt,
    maxSteps,
    steps.length,
    phase,
  );

  const scene = (
    <AgentTheaterScene
      status={status}
      phase={phase}
      tools={tools}
      steps={steps}
      holding={holding}
      finalAnswer={finalAnswer}
      activeAction={activeAction}
      activeThought={activeThought}
      elapsed={elapsed}
      maxSteps={maxSteps}
      variant={presentation === "dock" ? "dock" : "stage"}
    />
  );

  const cluster = (
    <AgentInstrumentCluster
      status={status}
      phase={phase}
      steps={steps}
      tools={tools}
      maxSteps={maxSteps}
      elapsed={elapsed}
      progress={progress}
      activeAction={activeAction}
      density={presentation === "dock" ? "rail" : "panel"}
      framed={presentation !== "dock"}
      headerAction={
        presentation === "dock" ? (
          <Button
            size="small"
            onClick={onToggleReasoning}
            aria-expanded={reasoningOpen}
            aria-controls="research-reasoning"
            endIcon={
              <ExpandMoreIcon
                sx={{
                  transform: reasoningOpen ? "rotate(180deg)" : "none",
                  transition: "transform 0.15s ease",
                }}
              />
            }
            sx={{
              textTransform: "none",
              fontWeight: 700,
              color: isLive ? "primary.main" : "text.secondary",
              flexShrink: 0,
            }}
          >
            {isLive ? "Reasoning · live" : "Reasoning"}
          </Button>
        ) : undefined
      }
    />
  );

  if (presentation === "console") {
    return (
      <Box
        sx={{
          height: "100%",
          minHeight: 0,
          display: "flex",
          flexDirection: "column",
          gap: 1,
          overflow: "auto",
        }}
      >
        {cluster}
        <Box sx={{ flex: 1, minHeight: 360 }}>{scene}</Box>
        {error && (
          <Typography
            color="error"
            variant="body2"
            sx={{ flexShrink: 0, wordBreak: "break-word" }}
          >
            {error}
          </Typography>
        )}
      </Box>
    );
  }

  return (
    <Paper
      sx={{
        flexShrink: 0,
        borderRadius: 2,
        border: "1px solid",
        borderColor: "divider",
        overflow: "hidden",
        bgcolor: "background.paper",
      }}
    >
      {cluster}
      <Collapse in={reasoningOpen}>
        <Box
          id="research-reasoning"
          sx={{
            height: 220,
            borderTop: "1px solid",
            borderColor: "divider",
            minHeight: 0,
          }}
        >
          {scene}
        </Box>
      </Collapse>
    </Paper>
  );
};

export default AgentTheater;
