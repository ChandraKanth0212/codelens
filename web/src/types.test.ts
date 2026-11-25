import { describe, expect, it } from "vitest";
import { filterFindings, type Finding } from "./types";

const items = [
  {
    id: 1,
    title: "Unused import",
    severity: "low",
    analyzer: "ruff",
    file_path: "src/a.py",
    rule_id: "F401",
    category: "maintainability",
    feedback: "useful",
  },
  {
    id: 2,
    title: "Dynamic evaluation",
    severity: "high",
    analyzer: "eslint",
    file_path: "src/b.ts",
    rule_id: "no-eval",
    category: "security",
    feedback: "unreviewed",
  },
] as Finding[];
describe("finding filters", () => {
  it("sorts risk first without modifying the source", () => {
    expect(
      filterFindings(items, "", "all", "all", "all").map((f) => f.id),
    ).toEqual([2, 1]);
    expect(items[0].id).toBe(1);
  });
  it("combines search, severity, analyzer, and feedback", () => {
    expect(
      filterFindings(items, "SRC/A", "low", "ruff", "useful").map((f) => f.id),
    ).toEqual([1]);
    expect(filterFindings(items, "SRC/A", "high", "ruff", "useful")).toEqual(
      [],
    );
  });
});
