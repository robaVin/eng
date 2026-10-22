import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, pageImageUrl } from "../api";
import type { Submission, Test, WritingIssue } from "../types";
import StatusBadge from "../components/StatusBadge";

const WORD_RE = /[A-Za-z0-9]+(?:['’\-][A-Za-z0-9]+)*/g;
const countWords = (t: string) => (t.match(WORD_RE) || []).length;

export default function Review({ aiConfigured }: { aiConfigured: boolean }) {
  const { id } = useParams();
  const subId = Number(id);
  const navigate = useNavigate();

  const [sub, setSub] = useState<Submission | null>(null);
  const [test, setTest] = useState<Test | null>(null);
  const [text, setText] = useState("");
  const [scores, setScores] = useState<Record<string, number>>({});
  const [comments, setComments] = useState("");
  const [finalEdited, setFinalEdited] = useState(false);
  const [finalScore, setFinalScore] = useState(0);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const hydrate = useCallback((s: Submission) => {
    setSub(s);
    setText(s.corrected_transcription ?? s.original_transcription ?? "");
    setScores(s.approved_scores ?? {});
    setComments(s.teacher_comments ?? "");
    setFinalEdited(false);
    setFinalScore(s.final_score ?? 0);
  }, []);

  useEffect(() => {
    api.getSubmission(subId).then((s) => {
      hydrate(s);
      api.getTest(s.test_id).then(setTest);
    });
  }, [subId, hydrate]);

  const computedTotal = useMemo(() => {
    if (!test) return 0;
    const caps: Record<string, number> = {};
    test.rubric.forEach((r) => (caps[r.name] = r.points));
    let total = 0;
    for (const [name, v] of Object.entries(scores)) {
      let val = Math.max(0, Number(v) || 0);
      if (caps[name] !== undefined) val = Math.min(val, caps[name]);
      total += val;
    }
    return Math.round(Math.max(0, Math.min(total, test.max_points)) * 100) / 100;
  }, [scores, test]);

  useEffect(() => {
    if (!finalEdited) setFinalScore(computedTotal);
  }, [computedTotal, finalEdited]);

  const liveWordCount = useMemo(() => countWords(text), [text]);

  const runAnalyze = async () => {
    setError("");
    setBusy("Analyzing handwriting… 20–60s.");
    try {
      hydrate(await api.analyze(subId));
      setNotice("Analysis complete.");
    } catch (err) {
      setError((err as Error).message);
      api.getSubmission(subId).then(setSub);
    } finally {
      setBusy("");
    }
  };

  const reevaluate = async () => {
    setError("");
    setBusy("Re-evaluating the corrected text…");
    try {
      hydrate(await api.reevaluate(subId, text));
      setNotice("Re-evaluated against your corrected transcription.");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy("");
    }
  };

  const save = async (approve: boolean) => {
    setError("");
    setBusy(approve ? "Saving & approving…" : "Saving…");
    try {
      const s = await api.saveReview(subId, {
        corrected_transcription: text,
        approved_scores: scores,
        teacher_comments: comments,
        final_score: finalEdited ? finalScore : null,
      });
      hydrate(s);
      setNotice(approve ? "Saved and approved." : "Saved.");
      if (approve) navigate("/");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy("");
    }
  };

  if (!sub) return <p className="text-slate-400">Loading…</p>;

  // Show the review editor once there's any transcription — including a manual one typed
  // when AI is unavailable, not only an AI-produced original.
  const analyzed = !!(sub.original_transcription || sub.corrected_transcription);
  const meta = sub.transcription_meta;
  const ev = sub.evaluation;
  const issuesByType = (ev?.issues ?? []).reduce<Record<string, WritingIssue[]>>((acc, iss) => {
    (acc[iss.type] ??= []).push(iss);
    return acc;
  }, {});

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate("/")} className="btn-ghost">
            ← Back
          </button>
          <h1 className="text-xl font-semibold">{sub.student_name}</h1>
          <StatusBadge status={sub.status} />
        </div>
        <span className="text-sm text-slate-500">{test?.title}</span>
      </div>

      {sub.status === "error" && sub.error_message && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          Processing error: {sub.error_message}
        </div>
      )}
      {error && <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
      {notice && <div className="mb-4 rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700">{notice}</div>}

      <div className="grid gap-5 lg:grid-cols-2">
        {/* LEFT: original pages */}
        <div className="space-y-4">
          <div className="card">
            <h2 className="mb-3 font-medium">Original pages ({sub.image_paths.length})</h2>
            <div className="space-y-3">
              {sub.image_paths.map((_, i) => (
                <a key={i} href={pageImageUrl(sub.id, i)} target="_blank" rel="noreferrer" className="block">
                  <img
                    src={pageImageUrl(sub.id, i)}
                    alt={`Page ${i + 1}`}
                    className="w-full rounded-lg border border-slate-200 hover:opacity-90"
                  />
                  <span className="mt-1 block text-center text-xs text-slate-400">Page {i + 1} — click to enlarge</span>
                </a>
              ))}
            </div>
          </div>

          {meta && (meta.uncertain_passages?.length || meta.crossed_out_notes?.length) ? (
            <div className="card space-y-3 text-sm">
              {!!meta.uncertain_passages?.length && (
                <div>
                  <h3 className="mb-1 font-medium text-amber-700">⚠ Uncertain passages</h3>
                  <ul className="list-inside list-disc text-slate-600">
                    {meta.uncertain_passages.map((u, i) => (
                      <li key={i}>{u}</li>
                    ))}
                  </ul>
                </div>
              )}
              {!!meta.crossed_out_notes?.length && (
                <div>
                  <h3 className="mb-1 font-medium text-slate-500">Crossed-out (excluded)</h3>
                  <ul className="list-inside list-disc text-slate-500">
                    {meta.crossed_out_notes.map((u, i) => (
                      <li key={i}>{u}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : null}
        </div>

        {/* RIGHT: transcription + evaluation */}
        <div className="space-y-4">
          {!analyzed ? (
            <div className="card text-center">
              <p className="mb-3 text-slate-600">This submission hasn't been analyzed yet.</p>
              {!aiConfigured && (
                <p className="mb-3 text-sm text-amber-700">
                  No AI key is configured on the server — set ANTHROPIC_API_KEY to enable analysis.
                </p>
              )}
              <button onClick={runAnalyze} className="btn-primary" disabled={!!busy}>
                {busy || "Analyze now"}
              </button>
            </div>
          ) : (
            <>
              <div className="card">
                <div className="mb-2 flex items-center justify-between">
                  <h2 className="font-medium">Transcription (editable)</h2>
                  <span
                    className={`text-sm ${
                      test && (test.word_min || test.word_max)
                        ? liveWordCount < (test.word_min ?? 0) || (test.word_max && liveWordCount > test.word_max)
                          ? "text-amber-600"
                          : "text-green-600"
                        : "text-slate-500"
                    }`}
                  >
                    {liveWordCount} words
                    {test && (test.word_min || test.word_max) ? ` (target ${test.word_min ?? "?"}–${test.word_max ?? "?"})` : ""}
                  </span>
                </div>
                <textarea className="input min-h-[220px] font-mono text-sm" value={text} onChange={(e) => setText(e.target.value)} />
                <div className="mt-3 flex flex-wrap gap-2">
                  <button onClick={reevaluate} className="btn-ghost" disabled={!!busy}>
                    Re-evaluate corrected text
                  </button>
                  <button onClick={() => save(false)} className="btn-ghost" disabled={!!busy}>
                    Save transcription
                  </button>
                </div>
                <p className="mt-2 text-xs text-slate-400">
                  Transcription preserves the student's original spelling/grammar. Edit mistakes the AI made, then
                  re-evaluate — no need to re-upload photos.
                </p>
              </div>

              {ev?.notes?.length ? (
                <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                  {ev.notes.map((n, i) => (
                    <p key={i}>⚠ {n}</p>
                  ))}
                </div>
              ) : null}

              {/* Rubric scores */}
              <div className="card">
                <h2 className="mb-3 font-medium">Rubric scores</h2>
                <div className="space-y-3">
                  {test?.rubric.map((r) => {
                    const sugg = ev?.rubric_scores?.find((x) => x.criterion === r.name);
                    return (
                      <div key={r.name} className="border-b border-slate-100 pb-3 last:border-0">
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-sm font-medium">{r.name}</span>
                          <div className="flex items-center gap-1 text-sm">
                            <input
                              type="number"
                              step="0.5"
                              min={0}
                              max={r.points}
                              className="input w-20 py-1"
                              value={scores[r.name] ?? 0}
                              onChange={(e) => setScores((s) => ({ ...s, [r.name]: Number(e.target.value) }))}
                            />
                            <span className="text-slate-400">/ {r.points}</span>
                          </div>
                        </div>
                        {sugg && (
                          <p className="mt-1 text-xs text-slate-500">
                            AI suggested <strong>{sugg.suggested_points}</strong>: {sugg.explanation}
                          </p>
                        )}
                      </div>
                    );
                  })}
                </div>
                <div className="mt-4 flex items-center justify-between border-t border-slate-200 pt-3">
                  <span className="font-medium">Final score</span>
                  <div className="flex items-center gap-2">
                    <input
                      type="number"
                      step="0.5"
                      min={0}
                      max={test?.max_points}
                      className="input w-24"
                      value={finalScore}
                      onChange={(e) => {
                        setFinalEdited(true);
                        setFinalScore(Number(e.target.value));
                      }}
                    />
                    <span className="text-slate-400">/ {test?.max_points}</span>
                    {finalEdited && (
                      <button
                        onClick={() => {
                          setFinalEdited(false);
                          setFinalScore(computedTotal);
                        }}
                        className="text-xs text-brand-600 hover:underline"
                        title="Recalculate from rubric"
                      >
                        auto ({computedTotal})
                      </button>
                    )}
                  </div>
                </div>
              </div>

              {/* Issues */}
              {ev && (Object.keys(issuesByType).length > 0 || ev.overall_feedback) && (
                <div className="card space-y-4">
                  <h2 className="font-medium">Language issues & feedback</h2>
                  {Object.entries(issuesByType).map(([type, items]) => (
                    <div key={type}>
                      <h3 className="mb-1 text-sm font-semibold capitalize text-slate-600">{type}</h3>
                      <ul className="space-y-2">
                        {items.map((iss, i) => (
                          <li key={i} className="rounded-lg bg-slate-50 p-2 text-sm">
                            <span className="text-red-600 line-through">{iss.original}</span>{" "}
                            <span className="text-slate-400">→</span>{" "}
                            <span className="text-green-700">{iss.correction}</span>
                            {iss.explanation && <p className="mt-0.5 text-xs text-slate-500">{iss.explanation}</p>}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))}
                  {ev.overall_feedback && (
                    <div>
                      <h3 className="mb-1 text-sm font-semibold text-slate-600">Overall feedback</h3>
                      <p className="text-sm text-slate-600">{ev.overall_feedback}</p>
                    </div>
                  )}
                </div>
              )}

              {/* Teacher comments + approve */}
              <div className="card">
                <label className="label">Teacher comments</label>
                <textarea
                  className="input min-h-[70px]"
                  value={comments}
                  onChange={(e) => setComments(e.target.value)}
                  placeholder="Optional notes for this student…"
                />
                <div className="mt-3 flex justify-end gap-2">
                  <button onClick={() => save(false)} className="btn-ghost" disabled={!!busy}>
                    Save
                  </button>
                  <button onClick={() => save(true)} className="btn-primary" disabled={!!busy}>
                    {busy || "Approve & Save"}
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
