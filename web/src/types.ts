export type Run = {
  id: number;
  repository_id: number;
  repository: string;
  number: number;
  title: string;
  head_sha: string;
  status: string;
  is_demo: boolean;
  created_at: string;
  completed_at: string | null;
  url: string | null;
  report: {
    finding_count?: number;
    config?: { severity_threshold?: string };
    files_reviewed?: string[];
    skipped?: { file: string; reason: string }[];
    errors?: { message: string; analyzer?: string; file?: string }[];
    ai?: {
      status: string;
      advisory?: boolean;
      summary?: string;
      model?: string;
      prompt_version?: string;
    };
  };
};
export type Finding = {
  id: number;
  source: string;
  analyzer: string;
  rule_id: string;
  severity: string;
  category: string;
  title: string;
  file_path: string;
  start_line: number;
  end_line: number;
  explanation: string;
  suggested_action: string;
  evidence: string;
  confidence: string | number;
  feedback: string;
};
export type Repo = {
  id: number;
  full_name: string;
  installation_id: number;
  can_configure: boolean;
  config: Record<string, unknown>;
};
export type Settings = {
  is_operator: boolean;
  github_configured: boolean;
  webhook_configured: boolean;
  ai_enabled: boolean;
  retention_days: number;
  allowed_repositories: string[];
};

export const severityOrder: Record<string, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
  info: 4,
};
export function filterFindings(
  findings: Finding[],
  query: string,
  severity: string,
  source: string,
  status: string,
  category = "all",
  file = "all",
  threshold = "info",
) {
  return findings
    .filter(
      (f) =>
        (category === "all" || f.category === category) &&
        (file === "all" || f.file_path === file) &&
        severityOrder[f.severity] <= severityOrder[threshold] &&
        (severity === "all" || f.severity === severity) &&
        (source === "all" || f.analyzer === source || f.source === source) &&
        (status === "all" || f.feedback === status) &&
        `${f.title} ${f.file_path} ${f.rule_id} ${f.category}`
          .toLowerCase()
          .includes(query.toLowerCase()),
    )
    .sort((a, b) => severityOrder[a.severity] - severityOrder[b.severity]);
}
