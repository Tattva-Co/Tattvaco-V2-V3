import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { StudioToolsMenu } from "../../src/components/StudioToolsMenu";

describe("StudioToolsMenu", () => {
  it("shows only the tools relevant to the active section, plus cross-stage tools", async () => {
    render(<StudioToolsMenu activeSectionId="JRN-03" onOpenTool={vi.fn()} />);
    await userEvent.click(screen.getByRole("button", { name: "Studio Tools" }));

    expect(screen.getByRole("menuitem", { name: /Historical Research/ })).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: /Candidate Review/ })).toBeInTheDocument(); // cross-stage
    expect(screen.getByRole("menuitem", { name: /Audit Trail/ })).toBeInTheDocument(); // cross-stage
    expect(screen.queryByRole("menuitem", { name: /^Assets/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("menuitem", { name: /Storyboard/ })).not.toBeInTheDocument();
  });

  it("shows a 'no tools' message for a section with none", async () => {
    render(<StudioToolsMenu activeSectionId="JRN-10" onOpenTool={vi.fn()} />);
    await userEvent.click(screen.getByRole("button", { name: "Studio Tools" }));
    // JRN-10 has no section-scoped tool, but cross-stage tools (review, audit) still show.
    expect(screen.getByRole("menuitem", { name: /Audit Trail/ })).toBeInTheDocument();
  });

  it("calls onOpenTool with the tool's key and closes the menu", async () => {
    const onOpenTool = vi.fn();
    render(<StudioToolsMenu activeSectionId="JRN-02" onOpenTool={onOpenTool} />);
    await userEvent.click(screen.getByRole("button", { name: "Studio Tools" }));
    await userEvent.click(screen.getByRole("menuitem", { name: /^Assets/ }));

    expect(onOpenTool).toHaveBeenCalledWith("assets");
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });
});
