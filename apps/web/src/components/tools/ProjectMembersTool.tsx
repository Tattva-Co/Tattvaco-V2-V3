import { useState } from "react";
import {
  useAddProjectMember,
  useProjectMembers,
  useRemoveProjectMember,
  useRoleTemplates,
  useUpdateProjectMemberRole,
} from "../../hooks/useProjects";
import { describeError } from "../../lib/describeError";

/** S-TEAM-02 Project Members & Roles. A member must already belong to the
 * organization (S-TEAM-01); this tool only assigns a project role to an existing
 * org member, it does not invite strangers. */
export function ProjectMembersTool({ projectId }: { projectId: string }) {
  const members = useProjectMembers(projectId);
  const roleTemplates = useRoleTemplates(projectId);
  const addMember = useAddProjectMember(projectId);
  const updateRole = useUpdateProjectMemberRole(projectId);
  const removeMember = useRemoveProjectMember(projectId);

  const [email, setEmail] = useState("");
  const [roleKey, setRoleKey] = useState("viewer");

  if (members.isLoading || roleTemplates.isLoading) return <div className="state-panel">Loading members…</div>;

  const roles = roleTemplates.data ?? [];

  return (
    <div>
      <form
        className="tool-form"
        style={{ marginBottom: 16 }}
        onSubmit={(e) => {
          e.preventDefault();
          if (!email.trim()) return;
          addMember.mutate(
            { email: email.trim(), role_template_key: roleKey },
            { onSuccess: () => setEmail("") }
          );
        }}
      >
        <label htmlFor="member-email">Add an existing organization member</label>
        <input
          id="member-email"
          type="email"
          placeholder="person@studio.example"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <select value={roleKey} onChange={(e) => setRoleKey(e.target.value)} aria-label="Role">
          {roles.map((r) => (
            <option key={r.key} value={r.key}>
              {r.name}
            </option>
          ))}
        </select>
        <button type="submit" className="btn small" disabled={!email.trim() || addMember.isPending}>
          Add member
        </button>
        {addMember.isError && (
          <p role="alert" style={{ color: "var(--red)", fontSize: 11 }}>
            {describeError(addMember.error)}
          </p>
        )}
      </form>

      {members.data?.map((m) => (
        <div key={m.user_id} className="tool-list-item">
          <h4>{m.full_name}</h4>
          <p className="meta">{m.email}</p>
          <div style={{ display: "flex", gap: 6, alignItems: "center", marginTop: 6 }}>
            <select
              value={m.role_template_key}
              aria-label={`Role for ${m.full_name}`}
              disabled={updateRole.isPending}
              onChange={(e) =>
                updateRole.mutate({ userId: m.user_id, body: { role_template_key: e.target.value } })
              }
            >
              {roles.map((r) => (
                <option key={r.key} value={r.key}>
                  {r.name}
                </option>
              ))}
            </select>
            <button
              type="button"
              className="tiny-btn"
              disabled={removeMember.isPending}
              onClick={() => removeMember.mutate(m.user_id)}
            >
              Remove
            </button>
          </div>
        </div>
      ))}
      {(updateRole.isError || removeMember.isError) && (
        <p role="alert" style={{ color: "var(--red)", fontSize: 11 }}>
          {describeError(updateRole.error ?? removeMember.error)}
        </p>
      )}
    </div>
  );
}
