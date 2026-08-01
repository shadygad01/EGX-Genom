import path from "node:path";
import { fileURLToPath } from "node:url";
import { buildApp } from "./app.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const researchData = path.resolve(__dirname, "../../research/data");

const port = Number(process.env.PORT ?? 3001);

const app = buildApp({
  knowledgeStorePath:
    process.env.KNOWLEDGE_STORE_PATH ?? path.join(researchData, "knowledge_store.example.json"),
  eventsStorePath: process.env.EVENTS_STORE_PATH ?? path.join(researchData, "events.json"),
  runsStorePath: process.env.RUNS_STORE_PATH ?? path.join(researchData, "runs.json"),
  // Written by `agx_research.cli export-dashboard`; in production this
  // directory is refreshed on a schedule (System 18 -- deployment/scheduling
  // is business-blocked, see docs/ROADMAP.md) alongside the static site build.
  artifactsDir: process.env.DASHBOARD_ARTIFACTS_DIR ?? path.join(researchData, "dashboard"),
  // No default: must be the exact `--data-dir` a real `agx run`/`agx decide`
  // was pointed at, or Decision Center honestly reports itself unconfigured
  // rather than risk decisions that disagree with the rest of the dashboard.
  decisionDataDir: process.env.DECISION_DATA_DIR ?? null,
  universeSeedDir: process.env.UNIVERSE_SEED_DIR ?? path.join(researchData, "universe"),
  researchDir: path.resolve(__dirname, "../../research"),
});

app
  .listen({ port, host: "0.0.0.0" })
  .catch((err) => {
    app.log.error(err);
    process.exit(1);
  });
