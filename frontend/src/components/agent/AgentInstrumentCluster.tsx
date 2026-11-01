import React, { useEffect, useMemo, useState, type ReactNode } from "react";
import {
  Box,
  LinearProgress,
  Paper,
  Stack,
  Typography,
  useTheme,
} from "@mui/material";
import { motion, useReducedMotion } from "framer-motion";
import {
  ArcMeter,
  InstrumentTooltip,
  LiveTicker,
  NeedleGauge,
  PrecisionDial,
  SegmentRing,
} from "../instruments";
import type { SegmentStatus } from "../instruments";
import type {
  AgentPhase,
  AgentStep,
  AgentStreamStatus,
} from "../../hooks/useAgentStream";
import { INSTRUMENT_HELP, TOOL_HELP } from "./agentHelp";

const PIPELINE = [
  "list_documents",
  "search_documents",
  "read_document",
  "summarize_document",
  "compare_documents",
  "finish",
] as const;

interface AgentInstrumentClusterProps {
  status: AgentStreamStatus;
  phase: AgentPhase;
  steps: AgentStep[];
  tools: string[];
  maxSteps: number;
  elapsed: number;
  progress: number;
  activeAction?: string | null;
  /** `rail` is the short desk dock: face + digital readout, hairline execution scale. */
  density?: "panel" | "rail";
  /** Draw the cluster's own card. The desk dock supplies the card instead. */
  framed?: boolean;
  headerAction?: ReactNode;
}

