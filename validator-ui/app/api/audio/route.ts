import path from "node:path";
import fs from "node:fs/promises";
import { NextRequest } from "next/server";

const PROJECT_ROOT = path.resolve(process.cwd(), "..");
const CLEAN_ROOT_GLOBAL = path.join(PROJECT_ROOT, "clean");
const CLEAN_ROOT_LOCAL = path.join(
  PROJECT_ROOT,
  "local_diarization",
  "clean",
);

export async function GET(req: NextRequest) {
  const url = new URL(req.url);
  const rel = url.searchParams.get("path");
  const source = url.searchParams.get("source") || "global";

  if (!rel) {
    return new Response("Missing path", { status: 400 });
  }

  const root = source === "local" ? CLEAN_ROOT_LOCAL : CLEAN_ROOT_GLOBAL;

  const safeRel = rel.replace(/\\/g, "/");
  const fullPath = path.join(root, safeRel);

  try {
    const data = await fs.readFile(fullPath);
    const ext = path.extname(fullPath).toLowerCase();
    const type =
      ext === ".wav"
        ? "audio/wav"
        : ext === ".flac"
        ? "audio/flac"
        : "audio/mpeg";

    return new Response(data, {
      status: 200,
      headers: { "Content-Type": type },
    });
  } catch {
    return new Response("Not found", { status: 404 });
  }
}
