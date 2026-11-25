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