function formatClock(totalSeconds: number) {
  const m = Math.floor(totalSeconds / 60);
  const s = totalSeconds % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function statusWord(
  status: AgentStreamStatus,
  isLive: boolean,
  isDone: boolean,
  isError: boolean,
) {
  if (isError) return "error";
  if (isDone) return "complete";
  if (isLive) return "live";
  return status || "idle";
}

/** Live precision cluster — budget, tempo, coverage, instrument pipeline. */
export const AgentInstrumentCluster: React.FC<AgentInstrumentClusterProps> = ({
  status,
  phase,
  steps,
  tools,
  maxSteps,
  elapsed,
  progress,
  activeAction,
  density = "panel",
  framed = true,
  headerAction,
}) => {
  const theme = useTheme();
  const reduceMotion = useReducedMotion();
  const dark = theme.palette.mode === "dark";
  const isLive = status === "running" || status === "connecting";
  const isDone = status === "completed";
  const isError = status === "error";

  const [pulse, setPulse] = useState(0);
  useEffect(() => {
    if (!isLive || reduceMotion) {
      setPulse(0);
      return;
    }
    const id = window.setInterval(() => setPulse((p) => (p + 1) % 100), 180);
    return () => window.clearInterval(id);
  }, [isLive, reduceMotion]);

  const catalog = tools.length ? tools : [...PIPELINE];
  const used = useMemo(() => new Set(steps.map((s) => s.action)), [steps]);
  const toolCoverage = catalog.length ? (used.size / catalog.length) * 100 : 0;
  const stepsPerMin =
    elapsed > 0 ? steps.length / Math.max(elapsed / 60, 0.01) : 0;
  const tempo =
    elapsed > 0
      ? Math.min(100, stepsPerMin * 12)
      : isLive
        ? 8 + (pulse % 12)
        : 0;
  const liveBudget = Math.min(
    99,
    progress + (isLive && phase === "planning" ? (pulse % 5) * 0.35 : 0),
  );
  const budgetValue = isDone ? 100 : liveBudget;
  const runState = statusWord(status, isLive, isDone, isError);

  const segments = PIPELINE.map((tool) => {
    let segStatus: SegmentStatus = "pending";
    if (isError && activeAction === tool) segStatus = "failed";
    else if (activeAction === tool && isLive) segStatus = "active";
    else if (used.has(tool) || (isDone && tool === "finish"))
      segStatus = "complete";
    const short = TOOL_HELP[tool]?.short || tool.slice(0, 4).toUpperCase();
    const hits = steps.filter((s) => s.action === tool).length;
    const toolHelp = TOOL_HELP[tool];
    return {
      key: tool,
      label: short,
      status: segStatus,
      value:
        hits || (segStatus === "complete" || segStatus === "active" ? 1 : 0),
      help: {
        title: `${short} · ${tool.replace(/_/g, " ")}`,
        body: toolHelp?.help || "Research instrument in the agent pipeline.",
        reading: `Status: ${segStatus}${hits ? ` · ${hits} call${hits === 1 ? "" : "s"}` : ""}`,
        details: [
          { label: "Calls this run", value: String(hits) },
          { label: "State", value: segStatus },
        ],
        footer:
          segStatus === "pending"
            ? "Not used yet in this run — the planner may still choose it."
            : segStatus === "active"
              ? "Currently engaged by the agent."
              : segStatus === "failed"
                ? "This tool call failed; check the activity log."
                : "Already used at least once in this run.",
      },
    };
  });

  const dialStatus = isError
    ? "error"
    : isDone
      ? "ok"
      : isLive
        ? "active"
        : "idle";
  const phaseLabel =
    phase === "planning" || phase === "connecting"
      ? "PLANNING"
      : phase === "tool"
        ? "EXECUTING"
        : status.toUpperCase();

  const tempoReadout = elapsed > 0 ? `${stepsPerMin.toFixed(1)}/m` : "—";
  const rail = density === "rail";
  const face = rail ? "inline" : "stack";
  const dialSize = rail ? 76 : 104;
  const gaugeSize = rail ? 92 : 100;
  const arcSize = rail ? 92 : 98;
  const ringSize = rail ? 76 : 118;

  const body = (
    <Box
      sx={{
        p: rail ? { xs: 1, md: 1.25 } : { xs: 1, md: 1.25 },
        position: "relative",
        overflow: "hidden",
      }}
    >
      {isLive && !reduceMotion && !rail && (
        <Box
          component={motion.div}
          aria-hidden
          animate={{ x: ["-30%", "130%"] }}
          transition={{ duration: 2.8, repeat: Infinity, ease: "linear" }}
          sx={{
            position: "absolute",
            top: 0,
            bottom: 0,
            width: "28%",
            background:
              "linear-gradient(90deg, transparent, rgba(56,189,248,0.07), transparent)",
            pointerEvents: "none",
          }}
        />
      )}

      <Stack
        direction="row"
        justifyContent="space-between"
        alignItems="center"
        sx={{ mb: 1, position: "relative", minWidth: 0 }}
        flexWrap="wrap"
        gap={1}
      >
        <InstrumentTooltip
          help={{
            title: "Live instrument cluster",
            body: INSTRUMENT_HELP.cluster,
            reading: `Run · ${runState}`,
            details: [
              { label: "Phase", value: phaseLabel },
              { label: "Elapsed", value: formatClock(elapsed) },
              { label: "Steps", value: `${steps.length}/${maxSteps}` },
            ],
            footer:
              "Hover any dial, meter, ticker, or stage label for a full readout.",
          }}
        >
          <Typography
            variant="caption"
            sx={{
              fontWeight: 750,
              letterSpacing: 0.8,
              color: "text.secondary",
              cursor: "help",
            }}
          >
            INSTRUMENTS
          </Typography>
        </InstrumentTooltip>
        <Stack
          direction="row"
          spacing={1}
          alignItems="center"
          flexWrap="wrap"
          useFlexGap
        >
          <LiveTicker
            label="Phase"
            value={phaseLabel}
            live={isLive}
            accent={
              isError
                ? "error.main"
                : isDone
                  ? "success.main"
                  : phase === "tool"
                    ? "warning.main"
                    : "primary.main"
            }
            help={{
              ...INSTRUMENT_HELP.phase,
              reading: phaseLabel,
              details: [
                { label: "Stream status", value: status },
                { label: "Active tool", value: activeAction || "—" },
              ],
            }}
          />
          <LiveTicker
            label="Elapsed"
            value={formatClock(elapsed)}
            live={isLive}
            accent="info.main"
            help={{
              ...INSTRUMENT_HELP.elapsed,
              reading: formatClock(elapsed),
              details: [
                { label: "Seconds", value: String(elapsed) },
                {
                  label: "Steps/min",
                  value: elapsed > 0 ? stepsPerMin.toFixed(2) : "—",
                },
              ],
            }}
          />
          <LiveTicker
            label="Steps"
            value={`${steps.length}/${maxSteps}`}
            live={false}
            accent="text.secondary"
            help={{
              ...INSTRUMENT_HELP.steps,
              reading: `${steps.length} of ${maxSteps}`,
              details: [
                { label: "Completed", value: String(steps.length) },
                {
                  label: "Budget left",
                  value: String(Math.max(0, maxSteps - steps.length)),
                },
                { label: "Budget used", value: `${Math.round(budgetValue)}%` },
              ],
            }}
          />
          {headerAction}
        </Stack>
      </Stack>

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: rail
            ? "repeat(auto-fit, minmax(168px, 1fr))"
            : { xs: "1fr 1fr", sm: "repeat(4, minmax(0, 1fr))" },
          gap: { xs: 1, md: rail ? 2 : 1 },
          alignItems: "center",
          position: "relative",
        }}
      >
        <Box
          sx={{
            display: "flex",
            justifyContent: rail ? "flex-start" : "center",
            minWidth: 0,
          }}
        >
          <PrecisionDial
            value={budgetValue}
            label="Budget"
            unit="%"
            precision={0}
            size={dialSize}
            layout={face}
            showScaleNumbers={!rail}
            status={dialStatus}
            animate
            help={{
              ...INSTRUMENT_HELP.budget,
              reading: `${Math.round(budgetValue)}% · ${runState}`,
              details: [
                { label: "Steps used", value: `${steps.length}/${maxSteps}` },
                { label: "Phase", value: phaseLabel },
                { label: "Status", value: dialStatus },
              ],
            }}
          />
        </Box>
        <Box
          sx={{
            display: "flex",
            justifyContent: rail ? "flex-start" : "center",
            minWidth: 0,
          }}
        >
          <NeedleGauge
            value={Math.min(100, tempo)}
            label="Tempo"
            displayValue={tempoReadout}
            size={gaugeSize}
            layout={face}
            showScaleNumbers={!rail}
            status={isLive ? "active" : isDone ? "ok" : "idle"}
            help={{
              ...INSTRUMENT_HELP.tempo,
              reading: `${tempoReadout} · needle ${Math.round(Math.min(100, tempo))}%`,
              details: [
                { label: "Steps", value: String(steps.length) },
                { label: "Elapsed", value: formatClock(elapsed) },
                {
                  label: "Rate",
                  value:
                    elapsed > 0
                      ? `${stepsPerMin.toFixed(2)} steps/min`
                      : "warming up",
                },
              ],
            }}
          />
        </Box>
        <Box
          sx={{
            display: "flex",
            justifyContent: rail ? "flex-start" : "center",
            minWidth: 0,
          }}
        >
          <ArcMeter
            value={toolCoverage}
            label="Coverage"
            subtitle={`${used.size}/${catalog.length}`}
            unit="%"
            precision={0}
            size={arcSize}
            layout={face}
            showScaleNumbers={!rail}
            status={toolCoverage >= 50 ? "ok" : isLive ? "warn" : "idle"}
            help={{
              ...INSTRUMENT_HELP.coverage,
              reading: `${Math.round(toolCoverage)}% · ${used.size}/${catalog.length} tools`,
              details: [
                {
                  label: "Used",
                  value: used.size ? [...used].join(", ") : "—",
                },
                { label: "Catalog", value: String(catalog.length) },
                {
                  label: "Unused",
                  value: String(Math.max(0, catalog.length - used.size)),
                },
              ],
              footer: INSTRUMENT_HELP.coverage.footer,
            }}
          />
        </Box>
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: rail ? "flex-start" : "center",
            minWidth: 0,
          }}
        >
          {rail ? (
            <InstrumentTooltip
              help={{
                ...INSTRUMENT_HELP.stageRing,
                reading: `${steps.length} steps · ${runState}`,
                details: [
                  {
                    label: "Active",
                    value: activeAction
                      ? TOOL_HELP[activeAction]?.short || activeAction
                      : "—",
                  },
                  {
                    label: "Complete arcs",
                    value: String(
                      segments.filter((s) => s.status === "complete").length,
                    ),
                  },
                  {
                    label: "Pending arcs",
                    value: String(
                      segments.filter((s) => s.status === "pending").length,
                    ),
                  },
                ],
              }}
            >
              <Box
                sx={{
                  display: "flex",
                  alignItems: "center",
                  gap: 1.25,
                  minWidth: 0,
                  width: "100%",
                }}
              >
                <Box sx={{ width: ringSize, flexShrink: 0 }}>
                  <SegmentRing
                    segments={segments}
                    size={ringSize}
                    showLegend={false}
                  />
                </Box>
                <Box sx={{ minWidth: 0 }}>
                  <Typography
                    sx={{
                      fontWeight: 700,
                      fontSize: 20,
                      lineHeight: 1.1,
                      fontVariantNumeric: "tabular-nums",
                      letterSpacing: "-0.03em",
                      fontFamily:
                        "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
                    }}
                  >
                    {steps.length}
                  </Typography>
                  <Typography
                    sx={{
                      mt: 0.35,
                      color: "text.secondary",
                      fontWeight: 750,
                      letterSpacing: 0.8,
                      textTransform: "uppercase",
                      fontSize: 11,
                      lineHeight: 1.2,
                    }}
                  >
                    Steps
                  </Typography>
                  <Typography
                    sx={{
                      mt: 0.15,
                      color: "text.disabled",
                      fontSize: 11,
                      fontWeight: 650,
                      letterSpacing: 0.4,
                      lineHeight: 1.2,
                    }}
                  >
                    {phaseLabel}
                  </Typography>
                </Box>
              </Box>
            </InstrumentTooltip>
          ) : (
            <Box
              sx={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                minWidth: 0,
              }}
            >
              <SegmentRing
                segments={segments}
                size={ringSize}
                centerLabel={isLive ? "Live" : isDone ? "Done" : "Idle"}
                centerValue={String(steps.length)}
                showLegend={false}
                help={{
                  ...INSTRUMENT_HELP.stageRing,
                  reading: `${steps.length} steps · ${runState}`,
                  details: [
                    {
                      label: "Active",
                      value: activeAction
                        ? TOOL_HELP[activeAction]?.short || activeAction
                        : "—",
                    },
                    {
                      label: "Complete arcs",
                      value: String(
                        segments.filter((s) => s.status === "complete").length,
                      ),
                    },
                    {
                      label: "Pending arcs",
                      value: String(
                        segments.filter((s) => s.status === "pending").length,
                      ),
                    },
                  ],
                }}
              />
              <Stack
                direction="row"
                spacing={0.5}
                useFlexGap
                flexWrap="wrap"
                justifyContent="center"
                sx={{ mt: 0.4, maxWidth: 140 }}
              >
                {segments.map((seg) => (
                  <InstrumentTooltip
                    key={seg.key}
                    help={seg.help}
                    placement="bottom"
                  >
                    <Typography
                      variant="caption"
                      sx={{
                        fontSize: 9,
                        fontWeight: seg.status === "active" ? 800 : 600,
                        color:
                          seg.status === "complete"
                            ? "success.main"
                            : seg.status === "active"
                              ? "warning.main"
                              : seg.status === "failed"
                                ? "error.main"
                                : "text.disabled",
                        letterSpacing: 0.3,
                        cursor: "help",
                        lineHeight: 1.2,
                      }}
                    >
                      {seg.label}
                    </Typography>
                  </InstrumentTooltip>
                ))}
              </Stack>
            </Box>
          )}
        </Box>
      </Box>

      {rail && (
        <Box sx={{ mt: 1.25 }}>
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: `repeat(${segments.length}, minmax(0, 1fr))`,
              gap: "3px",
            }}
          >
            {segments.map((seg) => (
              <InstrumentTooltip key={seg.key} help={seg.help} placement="top">
                <Box sx={{ minWidth: 0, cursor: "help" }}>
                  <Box
                    sx={{
                      height: 3,
                      bgcolor:
                        seg.status === "complete"
                          ? "success.main"
                          : seg.status === "active"
                            ? "warning.main"
                            : seg.status === "failed"
                              ? "error.main"
                              : "action.disabledBackground",
                    }}
                  />
                  <Typography
                    sx={{
                      mt: 0.45,
                      fontSize: 10,
                      fontWeight: 750,
                      letterSpacing: 0.7,
                      textAlign: "center",
                      color:
                        seg.status === "pending"
                          ? "text.disabled"
                          : "text.secondary",
                    }}
                    noWrap
                  >
                    {seg.label}
                  </Typography>
                </Box>
              </InstrumentTooltip>
            ))}
          </Box>
          <LinearProgress
            variant="determinate"
            value={isDone ? 100 : progress}
            sx={{
              mt: 1,
              height: 2,
              borderRadius: 0,
              bgcolor: dark ? "rgba(255,255,255,0.08)" : "rgba(15,23,42,0.08)",
              "& .MuiLinearProgress-bar": {
                borderRadius: 0,
                bgcolor: isError
                  ? "error.main"
                  : isDone
                    ? "success.main"
                    : "primary.main",
              },
            }}
          />
        </Box>
      )}
    </Box>
  );

  if (!framed) return body;

  return (
    <Paper
      component={motion.div}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      sx={{
        borderRadius: 2,
        border: "1px solid",
        borderColor: "divider",
        background: dark
          ? "linear-gradient(180deg, rgba(18,24,34,0.98) 0%, rgba(10,13,18,0.95) 100%)"
          : "linear-gradient(180deg, rgba(255,255,255,0.98) 0%, rgba(244,247,251,0.95) 100%)",
        position: "relative",
        overflow: "hidden",
        flexShrink: 0,
      }}
    >
      {body}
    </Paper>
  );
};

export default AgentInstrumentCluster;
