"use client";

import { useEffect, useRef, useState } from "react";

type Pair = {
  audioPath: string;
  transcriptPath: string;
  transcriptText: string;
};

export default function Page() {
  const [pairs, setPairs] = useState<Pair[]>([]);
  const [index, setIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [marking, setMarking] = useState(false);
  const [badMap, setBadMap] = useState<Record<string, boolean>>({});
  const [maybeMap, setMaybeMap] = useState<Record<string, boolean>>({});
  const [mode, setMode] = useState<"global" | "local">("global");
  const [filter, setFilter] = useState<"all" | "marked" | "bad" | "maybe">(
    "all",
  );
  const [jumpInput, setJumpInput] = useState<string>("");
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    async function loadAll() {
      try {
        const [pairsRes, badRes] = await Promise.all([
          fetch(`/api/pairs?source=${mode}`),
          fetch("/api/mark-bad"),
        ]);
        const pairsData = await pairsRes.json();
        const badData = await badRes.json();
        setPairs(pairsData.pairs || []);
        const badMapped: Record<string, boolean> = {};
        const maybeMapped: Record<string, boolean> = {};
        Object.keys(badData || {}).forEach((k) => {
          const val = badData[k] as "bad" | "maybe" | undefined;
          if (!val) return;
          let keyMode: "global" | "local" = "global";
          let rel = k;
          const idx = k.indexOf(":");
          if (idx !== -1) {
            const m = k.slice(0, idx);
            if (m === "local" || m === "global") {
              keyMode = m;
              rel = k.slice(idx + 1);
            }
          }
          if (keyMode !== mode) return;
          if (val === "bad") badMapped[rel] = true;
          if (val === "maybe") maybeMapped[rel] = true;
        });
        setBadMap(badMapped);
        setMaybeMap(maybeMapped);
      } finally {
        setLoading(false);
      }
    }
    loadAll();
  }, [mode]);

  const current = pairs[index];

  // Autoplay whenever index (current pair) changes
  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.currentTime = 0;
      const p = audioRef.current.play();
      if (p && typeof p.catch === "function") {
        p.catch(() => {
          // ignore autoplay errors (browser policies)
        });
      }
    }
  }, [index, current?.audioPath]);

  // Keyboard shortcuts: Left/Right arrows for prev/next, Up arrow to toggle bad
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (!current) return;
      if (e.key === "ArrowLeft") {
        e.preventDefault();
        goPrev();
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        goNext();
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        toggleBad();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pairs.length, index, current?.audioPath, badMap, maybeMap]);

  async function toggleBad() {
    if (!current) return;
    setMarking(true);
    try {
      const res = await fetch("/api/mark-bad", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ audioPath: current.audioPath, mode }),
      });
      const data = await res.json().catch(() => ({}));
      const status = data.status as "bad" | "ok" | undefined;
      setBadMap((prev) => {
        const next = { ...prev };
        if (status === "bad") {
          next[current.audioPath] = true;
        } else if (status === "ok") {
          delete next[current.audioPath];
        }
        return next;
      });
      // Clear "maybe" if we just set "bad"
      if (status === "bad") {
        setMaybeMap((prev) => {
          const next = { ...prev };
          delete next[current.audioPath];
          return next;
        });
      }

      // If we just marked it as bad, move to next automatically
      if (status === "bad" && index < pairs.length - 1) {
        // move to next that matches current filter
        goNext();
      }
    } finally {
      setMarking(false);
    }
  }

  function matchesFilterForMode(
    path: string,
    mode: "all" | "marked" | "bad" | "maybe",
  ) {
    const isBad = !!badMap[path];
    const isMaybe = !!maybeMap[path];
    if (mode === "all") return true;
    if (mode === "bad") return isBad;
    if (mode === "maybe") return isMaybe;
    // marked
    return isBad || isMaybe;
  }

  function matchesFilterFor(path: string) {
    return matchesFilterForMode(path, filter);
  }

  function goPrev() {
    if (!pairs.length) return;
    for (let i = index - 1; i >= 0; i -= 1) {
      if (matchesFilterFor(pairs[i].audioPath)) {
        setIndex(i);
        return;
      }
    }
  }

  function goNext() {
    if (!pairs.length) return;
    for (let i = index + 1; i < pairs.length; i += 1) {
      if (matchesFilterFor(pairs[i].audioPath)) {
        setIndex(i);
        return;
      }
    }
  }

  async function toggleMaybe() {
    if (!current) return;
    setMarking(true);
    try {
      const res = await fetch("/api/mark-maybe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ audioPath: current.audioPath, mode }),
      });
      const data = await res.json().catch(() => ({}));
      const status = data.status as "maybe" | "ok" | undefined;
      setMaybeMap((prev) => {
        const next = { ...prev };
        if (status === "maybe") {
          next[current.audioPath] = true;
        } else if (status === "ok") {
          delete next[current.audioPath];
        }
        return next;
      });
      // Clear "bad" if we just set "maybe"
      if (status === "maybe") {
        setBadMap((prev) => {
          const next = { ...prev };
          delete next[current.audioPath];
          return next;
        });
      }
    } finally {
      setMarking(false);
    }
  }

  if (loading) {
    return <p>Loading...</p>;
  }

  if (!current) {
    return <p>No pairs found. Make sure clean/ and transcripts/ are populated.</p>;
  }

  const audioUrl = `/api/audio?path=${encodeURIComponent(current.audioPath)}&source=${mode}`;
  const isBad = !!badMap[current.audioPath];
  const isMaybe = !!maybeMap[current.audioPath];

  // Position within filtered set
  const filtered = pairs.filter((p) => matchesFilterFor(p.audioPath));
  const filteredIndex =
    filtered.findIndex((p) => p.audioPath === current.audioPath) + 1;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 16,
        borderRadius: 12,
        border: "1px solid #1f2937",
        padding: 16,
        background:
          "radial-gradient(circle at top left, rgba(56,189,248,0.1), transparent 55%), #020617",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: 8,
          flexWrap: "wrap",
        }}
      >
        <div>
          <div style={{ fontSize: 13, color: "#9ca3af" }}>File</div>
          <div style={{ fontSize: 14 }}>{current.audioPath}</div>
        </div>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            fontSize: 13,
            color: "#9ca3af",
          }}
        >
          <select
            value={mode}
            onChange={(e) => {
              const value = e.target.value as "global" | "local";
              setMode(value);
              setIndex(0);
            }}
            style={{
              backgroundColor: "#020617",
              borderRadius: 6,
              border: "1px solid #374151",
              color: "#e5e7eb",
              padding: "2px 6px",
              fontSize: 13,
            }}
          >
            <option value="global">Mode: clean/transcripts</option>
            <option value="local">Mode: local_diarization</option>
          </select>
          <span>
            {filteredIndex}/{filtered.length || 0}
          </span>
          <select
            value={filter}
            onChange={(e) => {
              const value = e.target.value as
                | "all"
                | "marked"
                | "bad"
                | "maybe";
              setFilter(value);
              // move to first matching item under new filter
              if (!pairs.length) return;
              if (matchesFilterForMode(current.audioPath, value)) return;
              for (let i = 0; i < pairs.length; i += 1) {
                if (matchesFilterForMode(pairs[i].audioPath, value)) {
                  setIndex(i);
                  break;
                }
              }
            }}
            style={{
              backgroundColor: "#020617",
              borderRadius: 6,
              border: "1px solid #374151",
              color: "#e5e7eb",
              padding: "2px 6px",
              fontSize: 13,
            }}
          >
            <option value="all">All</option>
            <option value="marked">Marked</option>
            <option value="bad">Bad only</option>
            <option value="maybe">Maybe only</option>
          </select>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 4,
            }}
          >
            <input
              type="number"
              min={1}
              max={filtered.length || 1}
              value={jumpInput}
              onChange={(e) => setJumpInput(e.target.value)}
              placeholder="#"
              style={{
                width: 52,
                backgroundColor: "#020617",
                borderRadius: 6,
                border: "1px solid #374151",
                color: "#e5e7eb",
                padding: "2px 6px",
                fontSize: 13,
              }}
            />
            <button
              type="button"
              onClick={() => {
                const n = parseInt(jumpInput, 10);
                if (!Number.isFinite(n)) return;
                if (n < 1 || n > filtered.length) return;
                const target = filtered[n - 1];
                const idx = pairs.findIndex(
                  (p) => p.audioPath === target.audioPath,
                );
                if (idx >= 0) {
                  setIndex(idx);
                }
              }}
              style={{
                padding: "2px 8px",
                borderRadius: 6,
                border: "1px solid #4b5563",
                backgroundColor: "#020617",
                color: "#e5e7eb",
                fontSize: 12,
                cursor: "pointer",
              }}
            >
              Go
            </button>
          </div>
        </div>
      </div>

      <div>
        <audio
          key={current.audioPath}
          ref={audioRef}
          controls
          src={audioUrl}
          style={{ width: "100%" }}
        />
      </div>

      <div
        style={{
          borderRadius: 8,
          border: "1px solid #1f2937",
          padding: 12,
          backgroundColor: "rgba(15,23,42,0.9)",
        }}
      >
        <div
          style={{
            fontSize: 13,
            color: "#9ca3af",
            marginBottom: 4,
          }}
        >
          Transcript
        </div>
        <div style={{ fontSize: 16, lineHeight: 1.5 }}>
          {current.transcriptText || <span style={{ color: "#6b7280" }}>—</span>}
        </div>
      </div>

      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          gap: 8,
          marginTop: 8,
        }}
      >
        <button
          onClick={goPrev}
          disabled={
            !pairs.length ||
            pairs.findIndex(
              (p, i) => i < index && matchesFilterFor(p.audioPath),
            ) === -1
          }
          style={{
            flex: 1,
            padding: "8px 0",
            borderRadius: 8,
            border: "1px solid #374151",
            backgroundColor: "#020617",
            color: "#e5e7eb",
            cursor: "pointer",
          }}
        >
          Prev
        </button>

        <button
          onClick={toggleMaybe}
          disabled={marking}
          style={{
            flex: 1.2,
            padding: "8px 0",
            borderRadius: 8,
            border: isMaybe ? "1px solid #eab308" : "1px solid #854d0e",
            background: isMaybe
              ? "linear-gradient(to right, #eab308, #ca8a04)"
              : "linear-gradient(to right, #facc15, #a16207)",
            color: "#111827",
            cursor: marking ? "default" : "pointer",
            fontWeight: 500,
          }}
        >
          {marking
            ? "Saving..."
            : isMaybe
            ? "Unmark Maybe"
            : "Mark Maybe"}
        </button>

        <button
          onClick={toggleBad}
          disabled={marking}
          style={{
            flex: 1.2,
            padding: "8px 0",
            borderRadius: 8,
            border: isBad ? "1px solid #22c55e" : "1px solid #7f1d1d",
            background: isBad
              ? "linear-gradient(to right, #22c55e, #15803d)"
              : "linear-gradient(to right, #b91c1c, #7f1d1d)",
            color: "#f9fafb",
            cursor: marking ? "default" : "pointer",
            fontWeight: 500,
          }}
        >
          {marking
            ? "Saving..."
            : isBad
            ? "Unmark Bad (↑)"
            : "Mark Bad (↑)"}
        </button>

        <button
          onClick={goNext}
          disabled={
            !pairs.length ||
            pairs.findIndex(
              (p, i) => i > index && matchesFilterFor(p.audioPath),
            ) === -1
          }
          style={{
            flex: 1,
            padding: "8px 0",
            borderRadius: 8,
            border: "1px solid #374151",
            backgroundColor: "#020617",
            color: "#e5e7eb",
            cursor: "pointer",
          }}
        >
          Next
        </button>
      </div>
    </div>
  );
}

