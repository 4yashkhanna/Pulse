"use client";

import Guard from "@/components/Guard";
import KnowledgePanel from "@/components/KnowledgePanel";
import { useAuth } from "@/lib/auth";
import { deleteTeamDoc, getTeamDocs, uploadTeamDocs } from "@/lib/api";

function TeamKnowledge() {
  const { user } = useAuth();
  const isManager = user?.role === "manager";
  return (
    <div className="page">
      <div className="page-title">Team Knowledge</div>
      <div className="page-sub">
        The general knowledge base shared with everyone on your team.
      </div>

      <KnowledgePanel
        title={isManager ? "General team knowledge" : "General team knowledge (read-only)"}
        hint={
          isManager
            ? "Files every team member's coach can draw on, in any chat. Only you (the manager) can edit these."
            : "Documents your manager shared with the whole team. The coach uses these in all your chats."
        }
        canEdit={isManager}
        load={getTeamDocs}
        upload={uploadTeamDocs}
        remove={deleteTeamDoc}
      />

      <div className="card muted" style={{ fontSize: 13 }}>
        Looking for <strong>personal or project-specific</strong> files? Those live in{" "}
        <strong>Projects</strong> inside the Coach — create a project there, add its files, and
        chat within it. {isManager && "Team projects (with their own files) are created there too."}
      </div>
    </div>
  );
}

export default function Page() {
  return (
    <Guard role={["employee", "manager"]}>
      <TeamKnowledge />
    </Guard>
  );
}
