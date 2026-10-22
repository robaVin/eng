import { FormEvent, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import type { RubricItem, TestType } from "../types";

const TYPES: { value: TestType; label: string }[] = [
  { value: "writing", label: "Writing" },
  { value: "grammar", label: "Grammar" },
  { value: "vocabulary", label: "Vocabulary" },
  { value: "reading", label: "Reading" },
];

export default function TestSetup() {
  const navigate = useNavigate();
  const [title, setTitle] = useState("The Mysterious Letter");
  const [testType, setTestType] = useState<TestType>("writing");
  const [instructions, setInstructions] = useState(
    "Continue the story in 150–180 words, making your story creative, logical, and detailed, with correct grammar and punctuation."
  );
  const [maxPoints, setMaxPoints] = useState(10);
  const [criteria, setCriteria] = useState("");
  const [expectedAnswer, setExpectedAnswer] = useState("");
  const [wordMin, setWordMin] = useState<number | "">(150);
  const [wordMax, setWordMax] = useState<number | "">(180);
  const [rubric, setRubric] = useState<RubricItem[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [imageFile, setImageFile] = useState<File | null>(null);

  // Load default writing rubric when writing + maxPoints change (and rubric empty)
  useEffect(() => {
    if (testType !== "writing") return;
    api.defaultWritingRubric(maxPoints).then(setRubric).catch(() => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [testType]);

  const rubricTotal = useMemo(() => rubric.reduce((s, r) => s + (Number(r.points) || 0), 0), [rubric]);
  const rubricOk = Math.abs(rubricTotal - maxPoints) < 0.01;

  const setRubricPoints = (i: number, pts: number) =>
    setRubric((r) => r.map((item, idx) => (idx === i ? { ...item, points: pts } : item)));
  const setRubricName = (i: number, name: string) =>
    setRubric((r) => r.map((item, idx) => (idx === i ? { ...item, name } : item)));
  const addRubricRow = () => setRubric((r) => [...r, { name: "", points: 0 }]);
  const removeRubricRow = (i: number) => setRubric((r) => r.filter((_, idx) => idx !== i));
  const resetDefaultRubric = () => api.defaultWritingRubric(maxPoints).then(setRubric);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    if (testType === "writing" && !rubricOk) {
      setError(`Rubric points (${rubricTotal}) must total the maximum points (${maxPoints}).`);
      return;
    }
    setBusy(true);
    try {
      const body: Record<string, unknown> = {
        title,
        test_type: testType,
        instructions,
        max_points: maxPoints,
        criteria,
        expected_answer: testType === "writing" ? null : expectedAnswer || null,
        word_min: testType === "writing" && wordMin !== "" ? wordMin : null,
        word_max: testType === "writing" && wordMax !== "" ? wordMax : null,
        rubric: testType === "writing" ? rubric : undefined,
      };
      const test = await api.createTest(body);
      if (imageFile) {
        try {
          await api.uploadTestImage(test.id, imageFile);
        } catch {
          /* non-fatal */
        }
      }
      navigate("/upload");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} className="mx-auto max-w-2xl space-y-5">
      <h1 className="text-xl font-semibold">Test Setup</h1>

      <div className="card space-y-4">
        <div>
          <label className="label">Test title</label>
          <input className="input" value={title} onChange={(e) => setTitle(e.target.value)} required />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="label">Type</label>
            <select className="input" value={testType} onChange={(e) => setTestType(e.target.value as TestType)}>
              {TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Maximum points</label>
            <input
              type="number"
              min={1}
              step="0.5"
              className="input"
              value={maxPoints}
              onChange={(e) => setMaxPoints(Number(e.target.value))}
            />
          </div>
        </div>

        <div>
          <label className="label">Instructions / question text</label>
          <textarea
            className="input min-h-[90px]"
            value={instructions}
            onChange={(e) => setInstructions(e.target.value)}
          />
        </div>

        <div>
          <label className="label">Grading criteria (notes for the AI & yourself)</label>
          <textarea className="input min-h-[60px]" value={criteria} onChange={(e) => setCriteria(e.target.value)} />
        </div>

        {testType !== "writing" && (
          <div>
            <label className="label">Expected answer (optional, for short-answer)</label>
            <textarea
              className="input min-h-[60px]"
              value={expectedAnswer}
              onChange={(e) => setExpectedAnswer(e.target.value)}
            />
          </div>
        )}

        {testType === "writing" && (
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label">Word count — min</label>
              <input
                type="number"
                className="input"
                value={wordMin}
                onChange={(e) => setWordMin(e.target.value === "" ? "" : Number(e.target.value))}
              />
            </div>
            <div>
              <label className="label">Word count — max</label>
              <input
                type="number"
                className="input"
                value={wordMax}
                onChange={(e) => setWordMax(e.target.value === "" ? "" : Number(e.target.value))}
              />
            </div>
          </div>
        )}

        <div>
          <label className="label">Original blank test image (optional)</label>
          <input
            type="file"
            accept="image/*"
            className="text-sm"
            onChange={(e) => setImageFile(e.target.files?.[0] ?? null)}
          />
        </div>
      </div>

      {testType === "writing" && (
        <div className="card">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="font-medium">Rubric</h2>
            <button type="button" onClick={resetDefaultRubric} className="text-sm text-brand-600 hover:underline">
              Reset to defaults
            </button>
          </div>
          <div className="space-y-2">
            {rubric.map((item, i) => (
              <div key={i} className="flex items-center gap-2">
                <input
                  className="input flex-1"
                  value={item.name}
                  placeholder="Criterion name"
                  onChange={(e) => setRubricName(i, e.target.value)}
                />
                <input
                  type="number"
                  step="0.5"
                  min={0}
                  className="input w-24"
                  value={item.points}
                  onChange={(e) => setRubricPoints(i, Number(e.target.value))}
                />
                <button type="button" onClick={() => removeRubricRow(i)} className="btn-danger px-2">
                  ✕
                </button>
              </div>
            ))}
          </div>
          <div className="mt-3 flex items-center justify-between text-sm">
            <button type="button" onClick={addRubricRow} className="text-brand-600 hover:underline">
              + Add criterion
            </button>
            <span className={rubricOk ? "text-green-600" : "text-red-600"}>
              Total: {rubricTotal} / {maxPoints}
            </span>
          </div>
        </div>
      )}

      {error && <p className="text-sm text-red-600">{error}</p>}
      <div className="flex justify-end gap-2">
        <button type="button" onClick={() => navigate("/")} className="btn-ghost">
          Cancel
        </button>
        <button type="submit" className="btn-primary" disabled={busy}>
          {busy ? "Saving…" : "Save test & continue"}
        </button>
      </div>
    </form>
  );
}
