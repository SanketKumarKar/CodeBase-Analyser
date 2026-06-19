"use client";

import ThreePanelLayout from "@/components/layout/ThreePanelLayout";
import RepoPanel from "@/components/layout/RepoPanel";
import ChatPanel from "@/components/layout/ChatPanel";
import GraphPanel from "@/components/layout/GraphPanel";
import TopBar from "@/components/layout/TopBar";

export default function Home() {
  return (
    <div className="flex flex-col h-screen overflow-hidden">
      <TopBar />
      <ThreePanelLayout
        left={<RepoPanel />}
        center={<ChatPanel />}
        right={<GraphPanel />}
      />
    </div>
  );
}
