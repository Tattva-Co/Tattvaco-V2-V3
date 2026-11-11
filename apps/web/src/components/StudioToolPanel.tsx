import { useEffect, useRef, type ReactNode } from "react";

/** A generic overlay shell every Studio Tool renders into (GW3): a title, a close
 * button, and a scrollable body -- the tool itself owns everything inside. Closing on
 * Escape and focusing the panel on open match the wireframe's existing modal behaviour
 * (see tokens.css's :focus-visible rules) without each tool re-implementing it. */
export function StudioToolPanel({
  title,
  subtitle,
  onClose,
  children,
}: {
  title: string;
  subtitle?: string;
  onClose: () => void;
  children: ReactNode;
}) {
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    panelRef.current?.focus();
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  return (
    <div className="tool-overlay" onClick={onClose}>
      <div
        className="tool-modal"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        tabIndex={-1}
        ref={panelRef}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="tool-modal-head">
          <div>
            <h2>{title}</h2>
            {subtitle && <p>{subtitle}</p>}
          </div>
          <button type="button" className="tool-modal-close" aria-label="Close" onClick={onClose}>
            &times;
          </button>
        </div>
        <div className="tool-modal-body">{children}</div>
      </div>
    </div>
  );
}
