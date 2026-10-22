import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import type { Test } from "../types";

interface Page {
  file: File;
  url: string;
}

export default function Upload() {
  const navigate = useNavigate();
  const [tests, setTests] = useState<Test[]>([]);
  const [testId, setTestId] = useState<number | "">("");
  const [studentName, setStudentName] = useState("");
  const [pages, setPages] = useState<Page[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");

  useEffect(() => {
    api.listTests().then((t) => {
      setTests(t);
      if (t.length) setTestId(t[0].id);
    });
  }, []);

  const addFiles = (files: FileList | null) => {
    if (!files) return;
    const added = Array.from(files).map((file) => ({ file, url: URL.createObjectURL(file) }));
    setPages((p) => [...p, ...added]);
  };

  const removePage = (i: number) => {
    setPages((p) => {
      URL.revokeObjectURL(p[i].url);
      return p.filter((_, idx) => idx !== i);
    });
  };

  const move = (i: number, dir: -1 | 1) => {
    setPages((p) => {
      const j = i + dir;
      if (j < 0 || j >= p.length) return p;
      const copy = [...p];
      [copy[i], copy[j]] = [copy[j], copy[i]];
      return copy;
    });
  };

  const submit = async () => {
    setError("");
    if (!testId) return setError("Select a test.");
    if (!studentName.trim()) return setError("Enter the student's name.");
    if (pages.length === 0) return setError("Add at least one page image.");
    try {
      setBusy("Uploading pages…");
      const sub = await api.createSubmission(studentName.trim(), Number(testId), pages.map((p) => p.file));
      setBusy("Analyzing handwriting with AI… this can take 20–60 seconds.");
      try {
        await api.analyze(sub.id);
      } catch (err) {
        // Upload succeeded; analysis failed. Send teacher to review so they can retry.
        setError(`Uploaded, but analysis failed: ${(err as Error).message}`);
        navigate(`/review/${sub.id}`);
        return;
      }
      navigate(`/review/${sub.id}`);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy("");
    }
  };

  return (
    <div className="mx-auto max-w-2xl space-y-5">
      <h1 className="text-xl font-semibold">Upload Student Work</h1>

      {tests.length === 0 ? (
        <div className="card text-center text-slate-500">
          You need a test first.{" "}
          <button className="text-brand-600 hover:underline" onClick={() => navigate("/setup")}>
            Create one
          </button>
          .
        </div>
      ) : (
        <>
          <div className="card space-y-4">
            <div>
              <label className="label">Test</label>
              <select className="input" value={testId} onChange={(e) => setTestId(Number(e.target.value))}>
                {tests.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.title} ({t.test_type})
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">Student name</label>
              <input className="input" value={studentName} onChange={(e) => setStudentName(e.target.value)} />
            </div>
            <div>
              <label className="label">Pages (photos of the handwritten work)</label>
              <div className="flex flex-wrap gap-2">
                <label className="btn-ghost cursor-pointer">
                  📷 Take photo
                  <input
                    type="file"
                    accept="image/*"
                    capture="environment"
                    className="hidden"
                    onChange={(e) => {
                      addFiles(e.target.files);
                      e.target.value = "";
                    }}
                  />
                </label>
                <label className="btn-ghost cursor-pointer">
                  🖼️ Choose from device
                  <input
                    type="file"
                    accept="image/*"
                    multiple
                    className="hidden"
                    onChange={(e) => {
                      addFiles(e.target.files);
                      e.target.value = "";
                    }}
                  />
                </label>
              </div>
              <p className="mt-1 text-xs text-slate-400">
                Add every page in order. <strong>Take photo</strong> opens the camera (one page at a
                time); <strong>Choose from device</strong> attaches existing pictures (select multiple
                at once). Multi-page writing is supported.
              </p>
            </div>
          </div>

          {pages.length > 0 && (
            <div className="card">
              <h2 className="mb-3 font-medium">Pages ({pages.length})</h2>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                {pages.map((p, i) => (
                  <div key={p.url} className="relative rounded-lg border border-slate-200 p-2">
                    <img src={p.url} alt={`page ${i + 1}`} className="h-40 w-full rounded object-cover" />
                    <div className="mt-2 flex items-center justify-between text-xs">
                      <span className="font-medium text-slate-500">Page {i + 1}</span>
                      <div className="flex gap-1">
                        <button onClick={() => move(i, -1)} disabled={i === 0} className="btn-ghost px-2 py-1">
                          ↑
                        </button>
                        <button
                          onClick={() => move(i, 1)}
                          disabled={i === pages.length - 1}
                          className="btn-ghost px-2 py-1"
                        >
                          ↓
                        </button>
                        <button onClick={() => removePage(i)} className="btn-danger px-2 py-1">
                          ✕
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {error && <p className="text-sm text-red-600">{error}</p>}
          {busy && <p className="text-sm text-brand-600">{busy}</p>}

          <div className="flex justify-end">
            <button onClick={submit} className="btn-primary" disabled={!!busy}>
              {busy ? "Working…" : "Upload & Analyze"}
            </button>
          </div>
        </>
      )}
    </div>
  );
}
