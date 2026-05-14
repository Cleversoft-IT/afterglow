import { PostCallActions } from "@/components/phone/PostCallActions";

export default function PostCallPage({ params }: { params: { callId: string } }) {
  return (
    <main className="min-h-screen bg-zinc-50">
      <PostCallActions callId={params.callId} />
    </main>
  );
}
