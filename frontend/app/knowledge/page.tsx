"use client";

import { useEffect, useState } from "react";
import Guard from "@/components/Guard";
import KnowledgePanel from "@/components/KnowledgePanel";
import { useAuth } from "@/lib/auth";
import {
  dashTeam,
  deleteMemberDoc,
  deleteMyDoc,
  deleteTeamDoc,
  getMemberDocs,
  getMyDocs,
  getTeamDocs,
  uploadMemberDocs,
  uploadMyDocs,
  uploadTeamDocs,
} from "@/lib/api";

function Knowledge() {
  const { user } = useAuth();
  const isManager = user?.role === "manager";
  const [members, setMembers] = useState<{ id: string; name: string }[]>([]);
  const [memberId, setMemberId] = useState<string>("");

  useEffect(() => {
    if (isManager) {
      dashTeam()
        .then((t) => setMembers((t.members || []).filter((m: any) => m.id !== user?.id)))
        .catch(() => {});
    }
  }, [isManager, user?.id]);

  return (
    <div className="page">
      <div className="page-title">Knowledge</div>
      <div className="page-sub">
        Add documents the coach should draw on. These stack on top of KPMG&apos;s org-wide knowledge.
      </div>

      {/* Personal / project knowledge — everyone */}
      <KnowledgePanel
        title="My project knowledge (only me)"
        hint="Files only you see — like adding documents to a Claude Project. The coach uses these in your chats."
        load={getMyDocs}
        upload={uploadMyDocs}
        remove={deleteMyDoc}
      />

      {/* Team knowledge — manager edits, members view */}
      <KnowledgePanel
        title={isManager ? "Team knowledge (shared with your team)" : "Team knowledge (read-only)"}
        hint={
          isManager
            ? "Files shared with everyone on your team. Only you (the manager) can add or remove these."
            : "Documents your manager shared with the whole team. Used in everyone's chats."
        }
        canEdit={isManager}
        load={getTeamDocs}
        upload={uploadTeamDocs}
        remove={deleteTeamDoc}
      />

      {/* Manager → a specific member's personal knowledge */}
      {isManager && (
        <div className="card">
          <div className="card-label">Give a team member their own knowledge</div>
          <div className="muted" style={{ fontSize: 12, marginBottom: 12 }}>
            Add files to a specific person&apos;s personal knowledge base — useful for setting up
            someone&apos;s project before they start.
          </div>
          <select
            className="select"
            style={{ marginBottom: 14 }}
            value={memberId}
            onChange={(e) => setMemberId(e.target.value)}
          >
            <option value="">Select a team member…</option>
            {members.map((m) => (
              <option key={m.id} value={m.id}>{m.name}</option>
            ))}
          </select>
          {memberId && (
            <KnowledgePanel
              key={memberId}
              title={`${members.find((m) => m.id === memberId)?.name}'s knowledge`}
              hint="Files added to this person's personal knowledge base."
              load={() => getMemberDocs(memberId)}
              upload={(files) => uploadMemberDocs(memberId, files)}
              remove={(id) => deleteMemberDoc(memberId, id)}
            />
          )}
        </div>
      )}
    </div>
  );
}

export default function Page() {
  return (
    <Guard role={["employee", "manager"]}>
      <Knowledge />
    </Guard>
  );
}
