import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { JourneyRail } from "../../src/components/JourneyRail";
import { makeProject, makeSection } from "../factories";

function renderRail(sections: ReturnType<typeof makeSection>[], activeSectionId: string, onSelectSection = vi.fn()) {
  render(
    <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <JourneyRail
        project={makeProject()}
        sections={sections}
        activeSectionId={activeSectionId}
        onSelectSection={onSelectSection}
      />
    </MemoryRouter>
  );
  return onSelectSection;
}

describe("JourneyRail", () => {
  it("always unlocks the first section regardless of its status", () => {
    const sections = [makeSection({ id: "JRN-01", status: "not_started" })];
    renderRail(sections, "JRN-01");
    expect(screen.getByRole("button", { name: /Project Workspace & Setup/ })).toBeEnabled();
  });

  it("locks a section until the previous one is ready_to_continue or completed", () => {
    const sections = [
      makeSection({ id: "JRN-01", title: "Setup", status: "in_progress" }),
      makeSection({ id: "JRN-02", title: "Screenplay", status: "not_started" }),
    ];
    renderRail(sections, "JRN-01");
    expect(screen.getByRole("button", { name: /Screenplay/ })).toBeDisabled();
  });

  it("unlocks the next section once the previous one is ready_to_continue", () => {
    const sections = [
      makeSection({ id: "JRN-01", title: "Setup", status: "ready_to_continue" }),
      makeSection({ id: "JRN-02", title: "Screenplay", status: "not_started" }),
    ];
    renderRail(sections, "JRN-02");
    expect(screen.getByRole("button", { name: /Screenplay/ })).toBeEnabled();
  });

  it("marks the active section with aria-current and calls back when an unlocked one is clicked", async () => {
    const sections = [
      makeSection({ id: "JRN-01", title: "Setup", status: "completed" }),
      makeSection({ id: "JRN-02", title: "Screenplay", status: "not_started" }),
    ];
    const onSelectSection = renderRail(sections, "JRN-01");

    expect(screen.getByRole("button", { name: /Setup/ })).toHaveAttribute("aria-current", "step");

    await userEvent.click(screen.getByRole("button", { name: /Screenplay/ }));
    expect(onSelectSection).toHaveBeenCalledWith("JRN-02");
  });

  it("never calls back for a disabled (locked) section", async () => {
    const sections = [
      makeSection({ id: "JRN-01", title: "Setup", status: "not_started" }),
      makeSection({ id: "JRN-02", title: "Screenplay", status: "not_started" }),
    ];
    const onSelectSection = renderRail(sections, "JRN-01");

    await userEvent.click(screen.getByRole("button", { name: /Screenplay/ }));
    expect(onSelectSection).not.toHaveBeenCalled();
  });
});
