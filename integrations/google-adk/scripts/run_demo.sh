#!/usr/bin/env bash
# Two-user demo runner: mints 30-minute MCP tokens for both demo users (indoc
# env), runs the agent in the indoc-adk image, and writes DEMO_RESULTS.md.
#
#   integrations/google-adk/scripts/run_demo.sh local
#   integrations/google-adk/scripts/run_demo.sh deployed projects/P/locations/R/reasoningEngines/ID
set -euo pipefail

MODE="${1:?usage: run_demo.sh local|deployed [resource]}"
RESOURCE="${2:-}"
ROOT="$(git rev-parse --show-toplevel)"
ADK_DIR="$ROOT/integrations/google-adk"
ENV_FILE="$ADK_DIR/indoc_agent/.env"
ADC_FILE="$HOME/.config/gcloud/application_default_credentials.json"

[[ -f "$ENV_FILE" ]] || { echo "Missing $ENV_FILE (copy .env.example)" >&2; exit 1; }
[[ -f "$ADC_FILE" ]] || { echo "Run: gcloud auth application-default login" >&2; exit 1; }

TOKENS="$(mktemp -d)"
trap 'rm -rf "$TOKENS"' EXIT
chmod 700 "$TOKENS"
for user in manager analyst; do
  conda run -n indoc --cwd "$ROOT" python -m app.mcp_server.mint_token \
    --email "$user.demo@example.com" --ttl 30 --output "$TOKENS/$user" >/dev/null
done

PROJECT="$(sed -n 's/^GOOGLE_CLOUD_PROJECT=//p' "$ENV_FILE")"
DOCKER_ARGS=(
  --rm --user "$(id -u):$(id -g)"
  --env-file "$ENV_FILE"
  -e GOOGLE_APPLICATION_CREDENTIALS=/run/adc.json
  -e "GOOGLE_CLOUD_QUOTA_PROJECT=$PROJECT"
  -e INDOC_MANAGER_TOKEN_FILE=/run/tokens/manager
  -e INDOC_ANALYST_TOKEN_FILE=/run/tokens/analyst
  -v "$ADC_FILE:/run/adc.json:ro"
  -v "$TOKENS:/run/tokens:ro"
  -v "$ADK_DIR:/workspace/out"
)
if [[ "$MODE" == "local" ]]; then
  # Local runs reach the MCP server on the compose network unless overridden.
  DOCKER_ARGS+=(--network indoc_default -e "INDOC_MCP_URL=${INDOC_MCP_URL_LOCAL:-http://indoc-mcp:8010/mcp}")
fi

docker run "${DOCKER_ARGS[@]}" indoc-adk \
  python scripts/demo_two_users.py --mode "$MODE" ${RESOURCE:+--resource "$RESOURCE"} \
  --output out/DEMO_RESULTS.md
