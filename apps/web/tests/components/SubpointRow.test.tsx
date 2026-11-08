import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SubpointRow } from "../../src/components/SubpointRow";
import { makeSubpoint } from "../factories";

describe("SubpointRow", () => {
  it("shows no action buttons when the viewer cannot act, only the status", () => {
    render(
      <SubpointRow
        subpoint={makeSubpoint()}
        index={1}
        canAct={false}
        naPolicy="never"
        isSystemDerived={false}
        onAct={vi.fn()}
        pending={false}
      />
    );
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    expect(screen.getByText("Not started")).toBeInTheDocument();
  });

  it("offers draft, complete, and not-applicable actions for a plain not-started work item", () => {
    render(
      <SubpointRow
        subpoint={makeSubpoint({ status: "not_started", kind: "work" })}
        index={1}
        canAct
        naPolicy="reason_required"
        isSystemDerived={false}
        onAct={vi.fn()}
        pending={false}
      />
    );
    expect(screen.getByRole("button", { name: "Save draft" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Mark complete" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Not applicable" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Request review" })).not.toBeInTheDocument();
  });

  it("offers a request-review action for a review_gate subpoint", () => {
    render(
      <SubpointRow
        subpoint={makeSubpoint({ status: "in_progress", kind: "review_gate" })}
        index={1}
        canAct
        naPolicy="never"
        isSystemDerived={false}
        onAct={vi.fn()}
        pending={false}
      />
    );
    expect(screen.getByRole("button", { name: "Request review" })).toBeInTheDocument();
  });

  it("hides the not-applicable action when the group's na_policy is 'never'", () => {
    render(
      <SubpointRow
        subpoint={makeSubpoint()}
        index={1}
        canAct
        naPolicy="never"
        isSystemDerived={false}
        onAct={vi.fn()}
        pending={false}
      />
    );
    expect(screen.queryByRole("button", { name: "Not applicable" })).not.toBeInTheDocument();
  });

  it("hides all manual actions for a system-derived validate subpoint", () => {
    render(
      <SubpointRow
        subpoint={makeSubpoint({ key: "validate", kind: "review_gate", status: "not_started" })}
        index={2}
        canAct
        naPolicy="never"
        isSystemDerived
        onAct={vi.fn()}
        pending={false}
      />
    );
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    expect(screen.getByText("Completes automatically")).toBeInTheDocument();
  });

  it("shows no actions once a subpoint is in a terminal state", () => {
    render(
      <SubpointRow
        subpoint={makeSubpoint({ status: "completed" })}
        index={1}
        canAct
        naPolicy="reason_required"
        isSystemDerived={false}
        onAct={vi.fn()}
        pending={false}
      />
    );
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("calls onAct('complete') when Mark complete is clicked", async () => {
    const onAct = vi.fn();
    render(
      <SubpointRow
        subpoint={makeSubpoint()}
        index={1}
        canAct
        naPolicy="never"
        isSystemDerived={false}
        onAct={onAct}
        pending={false}
      />
    );
    await userEvent.click(screen.getByRole("button", { name: "Mark complete" }));
    expect(onAct).toHaveBeenCalledWith("complete");
  });

  it("requires a reason before confirming not-applicable, then submits it", async () => {
    const onAct = vi.fn();
    render(
      <SubpointRow
        subpoint={makeSubpoint()}
        index={1}
        canAct
        naPolicy="reason_required"
        isSystemDerived={false}
        onAct={onAct}
        pending={false}
      />
    );
    await userEvent.click(screen.getByRole("button", { name: "Not applicable" }));
    const confirmButton = screen.getByRole("button", { name: "Confirm" });
    expect(confirmButton).toBeDisabled();

    await userEvent.type(screen.getByLabelText("Reason this item is not applicable"), "No weapons in this story");
    expect(confirmButton).toBeEnabled();

    await userEvent.click(confirmButton);
    expect(onAct).toHaveBeenCalledWith("not_applicable", "No weapons in this story");
  });

  it("disables every action button while a mutation is pending", () => {
    render(
      <SubpointRow
        subpoint={makeSubpoint()}
        index={1}
        canAct
        naPolicy="reason_required"
        isSystemDerived={false}
        onAct={vi.fn()}
        pending
      />
    );
    for (const button of screen.getAllByRole("button")) {
      expect(button).toBeDisabled();
    }
  });
});
