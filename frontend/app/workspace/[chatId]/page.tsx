import { WorkspaceShell } from '@/components/workspace/workspace-shell';

export default function WorkspaceChatPage({ params }: { params: { chatId: string } }) {
  return <WorkspaceShell initialChatId={params.chatId} />;
}
