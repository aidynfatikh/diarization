import path from "node:path";
import fs from "node:fs/promises";
import { NextRequest } from "next/server";

const PROJECT_ROOT = path.resolve(process.cwd(), "..");
const RESULTS_PATH = path.join(PROJECT_ROOT, "validation_results.json");

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => null);
  if (!body || typeof body.audioPath !== "string") {
    return new Response("Invalid body", { status: 400 });
  }

  const mode = body.mode === "local" ? "local" : "global";
  const key = `${mode}:${body.audioPath}`;

  let current: Record<string, "bad" | "maybe"> = {};
  try {
    const buf = await fs.readFile(RESULTS_PATH, "utf-8");
    current = JSON.parse(buf);
  } catch {
    // ignore if file missing
  }

  const alreadyMaybe = current[key] === "maybe";

  if (alreadyMaybe) {
    delete current[key];
  } else {
    current[key] = "maybe";
  }

  await fs.writeFile(RESULTS_PATH, JSON.stringify(current, null, 2), "utf-8");

  return new Response(
    JSON.stringify({ status: alreadyMaybe ? "ok" : "maybe" }),
    {
      status: 200,
      headers: { "Content-Type": "application/json" },
    },
  );
}

