export type TestType = "grammar" | "vocabulary" | "reading" | "writing";

export interface RubricItem {
  name: string;
  points: number;
}

export interface Test {
  id: number;
  title: string;
  test_type: TestType;
  instructions: string;
  max_points: number;
  criteria: string;
  expected_answer: string | null;
  rubric: RubricItem[];
  word_min: number | null;
  word_max: number | null;
  has_test_image: boolean;
  created_at: string;
}

export interface WritingIssue {
  type: string;
  original: string;
  correction: string;
  explanation: string;
}

export interface RubricScoreSuggestion {
  criterion: string;
  max_points: number;
  suggested_points: number;
  explanation: string;
}

export interface Evaluation {
  issues: WritingIssue[];
  rubric_scores: RubricScoreSuggestion[];
  overall_feedback: string;
  notes: string[];
}

export interface TranscriptionMeta {
  uncertain_passages?: string[];
  crossed_out_notes?: string[];
  pages?: { page: number; summary: string }[];
  usage?: Record<string, unknown>;
}

export interface Submission {
  id: number;
  student_name: string;
  test_id: number;
  status: string;
  error_message: string | null;
  image_paths: string[];
  original_transcription: string | null;
  corrected_transcription: string | null;
  word_count: number | null;
  transcription_meta: TranscriptionMeta | null;
  evaluation: Evaluation | null;
  approved_scores: Record<string, number> | null;
  final_score: number | null;
  teacher_comments: string | null;
  created_at: string;
  updated_at: string;
}

export interface SubmissionSummary {
  id: number;
  student_name: string;
  test_id: number;
  test_title: string | null;
  status: string;
  final_score: number | null;
  created_at: string;
}
