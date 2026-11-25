import React, { useCallback, useEffect, useState, useRef } from "react";
import {
  Activity,
  ArrowUpRight,
  BookOpen,
  Check,
  CheckCheck,
  ChevronRight,
  CircleDot,
  Code2,
  FileCode2,
  GitBranch,
  GitPullRequest,
  LayoutDashboard,
  LockKeyhole,
  LogOut,
  Moon,
  Play,
  Plus,
  Search,
  Settings2,
  ShieldCheck,
  Sparkles,
  Sun,
  Terminal,
  TriangleAlert,
  X,
} from "lucide-react";
import {
  filterFindings,
  type Finding,
  type Repo,
  type Run,
  type Settings,
} from "./types";
import "./style.css";

type Page = "reviews" | "repositories" | "settings" | "docs";
export default function App() {
  const [token, setToken] = useState("");
  const tokenRef = useRef(token);
  tokenRef.current = token;
  const [entry, setEntry] = useState("");
  const [page, setPage] = useState<Page>("reviews");
  const [runs, setRuns] = useState<Run[]>([]);
  const [repos, setRepos] = useState<Repo[]>([]);
  const [config, setConfig] = useState<Settings | null>(null);
  const [active, setActive] = useState<number | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [selected, setSelected] = useState<number | null>(null);
  const [query, setQuery] = useState("");
  const [severity, setSeverity] = useState("all");
  const [source, setSource] = useState("all");
  const [category, setCategory] = useState("all");
  const [file, setFile] = useState("all");
  const [status, setStatus] = useState("all");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [dark, setDark] = useState(
    localStorage.getItem("codelens-theme") === "dark",
  );
  const [repoName, setRepoName] = useState("");
  const [installation, setInstallation] = useState("");

  const api = useCallback(
    async <T,>(path: string, method = "GET", body?: unknown): Promise<T> => {
      const response = await fetch(`/api/v1${path}`, {
        method,
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: body === undefined ? undefined : JSON.stringify(body),
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        if (response.status === 401 && tokenRef.current === token) setToken("");
        throw new Error(
          typeof payload.detail === "string"
            ? payload.detail
            : `Request failed (${response.status})`,
        );
      }
      return response.status === 204 ? (undefined as T) : response.json();
    },
    [token],
  );

  const refresh = useCallback(async () => {
    const [newRuns, newRepos, newConfig] = await Promise.all([
      api<Run[]>("/review-runs"),
      api<Repo[]>("/repositories"),
      api<Settings>("/settings"),
    ]);
    if (tokenRef.current !== token) return;
    setRuns(newRuns);
    setRepos(newRepos);
    setConfig(newConfig);
    setActive((previous) => previous ?? newRuns[0]?.id ?? null);
    setLoading(false);
  }, [api, token]);

  useEffect(() => {
    document.documentElement.dataset.theme = dark ? "dark" : "light";
    localStorage.setItem("codelens-theme", dark ? "dark" : "light");
  }, [dark]);
  useEffect(() => {
    if (!token) return;
    let alive = true;
    const load = () =>
      refresh().catch((e) => {
        if (alive) {
          setError(e.message);
          setLoading(false);
        }
      });
    void load();
    const timer = setInterval(load, 4000);
    return () => {
      alive = false;
      clearInterval(timer);
    };
  }, [token, refresh]);
  const run = runs.find((r) => r.id === active);
  useEffect(() => {
    if (!token || !active) return;
    let alive = true;
    setFindings([]);
    setCategory("all");
    setFile("all");
    setSelected(null);
    api<Finding[]>(`/review-runs/${active}/findings`)
      .then((result) => {
        if (alive) {
          setFindings(result);
        }
      })
      .catch((e) => {
        if (alive) setError(e.message);
      });
    return () => {
      alive = false;
    };
  }, [active, run?.status, token, api]);

  async function action(fn: () => Promise<void>) {
    setBusy(true);
    setError("");
    try {
      await fn();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }
  async function demo() {
    await action(async () => {
      const result = await api<{ run_id: number }>("/demo", "POST");
      setActive(result.run_id);
      setPage("reviews");
      await refresh();
    });
  }
  async function feedback(id: number, value: string) {
    await action(async () => {
      await api(`/findings/${id}/feedback`, "POST", { value });
      setFindings((previous) =>
        previous.map((f) => (f.id === id ? { ...f, feedback: value } : f)),
      );
    });
  }
  const visible = filterFindings(
    findings,
    query,
    severity,
    source,
    status,
    category,
    file,
    run?.report.config?.severity_threshold,
  );
  const detail = findings.find((f) => f.id === selected);
  useEffect(() => {
    if (selected === null) return;
    const dialog = document.querySelector<HTMLElement>('[role="dialog"]');
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setSelected(null);
      if (event.key !== "Tab" || !dialog) return;
      const controls = Array.from(
        dialog.querySelectorAll<HTMLElement>(
          'button:not(:disabled), a[href], input, select, [tabindex="0"]',
        ),
      );
      const first = controls[0],
        last = controls[controls.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last?.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first?.focus();
      }
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [selected]);
  const total = runs.reduce((sum, r) => sum + (r.report.finding_count ?? 0), 0);
  const openCount = runs.filter((r) =>
    ["queued", "running"].includes(r.status),
  ).length;

  if (!token)
    return (
      <main className="login-shell">
        <div className="login-story">
          <Brand />
          <div>
            <span className="eyebrow">EVIDENCE-FIRST CODE REVIEW</span>
            <h1>
              Understand
              <br />
              every change.
            </h1>
            <p>
              A quieter inbox. A clearer review.
              <br />
              Your code stays in your workspace.
            </p>
            <div className="login-code">
              <span>pull_request.opened</span>
              <p>✓ Verify delivery signature</p>
              <p>✓ Review changed lines</p>
              <p>✓ Keep humans in control</p>
            </div>
          </div>
          <small>Open source · Self hosted · Built for developers</small>
        </div>
        <section className="login-card">
          <span className="mini-logo">
            <LockKeyhole size={23} />
          </span>
          <h2>Your review workspace</h2>
          <p>
            Use the access token supplied by your CodeLens operator to sign in.
          </p>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              setError("");
              setLoading(true);
              setToken(entry);
              setEntry("");
            }}
          >
            <label htmlFor="token">Access token</label>
            <input
              id="token"
              type="password"
              autoComplete="off"
              value={entry}
              onChange={(e) => setEntry(e.target.value)}
              required
              minLength={32}
              placeholder="Paste your local access token"
            />
            <button className="primary" type="submit">
              Open workspace
            </button>
          </form>
          {error && (
            <p role="alert" className="error">
              {error}
            </p>
          )}
          <div className="callout">
            <Terminal size={18} />
            <div>
              First time here?
              <p>
                Follow the README quick start, then run the sample review. No
                GitHub account or AI key required.
              </p>
            </div>
          </div>
          <small>Your token is held in memory and cleared on refresh.</small>
        </section>
      </main>
    );

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Brand />
        <div className="workspace">
          <span className="workspace-icon">L</span>
          <div>
            Local workspace
            <small>
              {config?.is_operator ? "Operator" : "Repository access"}
            </small>
          </div>
          <LockKeyhole size={14} />
        </div>
        <span className="nav-label">WORKSPACE</span>
        <nav>
          {(
            [
              ["reviews", GitPullRequest, "Pull requests"],
              ["repositories", GitBranch, "Repositories"],
              ["settings", Settings2, "Settings"],
              ["docs", BookOpen, "Getting started"],
            ] as const
          ).map(([key, Icon, label]) => (
            <button
              key={key}
              className={page === key ? "nav active" : "nav"}
              onClick={() => setPage(key)}
            >
              <Icon size={18} />
              {label}
              {key === "reviews" && (
                <span className="nav-count">{runs.length}</span>
              )}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="privacy">
            <ShieldCheck size={19} />
            <strong>Private by design</strong>
            <p>
              Source stays local. AI is optional and receives rule metadata
              only.
            </p>
          </div>
          <button className="nav" onClick={() => setDark(!dark)}>
            {dark ? <Sun size={17} /> : <Moon size={17} />}{" "}
            {dark ? "Light appearance" : "Dark appearance"}
          </button>
          <button
            className="nav"
            onClick={() => {
              setToken("");
              tokenRef.current = "";
              setActive(null);
              setSelected(null);
              setRepos([]);
              setConfig(null);
              setPage("reviews");
              setRuns([]);
              setFindings([]);
            }}
          >
            <LogOut size={17} />
            Lock workspace
          </button>
          <div className="version">
            CodeLens <code>v0.1.0</code>
          </div>
        </div>
      </aside>
      <main className="main">
        <header className="topbar">
          <div>
            <LayoutDashboard size={16} />
            <span>Workspace</span>
            <ChevronRight size={14} />
            <strong>
              {page === "reviews"
                ? "Pull requests"
                : page === "docs"
                  ? "Getting started"
                  : page[0].toUpperCase() + page.slice(1)}
            </strong>
          </div>
          <span className="local-badge">
            <LockKeyhole size={13} /> Self hosted
          </span>
        </header>
        <div className="page-content">
          {error && (
            <div role="alert" className="error-banner">
              <TriangleAlert size={18} />
              {error}
              <button aria-label="Dismiss error" onClick={() => setError("")}>
                <X size={16} />
              </button>
            </div>
          )}
          {page === "reviews" && (
            <>
              <section className="page-heading">
                <div>
                  <span className="eyebrow">REVIEW WORKSPACE</span>
                  <h1>Every change, in focus.</h1>
                  <p>Evidence you can inspect. Decisions you control.</p>
                </div>
                <button
                  className="primary"
                  disabled={busy || !config?.is_operator}
                  onClick={demo}
                >
                  <Play size={16} />
                  Run sample review
                </button>
              </section>
              <div className="metrics">
                <Metric
                  label="Review runs"
                  value={runs.length}
                  icon={<GitPullRequest size={19} />}
                  note="Latest 100 runs"
                />
                <Metric
                  label="Findings surfaced"
                  value={total}
                  icon={<CircleDot size={19} />}
                  note="Across recent reviews"
                />
                <Metric
                  label="In progress"
                  value={openCount}
                  icon={<Activity size={19} />}
                  note="Queued or analyzing"
                />
                <Metric
                  label="Connected repositories"
                  value={repos.filter((r) => r.installation_id > 0).length}
                  icon={<GitBranch size={19} />}
                  note="GitHub App installations"
                />
              </div>
              <div className="section-title">
                <h2>
                  Review activity <span>{runs.length}</span>
                </h2>
                <span>
                  <ShieldCheck size={14} /> Deterministic checks first
                </span>
              </div>
              {loading ? (
                <div className="empty">
                  <Activity />
                  Loading review activity…
                </div>
              ) : runs.length === 0 ? (
                <div className="empty">
                  <GitPullRequest size={36} />
                  <h2>Your first review starts here</h2>
                  <p>
                    Analyze a small Python and TypeScript example with real
                    analyzers.
                  </p>
                  <button
                    className="primary"
                    onClick={demo}
                    disabled={busy || !config?.is_operator}
                  >
                    Run sample review
                  </button>
                </div>
              ) : (
                <div className="review-layout">
                  <section className="run-list" aria-label="Review runs">
                    {runs.map((r) => (
                      <button
                        key={r.id}
                        className={`run-item ${active === r.id ? "selected" : ""}`}
                        onClick={() => {
                          setActive(r.id);
                          setQuery("");
                          setSeverity("all");
                          setSource("all");
                          setStatus("all");
                        }}
                      >
                        <div className="run-meta">
                          <GitPullRequest size={17} />
                          <span>{r.repository}</span>
                          <span>#{r.number}</span>
                        </div>
                        <h3>{r.title}</h3>
                        <div className="run-bottom">
                          <Badge value={r.status} />
                          <code>{r.head_sha.slice(0, 7)}</code>
                        </div>
                        {r.is_demo && (
                          <span className="sample-label">SYNTHETIC SAMPLE</span>
                        )}
                      </button>
                    ))}
                  </section>
                  {run && (
                    <section className="report">
                      <div className="report-heading">
                        <div>
                          <span className="eyebrow">
                            PULL REQUEST #{run.number}
                          </span>
                          <h2>{run.title}</h2>
                          <div className="report-meta">
                            <GitBranch size={14} />
                            {run.repository}
                            <span>·</span>
                            <code title={run.head_sha}>
                              {run.head_sha.slice(0, 7)}
                            </code>
                            {run.url && (
                              <a
                                href={run.url}
                                target="_blank"
                                rel="noreferrer"
                              >
                                View on GitHub <ArrowUpRight size={13} />
                              </a>
                            )}
                          </div>
                        </div>
                        <Badge value={run.status} />
                      </div>
                      {run.is_demo && (
                        <div className="sample-notice">
                          <Code2 size={15} />
                          Sample repository · Results produced by the installed
                          analyzers
                        </div>
                      )}
                      <div className="report-tabs">
                        <span className="tab active">
                          Findings <b>{findings.length}</b>
                        </span>
                        <span className="tab">
                          {run.report.files_reviewed?.length ?? 0} files
                          reviewed
                        </span>
                        <span className="tab">
                          {run.report.skipped?.length ?? 0} skipped
                        </span>
                      </div>
                      {["queued", "running"].includes(run.status) ? (
                        <div className="empty">
                          <Activity size={28} />
                          <h3>
                            {run.status === "queued"
                              ? "Waiting for the worker"
                              : "Analyzing changed code"}
                          </h3>
                          <p>
                            This report refreshes automatically. Start the
                            worker if the queue stays idle.
                          </p>
                        </div>
                      ) : (
                        <>
                          {run.report.errors?.map((e, i) => (
                            <div className="warning" key={i}>
                              <TriangleAlert size={17} />
                              <span>
                                {e.analyzer ? `${e.analyzer}: ` : ""}
                                {e.message}
                              </span>
                            </div>
                          ))}
                          <div className="filters">
                            <label className="search">
                              <Search size={16} />
                              <input
                                aria-label="Search findings"
                                placeholder="Search findings or files…"
                                value={query}
                                onChange={(e) => setQuery(e.target.value)}
                              />
                            </label>
                            <select
                              aria-label="Filter severity"
                              value={severity}
                              onChange={(e) => setSeverity(e.target.value)}
                            >
                              <option value="all">All severities</option>
                              {[
                                "critical",
                                "high",
                                "medium",
                                "low",
                                "info",
                              ].map((v) => (
                                <option key={v}>{v}</option>
                              ))}
                            </select>
                            <select
                              aria-label="Filter source"
                              value={source}
                              onChange={(e) => setSource(e.target.value)}
                            >
                              <option value="all">All sources</option>
                              <option value="static_analyzer">
                                Static analyzer
                              </option>
                              <option value="secret_scanner">
                                Secret scanner
                              </option>
                              <option value="ai">AI advisory</option>
                              {Array.from(
                                new Set(findings.map((f) => f.analyzer)),
                              ).map((v) => (
                                <option key={v}>{v}</option>
                              ))}
                            </select>
                            <select
                              aria-label="Filter category"
                              value={category}
                              onChange={(e) => setCategory(e.target.value)}
                            >
                              <option value="all">All categories</option>
                              {Array.from(
                                new Set(findings.map((f) => f.category)),
                              ).map((v) => (
                                <option key={v}>{v}</option>
                              ))}
                            </select>
                            <select
                              aria-label="Filter file"
                              value={file}
                              onChange={(e) => setFile(e.target.value)}
                            >
                              <option value="all">All files</option>
                              {Array.from(
                                new Set(findings.map((f) => f.file_path)),
                              ).map((v) => (
                                <option key={v}>{v}</option>
                              ))}
                            </select>
                            <select
                              aria-label="Filter feedback"
                              value={status}
                              onChange={(e) => setStatus(e.target.value)}
                            >
                              <option value="all">All feedback</option>
                              {[
                                "unreviewed",
                                "useful",
                                "not_useful",
                                "ignored",
                              ].map((v) => (
                                <option key={v}>{v}</option>
                              ))}
                            </select>
                          </div>
                          <div className="findings">
                            {visible.length ? (
                              visible.map((f) => (
                                <button
                                  key={f.id}
                                  className="finding"
                                  onClick={() => setSelected(f.id)}
                                >
                                  <div className={`finding-icon ${f.severity}`}>
                                    <TriangleAlert size={18} />
                                  </div>
                                  <div className="finding-body">
                                    <div className="finding-title">
                                      {f.source === "ai" && (
                                        <span>AI � Advisory � </span>
                                      )}
                                      <h3>{f.title}</h3>
                                      <Badge value={f.severity} />
                                    </div>
                                    <p>{f.explanation}</p>
                                    <div className="finding-meta">
                                      <FileCode2 size={13} />
                                      <code>
                                        {f.file_path}:{f.start_line}
                                      </code>
                                      <span className="rule">{f.rule_id}</span>
                                      <span>{f.analyzer}</span>
                                      {f.feedback !== "unreviewed" && (
                                        <span className="feedback-state">
                                          <Check size={12} />
                                          {f.feedback.replace("_", " ")}
                                        </span>
                                      )}
                                    </div>
                                  </div>
                                  <ChevronRight size={17} />
                                </button>
                              ))
                            ) : (
                              <div className="empty compact">
                                <CheckCheck size={28} />
                                <h3>
                                  {findings.length
                                    ? "No matching findings"
                                    : run.status === "failed"
                                      ? "No report available"
                                      : "No findings reported"}
                                </h3>
                                <p>
                                  {findings.length
                                    ? "Try adjusting your search or filters."
                                    : "A clean result does not guarantee code is free of defects."}
                                </p>
                              </div>
                            )}
                          </div>
                          {run.report.ai?.summary && (
                            <div className="ai-summary">
                              <h3>
                                <Sparkles size={17} />
                                AI explanation · Advisory
                              </h3>
                              <p>{run.report.ai.summary}</p>
                              <small>
                                {run.report.ai.model} ·{" "}
                                {run.report.ai.prompt_version}
                              </small>
                            </div>
                          )}
                          {!!run.report.skipped?.length && (
                            <details className="skipped">
                              <summary>
                                Skipped files ({run.report.skipped.length})
                              </summary>
                              {run.report.skipped.map((f) => (
                                <p key={f.file}>
                                  <code>{f.file}</code> — {f.reason}
                                </p>
                              ))}
                            </details>
                          )}
                          <footer className="report-footer">
                            <ShieldCheck size={15} />
                            <span>Human review is the final check.</span>
                            <span>
                              AI {run.report.ai?.status ?? "disabled"}
                            </span>
                          </footer>
                        </>
                      )}
                    </section>
                  )}
                </div>
              )}
            </>
          )}
          {page === "repositories" && (
            <>
              <section className="page-heading">
                <div>
                  <span className="eyebrow">GITHUB INTEGRATION</span>
                  <h1>Your repositories</h1>
                  <p>Choose what CodeLens reviews. Keep access explicit.</p>
                </div>
              </section>
              {config?.is_operator && (
                <section className="panel">
                  <h2>
                    <Plus size={19} />
                    Connect a repository
                  </h2>
                  <p>
                    Install your GitHub App and add the repository to the server
                    allowlist first.
                  </p>
                  <form
                    className="repo-form"
                    onSubmit={(e) => {
                      e.preventDefault();
                      void action(async () => {
                        await api("/repositories", "POST", {
                          full_name: repoName,
                          installation_id: Number(installation),
                        });
                        setRepoName("");
                        setInstallation("");
                        await refresh();
                      });
                    }}
                  >
                    <label>
                      Repository
                      <input
                        required
                        placeholder="owner/repository"
                        value={repoName}
                        onChange={(e) => setRepoName(e.target.value)}
                      />
                    </label>
                    <label>
                      Installation ID
                      <input
                        required
                        type="number"
                        min="1"
                        placeholder="123456"
                        value={installation}
                        onChange={(e) => setInstallation(e.target.value)}
                      />
                    </label>
                    <button className="primary" disabled={busy}>
                      Connect repository
                    </button>
                  </form>
                </section>
              )}
              <div className="repo-grid">
                {repos.map((repo) => (
                  <section className="panel" key={repo.id}>
                    <div className="panel-top">
                      <GitBranch size={22} />
                      <Badge
                        value={repo.config.enabled ? "enabled" : "disabled"}
                      />
                    </div>
                    <h2>{repo.full_name}</h2>
                    <p>
                      {repo.installation_id
                        ? `Installation ${repo.installation_id}`
                        : "Synthetic demo repository"}
                    </p>
                    <p>
                      Analyzers:{" "}
                      {(repo.config.analyzers as string[]).join(", ")}
                    </p>
                    <div className="repo-actions">
                      <button
                        disabled={busy || !repo.can_configure}
                        onClick={() =>
                          action(async () => {
                            await api(
                              `/repositories/${repo.id}/config`,
                              "PATCH",
                              { ...repo.config, enabled: !repo.config.enabled },
                            );
                            await refresh();
                          })
                        }
                      >
                        {repo.config.enabled
                          ? "Pause reviews"
                          : "Enable reviews"}
                      </button>
                      <button
                        disabled={busy || !repo.can_configure}
                        onClick={() =>
                          action(async () => {
                            await api(
                              `/repositories/${repo.id}/config`,
                              "PATCH",
                              {
                                ...repo.config,
                                ai_enabled: !repo.config.ai_enabled,
                              },
                            );
                            await refresh();
                          })
                        }
                      >
                        AI: {repo.config.ai_enabled ? "on" : "off"}
                      </button>
                    </div>
                    <small>AI also requires the server-level opt-in.</small>
                  </section>
                ))}
              </div>
            </>
          )}
          {page === "settings" && (
            <>
              <section className="page-heading">
                <div>
                  <span className="eyebrow">CONFIGURATION</span>
                  <h1>Control the boundaries.</h1>
                  <p>
                    Credentials stay on the server. Source stays out of reports.
                  </p>
                </div>
              </section>
              <section className="panel settings-panel">
                <h2>Integration status</h2>
                <Setting
                  label="GitHub App"
                  value={
                    config?.github_configured ? "Configured" : "Not configured"
                  }
                />
                <Setting
                  label="Signed webhook receiver"
                  value={
                    config?.webhook_configured ? "Configured" : "Not configured"
                  }
                />
                <Setting
                  label="AI explanations"
                  value={
                    config?.ai_enabled
                      ? "Available · repository opt-in required"
                      : "Disabled"
                  }
                />
                <Setting
                  label="Data retention"
                  value={`${config?.retention_days ?? 30} days`}
                />
                <Setting
                  label="Access model"
                  value="Single operator · bearer token"
                />
                <Setting
                  label="Repository allowlist"
                  value={
                    config?.allowed_repositories.join(", ") ||
                    "No live repositories allowed"
                  }
                />
              </section>
              <div className="callout">
                <ShieldCheck />
                <div>
                  <strong>Only rule metadata can leave for AI.</strong>
                  <p>
                    Opt-in explanations send analyzer names, rule IDs, and
                    severities. Source, diffs, paths, PR titles, and secret
                    matches are never included. Provider retention depends on
                    your account terms.
                  </p>
                </div>
              </div>
            </>
          )}
          {page === "docs" && (
            <>
              <section className="page-heading">
                <div>
                  <span className="eyebrow">GETTING STARTED</span>
                  <h1>From change to clarity.</h1>
                  <p>Three steps to your first real pull request review.</p>
                </div>
              </section>
              <div className="docs-grid">
                {[
                  [
                    "Create a GitHub App",
                    "Grant read-only Contents, Pull requests, and Metadata permissions. Subscribe to pull_request events. Generate and securely mount the private key.",
                  ],
                  [
                    "Configure your workspace",
                    "Set the App ID, private key path, and webhook secret in the server environment. Add owner/repository to CODELENS_ALLOWED_REPOSITORIES and connect its installation ID.",
                  ],
                  [
                    "Open a pull request",
                    "Point the App webhook to /api/v1/webhooks/github over HTTPS. Open or update a PR. The worker analyzes added lines and this dashboard refreshes automatically.",
                  ],
                ].map(([title, text], i) => (
                  <section className="panel" key={title}>
                    <span className="step">{i + 1}</span>
                    <h2>{title}</h2>
                    <p>{text}</p>
                  </section>
                ))}
              </div>
              <section className="panel">
                <h2>What this release does</h2>
                <p>
                  Ruff for Python, fixed ESLint rules for JavaScript and
                  TypeScript, selected detect-secrets detectors, line-scoped
                  findings, feedback, and optional rule explanations.
                </p>
                <h2>Know the limits</h2>
                <p>
                  Repository-scoped access. No automatic fixes, approvals,
                  merges, or GitHub comments. No whole-program type analysis. A
                  clean report is not a security guarantee. See README,
                  SECURITY.md, and docs/architecture.md in the source repository
                  for deployment and contribution instructions.
                </p>
                <button
                  className="primary"
                  disabled={busy || !config?.is_operator}
                  onClick={demo}
                >
                  <Play size={15} />
                  Try the sample review
                </button>
              </section>
            </>
          )}
          <footer className="page-footer">
            <span>
              CodeLens <span className="muted">/</span> Understand every change.
            </span>
            <span>Open source. Human reviewed.</span>
          </footer>
        </div>
      </main>
      {detail && (
        <div className="modal-backdrop" onClick={() => setSelected(null)}>
          <section
            className="detail-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="finding-heading"
            onClick={(e) => e.stopPropagation()}
            onKeyDown={(e) => {
              if (e.key === "Escape") setSelected(null);
            }}
          >
            <button
              autoFocus
              className="close"
              aria-label="Close finding"
              onClick={() => setSelected(null)}
            >
              <X size={20} />
            </button>
            <div className="detail-tags">
              <Badge value={detail.severity} />
              <span>{detail.category}</span>
              {detail.source === "ai" && <span>AI � Advisory</span>}
              <span>{detail.confidence} confidence</span>
            </div>
            <h2 id="finding-heading">{detail.title}</h2>
            <div className="detail-location">
              <FileCode2 size={18} />
              <code>
                {detail.file_path}:{detail.start_line}
              </code>
            </div>
            <h3>Why this was flagged</h3>
            <p>{detail.explanation}</p>
            <h3>Evidence</h3>
            <pre>{detail.evidence}</pre>
            <h3>Suggested next step</h3>
            <p>{detail.suggested_action}</p>
            <div className="detail-source">
              Source: {detail.analyzer} · Rule: <code>{detail.rule_id}</code>
            </div>
            <h3>Was this finding useful?</h3>
            <div className="feedback-buttons">
              {["useful", "not_useful", "ignored", "unreviewed"].map(
                (value) => (
                  <button
                    key={value}
                    className={detail.feedback === value ? "chosen" : ""}
                    disabled={busy}
                    onClick={() => feedback(detail.id, value)}
                  >
                    {value.replace("_", " ")}
                  </button>
                ),
              )}
            </div>
          </section>
        </div>
      )}
    </div>
  );
}

function Brand() {
  return (
    <div className="brand">
      <span className="brand-mark">
        <Code2 size={22} />
      </span>
      CodeLens<span className="beta">BETA</span>
    </div>
  );
}
function Badge({ value }: { value: string }) {
  return (
    <span className={`badge ${value}`}>
      {["completed", "enabled"].includes(value) ? (
        <Check size={12} />
      ) : ["failed", "high", "critical"].includes(value) ? (
        <TriangleAlert size={12} />
      ) : (
        <CircleDot size={11} />
      )}{" "}
      {value}
    </span>
  );
}
function Metric({
  label,
  value,
  icon,
  note,
}: {
  label: string;
  value: number;
  icon: React.ReactNode;
  note: string;
}) {
  return (
    <section className="metric">
      <div>
        {label}
        {icon}
      </div>
      <strong>{String(value).padStart(2, "0")}</strong>
      <small>{note}</small>
    </section>
  );
}
function Setting({ label, value }: { label: string; value: string }) {
  return (
    <div className="setting">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
