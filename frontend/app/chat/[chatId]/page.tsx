import { DemoChatWorkspace } from '@/components/demo/demo-chat-workspace';

export default function ChatPage({ params }: { params: { chatId: string } }) {
  return <DemoChatWorkspace initialChatId={params.chatId} />;
}
