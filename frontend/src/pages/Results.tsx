import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";
import type { SubmissionSummary } from "../types";
import StatusBadge from "../components/StatusBadge";

export default function Results() {
  const [rows, setRows] = useState<SubmissionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  const load = async () => {
    setLoading(true);
    try {
      setRows(await api.listSubmissions());
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    load();
  }, []);

  const remove = async (id: number) => {
    if (!confirm("Delete this submission and its images?")) return;
    await api.deleteSubmission(id);
    load();
  };

  return (
    <div>
      <div className="mb-5 flex items-center justify-between">
        <h1 className="text-xl font-semibold">Results</h1>
        <div className="flex gap-2">
          <Link to="/setup" className="btn-ghost">
            + New Test
          </Link>
          <Link to="/upload" className="btn-primary">
            + Upload Student Work
          </Link>
        </div>
      </div>

      {loading ? (
        <p className="text-slate-400">Loading…</p>
      ) : rows.length === 0 ? (
        <div className="card text-center text-slate-500">
          <p className="mb-3">No submissions yet.</p>
          <Link to="/upload" className="btn-primary">
            Upload a student's work
          </Link>
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-slate-500">
              <tr>
                <th className="px-4 py-3">Student</th>
                <th className="px-4 py-3">Test</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Score</th>
                <th className="px-4 py-3">Date</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {rows.map((s) => (
                  <tr key={s.id} onClick={() => navigate(`/review/${s.id}`)} className="cursor-pointer hover:bg-slate-50 active:bg-slate-100">
                  <td className="px-4 py-3 font-medium">{s.student_name}</td>
                  <td className="px-4 py-3 text-slate-600">{s.test_title ?? `Test #${s.test_id}`}</td>
                  <td className="px-4 py-3">
                    <StatusBadge status={s.status} />
                  </td>
                  <td className="px-4 py-3">{s.final_score ?? "—"}</td>
                  <td className="px-4 py-3 text-slate-500">{new Date(s.created_at).toLocaleDateString()}</td>
                  <td className="px-4 py-3 text-right">
                    <button onClick={(e) => { e.stopPropagation(); navigate(`/review/${s.id}`); }} className="btn-ghost mr-2">
                    </button>
                    <button onClick={(e) => { e.stopPropagation(); remove(s.id); }} className="btn-danger">
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
