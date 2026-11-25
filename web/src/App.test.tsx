// @vitest-environment jsdom
import React from "react";
import { afterEach, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  localStorage.clear();
});

it("opens a scoped workspace, hides connection controls, and locks without storing credentials", async () => {
  const token = "synthetic-reviewer-" + "x".repeat(32);
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => ({
      ok: true,
      status: 200,
      json: async () =>
        url.endsWith("/settings")
          ? { is_operator: false, allowed_repositories: [], retention_days: 30 }
          : [],
    })),
  );
  const user = userEvent.setup();
  render(<App />);
  await user.type(screen.getByLabelText("Access token"), token);
  await user.click(screen.getByRole("button", { name: "Open workspace" }));
  await screen.findByText("Repository access");
  await user.click(screen.getByRole("button", { name: "Repositories" }));
  expect(screen.queryByText("Connect a repository")).toBeNull();
  expect(JSON.stringify(localStorage)).not.toContain(token);
  await user.click(screen.getByRole("button", { name: "Lock workspace" }));
  expect(screen.getByLabelText("Access token")).toBeTruthy();
});

it("renders authentication failure without admitting the user", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => ({
      ok: false,
      status: 401,
      json: async () => ({ detail: "A valid access token is required" }),
    })),
  );
  const user = userEvent.setup();
  render(<App />);
  await user.type(
    screen.getByLabelText("Access token"),
    "invalid-" + "x".repeat(32),
  );
  await user.click(screen.getByRole("button", { name: "Open workspace" }));
  expect(await screen.findByRole("alert")).toBeTruthy();
  expect(screen.getByLabelText("Access token")).toBeTruthy();
});

it("shows a completed review, filters files, and opens escaped advisory evidence", async () => {
  const finding = {
    id: 1,
    title: "Check unused import",
    severity: "low",
    source: "ai",
    analyzer: "openai",
    rule_id: "advice:F401",
    file_path: "src/a.py",
    start_line: 3,
    end_line: 3,
    category: "maintainability",
    confidence: 0.8,
    feedback: "unreviewed",
    explanation: "Review the import",
    evidence: "<script>untrusted()</script>",
    suggested_action: "Remove if unused",
  };
  const run = {
    id: 1,
    repository_id: 1,
    repository: "demo/repository",
    number: 1,
    title: "Synthetic review",
    head_sha: "a".repeat(40),
    status: "completed",
    is_demo: true,
    created_at: "2026-01-01T00:00:00Z",
    report: { finding_count: 1, files_reviewed: ["src/a.py"] },
  };
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => ({
      ok: true,
      status: 200,
      json: async () =>
        url.endsWith("/findings")
          ? [finding]
          : url.endsWith("/review-runs")
            ? [run]
            : url.endsWith("/settings")
              ? { is_operator: false, allowed_repositories: [] }
              : [],
    })),
  );
  const user = userEvent.setup();
  render(<App />);
  await user.type(
    screen.getByLabelText("Access token"),
    "synthetic-" + "x".repeat(32),
  );
  await user.click(screen.getByRole("button", { name: "Open workspace" }));
  await screen.findByText("Check unused import");
  await user.selectOptions(screen.getByLabelText("Filter file"), "src/a.py");
  await user.selectOptions(screen.getByLabelText("Filter source"), "ai");
  await user.click(screen.getByRole("button", { name: /Check unused import/ }));
  expect(screen.getByRole("dialog")).toBeTruthy();
  expect(screen.getByText("<script>untrusted()</script>")).toBeTruthy();
  expect(document.querySelector("script")).toBeNull();
  await user.keyboard("{Escape}");
  expect(screen.queryByRole("dialog")).toBeNull();
});
