import { render, screen } from "@testing-library/react";
import { StatusChip } from "../../src/components/StatusChip";

describe("StatusChip", () => {
  it("renders human-readable text, never color alone, for every known status", () => {
    const cases: [string, string, string][] = [
      ["not_started", "Not started", ""],
      ["in_progress", "In progress", "progress"],
      ["review_required", "Review required", "review"],
      ["changes_required", "Changes required", "changes"],
      ["blocked", "Blocked", "blocked"],
      ["completed", "Completed", "done"],
      ["not_applicable", "Not applicable", "na"],
      ["stale", "Needs re-review", "blocked"],
      ["ready_to_continue", "Ready to continue", "done"],
    ];
    for (const [status, label, cls] of cases) {
      const { unmount } = render(<StatusChip status={status} />);
      const chip = screen.getByText(label);
      expect(chip).toBeInTheDocument();
      if (cls) expect(chip.className).toContain(cls);
      unmount();
    }
  });

  it("falls back to the raw status string for an unknown value rather than crashing", () => {
    render(<StatusChip status="some_future_status" />);
    expect(screen.getByText("some_future_status")).toBeInTheDocument();
  });
});
