/** Maps the 8 journey statuses (packages/domain/journey.py ITEM_STATUSES; the same set
 * is also used, as a subset, for groups and sections) to the wireframe's status chip
 * styles and to human-readable, non-color-only text (WCAG 2.2 AA: never color alone). */
const STATUS_LABEL: Record<string, string> = {
  not_started: "Not started",
  in_progress: "In progress",
  review_required: "Review required",
  changes_required: "Changes required",
  blocked: "Blocked",
  completed: "Completed",
  not_applicable: "Not applicable",
  stale: "Needs re-review",
  ready_to_continue: "Ready to continue",
};

const STATUS_CLASS: Record<string, string> = {
  completed: "done",
  ready_to_continue: "done",
  in_progress: "progress",
  review_required: "review",
  changes_required: "changes",
  blocked: "blocked",
  stale: "blocked",
  not_applicable: "na",
};

export function StatusChip({ status }: { status: string }) {
  const cls = STATUS_CLASS[status] ?? "";
  const label = STATUS_LABEL[status] ?? status;
  return <span className={`status ${cls}`.trim()}>{label}</span>;
}
