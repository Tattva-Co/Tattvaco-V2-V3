export type ToolKey =
  | "overview"
  | "assets"
  | "script_intelligence"
  | "review"
  | "historical_research"
  | "storyboard"
  | "film_bible"
  | "audit";

export interface ToolDescriptor {
  key: ToolKey;
  name: string;
  description: string;
  /** Journey section ids this tool is reachable from. An empty array means "cross-stage"
   * -- always reachable, regardless of which section is open (GW3 scope note: this is a
   * section-scoped index of the tools that actually exist today, not the full 60+ screen
   * registry in packages/domain/journey_manifest.yaml's `screens` list -- most of those
   * describe features not built until the D-stage milestones). */
  sections: string[];
}

export const TOOL_REGISTRY: ToolDescriptor[] = [
  {
    key: "overview",
    name: "Project Overview",
    description: "Screenplay/version status, pending approvals, running tasks and the next action (S-PRJ-01).",
    sections: [],
  },
  {
    key: "assets",
    name: "Assets",
    description: "Upload screenplays into immutable storage.",
    // Also reachable from JRN-01: section 01's 7 subpoints (format, mode, governance,
    // delivery, team, policies) are all administrative, and gating the screenplay
    // upload behind finishing every one of them first blocks the thing a writer
    // actually wants to do first on a new project.
    sections: ["JRN-01", "JRN-02"],
  },
  {
    key: "script_intelligence",
    name: "Script Intelligence",
    description: "Extract scenes, characters and locations from the screenplay.",
    sections: ["JRN-01", "JRN-02"],
  },
  {
    key: "review",
    name: "Candidate Review",
    description: "Approve or reject AI-extracted candidates from any workflow.",
    sections: [],
  },
  {
    key: "historical_research",
    name: "Historical Research",
    description: "Investigate, record and verify historical evidence.",
    sections: ["JRN-03"],
  },
  {
    key: "storyboard",
    name: "Storyboard",
    description: "Generate and review the visual shot sequence.",
    sections: ["JRN-06"],
  },
  {
    key: "film_bible",
    name: "Film Bible",
    description: "Canonical visual-world rules, scenes and entities.",
    // Cross-stage, like Review and Audit: its Scenes/Entities/Versions tabs show canon
    // that starts existing the moment the first Script Intelligence candidate is
    // approved (JRN-01/02), well before Visual World (JRN-05) is reached -- gating the
    // whole tool to JRN-05 hid that canon from a writer for most of the journey, even
    // though the Visual World rule tabs it also holds are section-05 work.
    sections: [],
  },
  { key: "audit", name: "Audit Trail", description: "Every project lifecycle action and decision.", sections: [] },
];
