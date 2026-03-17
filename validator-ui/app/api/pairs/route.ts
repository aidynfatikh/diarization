import path from "node:path";
import fs from "node:fs/promises";
import type { NextRequest } from "next/server";

const PROJECT_ROOT = path.resolve(process.cwd(), "..");
const CLEAN_ROOT_GLOBAL = path.join(PROJECT_ROOT, "clean");
const TRANSCRIPTS_ROOT_GLOBAL = path.join(PROJECT_ROOT, "transcripts");

const CLEAN_ROOT_LOCAL = path.join(
  PROJECT_ROOT,
  "local_diarization",
  "clean",
);
const TRANSCRIPTS_ROOT_LOCAL = path.join(
  PROJECT_ROOT,
  "local_diarization",
  "transcripts",
);

export type Pair = {
  audioPath: string; // relative to public base (served via /api/audio)
  transcriptPath: string;
  transcriptText: string;
};

async function collectPairs(
  cleanRoot: string,
  transcriptsRoot: string,
): Promise<Pair[]> {
  const pairs: Pair[] = [];

  async function walk(dir: string) {
    const entries = await fs.readdir(dir, { withFileTypes: true });
    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        await walk(fullPath);
      } else if (entry.isFile()) {
        const ext = path.extname(entry.name).toLowerCase();
        if (![".mp3", ".wav", ".flac"].includes(ext)) continue;

        const rel = path.relative(cleanRoot, fullPath);
        const transcriptJson = path.join(
          transcriptsRoot,
          rel + ".json",
        );

        try {
          const buf = await fs.readFile(transcriptJson, "utf-8");
          const parsed = JSON.parse(buf);
          const text = parsed.text ?? "";
          pairs.push({
            audioPath: rel.replace(/\\/g, "/"),
            transcriptPath: path
              .relative(PROJECT_ROOT, transcriptJson)
              .replace(/\\/g, "/"),
            transcriptText: text,
          });
        } catch {
          // missing or invalid transcript, skip
        }
      }
    }
  }

  try {
    await walk(cleanRoot);
  } catch {
    // ignore if clean folder missing
  }

  return pairs;
}

export async function GET(req: NextRequest) {
  const url = new URL(req.url);
  const source = url.searchParams.get("source") || "global";

  const cleanRoot =
    source === "local" ? CLEAN_ROOT_LOCAL : CLEAN_ROOT_GLOBAL;
  const transcriptsRoot =
    source === "local" ? TRANSCRIPTS_ROOT_LOCAL : TRANSCRIPTS_ROOT_GLOBAL;

  const pairs = await collectPairs(cleanRoot, transcriptsRoot);
  return new Response(JSON.stringify({ pairs }), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

