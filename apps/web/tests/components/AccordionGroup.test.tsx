import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AccordionGroup } from "../../src/components/AccordionGroup";
import { makeGroup, makeSubpoint } from "../factories";

describe("AccordionGroup", () => {
  it("hides its body when closed and shows it when open", () => {
    const group = makeGroup();
    const { rerender } = render(
      <AccordionGroup group={group} index={1} isOpen={false} onToggle={vi.fn()} onAct={vi.fn()} pendingSubpointId={null} />
    );
    expect(screen.queryByText(group.purpose)).toBeInTheDocument(); // header subtitle always visible
    expect(screen.queryByText(group.subpoints[0].title)).not.toBeInTheDocument();

    rerender(
      <AccordionGroup group={group} index={1} isOpen onToggle={vi.fn()} onAct={vi.fn()} pendingSubpointId={null} />
    );
    expect(screen.getByText(group.subpoints[0].title)).toBeInTheDocument();
  });

  it("calls onToggle when the header is clicked", async () => {
    const onToggle = vi.fn();
    const group = makeGroup();
    render(<AccordionGroup group={group} index={1} isOpen={false} onToggle={onToggle} onAct={vi.fn()} pendingSubpointId={null} />);
    await userEvent.click(screen.getByRole("button", { name: new RegExp(group.title) }));
    expect(onToggle).toHaveBeenCalledTimes(1);
  });

  it("shows the applicability reason instead of subpoints when the group does not apply", () => {
    const group = makeGroup({
      applies: false,
      applicability_reason: "Not needed for this production mode",
      status: "not_applicable",
    });
    render(<AccordionGroup group={group} index={1} isOpen onToggle={vi.fn()} onAct={vi.fn()} pendingSubpointId={null} />);
    expect(screen.getByText(/Not needed for this production mode/)).toBeInTheDocument();
    expect(screen.queryByText(group.subpoints[0].title)).not.toBeInTheDocument();
  });

  it("forwards a subpoint action with the jrn id and a full JourneyItemAction payload", async () => {
    const onAct = vi.fn();
    const group = makeGroup({
      can_act: true,
      na_policy: "never",
      subpoints: [makeSubpoint({ id: "JRN-01.1.1", status: "not_started" })],
    });
    render(<AccordionGroup group={group} index={1} isOpen onToggle={vi.fn()} onAct={onAct} pendingSubpointId={null} />);
    await userEvent.click(screen.getByRole("button", { name: "Mark complete" }));
    expect(onAct).toHaveBeenCalledWith("JRN-01.1.1", { action: "complete", not_applicable_reason: null });
  });

  it("only shows the pending state on the matching subpoint", () => {
    const group = makeGroup({
      subpoints: [
        makeSubpoint({ id: "JRN-01.1.1", key: "a", status: "not_started" }),
        makeSubpoint({ id: "JRN-01.1.2", key: "validate", kind: "review_gate", status: "not_started" }),
      ],
    });
    render(
      <AccordionGroup group={group} index={1} isOpen onToggle={vi.fn()} onAct={vi.fn()} pendingSubpointId="JRN-01.1.1" />
    );
    const buttons = screen.getAllByRole("button", { name: "Mark complete" });
    expect(buttons[0]).toBeDisabled();
    expect(buttons[1]).toBeEnabled();
  });
});
