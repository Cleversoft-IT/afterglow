import { PostCallActions } from "@/components/phone/PostCallActions";

export default function PostCallPage({ params }: { params: { callId: string } }) {
  return (
    <main className="min-h-dvh bg-ui-canvas">
      <PostCallActions callId={params.callId} />
    </main>
  );
}
