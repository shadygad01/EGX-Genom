// Live bridge to `agx_research.decision_service.DecisionService` -- the ONE
// route in this API that computes something on demand rather than reading a
// pre-produced JSON artifact (see artifactsStore.ts for every other route).
// That's deliberate, not an architectural drift: `decision_service` is
// designed to be stateless-per-call, queried on demand, and MUST NEVER be
// wired into a scheduled/autonomous run (CLAUDE.md), because it depends on
// `PositionState` -- an investor's own portfolio holdings, which this
// platform can never autonomously discover (see
// docs/ARCHITECTURE_ADVERSARIAL_REVIEW.md Section 1.10). An HTTP request
// firing this route on demand is the same "queried on demand" semantics as
// the `agx decide` CLI command it shells out to -- not a second one.
//
// No business logic lives here (CLAUDE.md's "api/ has no business logic of
// its own by design" invariant): this route only shapes the HTTP request
// into the exact `agx decide` CLI invocation and returns its stdout
// unmodified. All target-weight/action/risk/thesis computation happens in
// Python, in `research/`.
import type { FastifyInstance, FastifyReply } from "fastify";
import { execFile } from "node:child_process";
import { mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { promisify } from "node:util";
import type { PositionInput } from "../types.js";

const execFileAsync = promisify(execFile);
const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;
const TICKER = /^[A-Za-z0-9._-]{1,20}$/;

export interface DecisionsRouteOptions {
  // Directory a real `agx run`/`agx decide --data-dir <dir>` was already
  // pointed at -- decisions must be computed against the same collected
  // data the rest of the dashboard shows, never a guessed default. `null`
  // means genuinely unconfigured (see README's "Personalized decisions"
  // section) -- the route reports that honestly rather than silently
  // falling back to a directory that doesn't match the served dashboard.
  decisionDataDir: string | null;
  universeSeedDir: string;
  researchDir: string;
}

interface DecideRequestBody {
  date?: string;
  positions?: Record<string, PositionInput>;
}

function isValidPositionInput(value: unknown): value is PositionInput {
  if (typeof value !== "object" || value === null) return false;
  const p = value as Record<string, unknown>;
  if (typeof p.held !== "boolean") return false;
  if (p.current_weight !== undefined && typeof p.current_weight !== "number") return false;
  if (
    p.average_cost !== undefined &&
    p.average_cost !== null &&
    typeof p.average_cost !== "number"
  ) {
    return false;
  }
  return true;
}

export async function decisionsRoutes(
  app: FastifyInstance,
  opts: DecisionsRouteOptions
): Promise<void> {
  const { decisionDataDir, universeSeedDir, researchDir } = opts;

  app.post<{ Body: DecideRequestBody }>("/decisions", async (request, reply) => {
    if (!decisionDataDir) {
      reply.code(501);
      return {
        error:
          "Decision Center is not configured: set DECISION_DATA_DIR to the --data-dir a real " +
          "`agx run` was pointed at, then restart the API. See README's 'Personalized decisions' section.",
      };
    }

    const body = request.body ?? {};
    const date = body.date;
    if (typeof date !== "string" || !ISO_DATE.test(date)) {
      reply.code(400);
      return { error: "date is required, ISO format (e.g. 2026-06-14)." };
    }

    const positions = body.positions ?? {};
    for (const [ticker, position] of Object.entries(positions)) {
      if (!TICKER.test(ticker) || !isValidPositionInput(position)) {
        reply.code(400);
        return { error: `Invalid position entry for "${ticker}".` };
      }
    }

    return runCli(app, { researchDir, decisionDataDir, universeSeedDir }, "decide", date, positions, reply);
  });

  // Capital Allocation Intelligence: same live-bridge shape as /decisions
  // above (shells out to `agx allocate-capital`, which itself composes
  // `agx decide`'s own real evidence -- see
  // agx_research.cli.build_position_aware_decisions). Still no business
  // logic in this file: the ranking/opportunity-cost/recycling matching
  // happens entirely in research/, this route only shapes the request.
  app.post<{ Body: DecideRequestBody }>("/capital-allocation", async (request, reply) => {
    if (!decisionDataDir) {
      reply.code(501);
      return {
        error:
          "Capital Allocation is not configured: set DECISION_DATA_DIR to the --data-dir a real " +
          "`agx run` was pointed at, then restart the API. See README's 'Personalized decisions' section.",
      };
    }

    const body = request.body ?? {};
    const date = body.date;
    if (typeof date !== "string" || !ISO_DATE.test(date)) {
      reply.code(400);
      return { error: "date is required, ISO format (e.g. 2026-06-14)." };
    }

    const positions = body.positions ?? {};
    for (const [ticker, position] of Object.entries(positions)) {
      if (!TICKER.test(ticker) || !isValidPositionInput(position)) {
        reply.code(400);
        return { error: `Invalid position entry for "${ticker}".` };
      }
    }

    return runCli(
      app,
      { researchDir, decisionDataDir, universeSeedDir },
      "allocate-capital",
      date,
      positions,
      reply
    );
  });
}

async function runCli(
  app: FastifyInstance,
  opts: { researchDir: string; decisionDataDir: string; universeSeedDir: string },
  command: "decide" | "allocate-capital",
  date: string,
  positions: Record<string, PositionInput>,
  reply: FastifyReply
) {
  let tempDir: string | null = null;
  try {
    const args = [
      "run",
      "--project",
      opts.researchDir,
      "python",
      "-m",
      "agx_research.cli",
      "--data-dir",
      opts.decisionDataDir,
      "--universe-seed-dir",
      opts.universeSeedDir,
      command,
      "--date",
      date,
    ];

    if (Object.keys(positions).length > 0) {
      tempDir = await mkdtemp(path.join(tmpdir(), "agx-decide-"));
      const positionsFile = path.join(tempDir, "positions.json");
      await writeFile(positionsFile, JSON.stringify(positions), "utf-8");
      args.push("--positions", positionsFile);
    }

    const { stdout } = await execFileAsync("uv", args, {
      cwd: opts.researchDir,
      timeout: 60_000,
      maxBuffer: 10 * 1024 * 1024,
    });
    return JSON.parse(stdout);
  } catch (err) {
    app.log.error(err);
    reply.code(502);
    const stderr = err && typeof err === "object" && "stderr" in err ? String((err as { stderr: unknown }).stderr) : "";
    return {
      error: `${command === "decide" ? "Decision" : "Capital allocation"} computation failed.`,
      detail: stderr.slice(-2000) || undefined,
    };
  } finally {
    if (tempDir) await rm(tempDir, { recursive: true, force: true });
  }
}
