import type { RubricItem, Submission, SubmissionSummary, Test } from "./types";

const JSON_HEADERS = { "Content-Type": "application/json" };

async function handle(res: Response) {
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const j = await res.json();
      if (j && j.detail) detail = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail);
    } catch {
      /* ignore */
    }
    const err = new Error(detail) as Error & { status?: number };
    err.status = res.status;
    throw err;
  }
  const ct = res.headers.get("content-type") || "";
  return ct.includes("application/json") ? res.json() : res.text();
}

const get = (url: string) => fetch(url, { credentials: "include" }).then(handle);
const post = (url: string, body?: unknown) =>
  fetch(url, {
    method: "POST",
    credentials: "include",
    headers: body === undefined ? undefined : JSON_HEADERS,
    body: body === undefined ? undefined : JSON.stringify(body),
  }).then(handle);
const patch = (url: string, body: unknown) =>
  fetch(url, { method: "PATCH", credentials: "include", headers: JSON_HEADERS, body: JSON.stringify(body) }).then(handle);

export const api = {
  me: (): Promise<{ authenticated: boolean; ai_configured: boolean }> => get("/api/me"),
  login: (password: string) => post("/api/login", { password }),
  logout: () => post("/api/logout"),

  listTests: (): Promise<Test[]> => get("/api/tests"),
  getTest: (id: number): Promise<Test> => get(`/api/tests/${id}`),
  createTest: (body: unknown): Promise<Test> => post("/api/tests", body),
  deleteTest: (id: number) => fetch(`/api/tests/${id}`, { method: "DELETE", credentials: "include" }).then(handle),
  defaultWritingRubric: (maxPoints: number): Promise<RubricItem[]> =>
    get(`/api/tests/defaults/writing-rubric?max_points=${maxPoints}`),
  uploadTestImage: (id: number, file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return fetch(`/api/tests/${id}/image`, { method: "POST", credentials: "include", body: fd }).then(handle);
  },

  createSubmission: (studentName: string, testId: number, files: File[]): Promise<Submission> => {
    const fd = new FormData();
    fd.append("student_name", studentName);
    fd.append("test_id", String(testId));
    files.forEach((f) => fd.append("files", f));
    return fetch("/api/submissions", { method: "POST", credentials: "include", body: fd }).then(handle);
  },
  analyze: (id: number): Promise<Submission> => post(`/api/submissions/${id}/analyze`),
  reevaluate: (id: number, correctedTranscription?: string): Promise<Submission> =>
    post(`/api/submissions/${id}/reevaluate`, { corrected_transcription: correctedTranscription }),
  saveReview: (id: number, body: unknown): Promise<Submission> => patch(`/api/submissions/${id}/review`, body),
  listSubmissions: (): Promise<SubmissionSummary[]> => get("/api/submissions"),
  getSubmission: (id: number): Promise<Submission> => get(`/api/submissions/${id}`),
  deleteSubmission: (id: number) =>
    fetch(`/api/submissions/${id}`, { method: "DELETE", credentials: "include" }).then(handle),
};

export const pageImageUrl = (submissionId: number, index: number) =>
  `/api/submissions/${submissionId}/pages/${index}`;
