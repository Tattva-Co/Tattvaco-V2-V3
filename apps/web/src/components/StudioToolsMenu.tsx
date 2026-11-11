import { useEffect, useRef, useState } from "react";
import { TOOL_REGISTRY, type ToolKey } from "../lib/studioTools";

export function StudioToolsMenu({
  activeSectionId,
  onOpenTool,
}: {
  activeSectionId: string;
  onOpenTool: (tool: ToolKey) => void;
}) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onClickOutside(event: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, [open]);

  const relevant = TOOL_REGISTRY.filter((t) => t.sections.length === 0 || t.sections.includes(activeSectionId));

  return (
    <div className="studio-tools-menu" ref={rootRef}>
      <button type="button" className="btn" aria-expanded={open} aria-haspopup="true" onClick={() => setOpen((v) => !v)}>
        Studio Tools
      </button>
      {open && (
        <div className="studio-tools-dropdown" role="menu">
          {relevant.length === 0 ? (
            <div className="studio-tools-empty">No tools for this section yet.</div>
          ) : (
            relevant.map((tool) => (
              <button
                key={tool.key}
                type="button"
                role="menuitem"
                className="tool-link"
                onClick={() => {
                  setOpen(false);
                  onOpenTool(tool.key);
                }}
              >
                {tool.name}
                <small>{tool.description}</small>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}
