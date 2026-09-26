import { ChatWorkspace } from "@/components/workspace/chat-workspace";
import { RequireAuth } from "@/components/require-auth";

export default function WorkspacePage() {
  return (
    <RequireAuth>
      <ChatWorkspace />
    </RequireAuth>
  );
}
