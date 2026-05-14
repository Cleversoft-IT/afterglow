import { notFound } from "next/navigation";

import { IncomingCallScreen } from "@/components/phone/IncomingCallScreen";
import { api } from "@/lib/api";
import { getScenario } from "@/lib/demoScenarios";

export default async function IncomingPage({
  params,
}: {
  params: { callId: string };
}) {
  const scenario = getScenario(params.callId);
  if (!scenario) notFound();

  const businesses = await api.listBusinesses().catch(() => []);
  const biz = businesses.find((b) => b.domain === scenario.business_domain);
  if (!biz) {
    return (
      <main className="min-h-screen grid place-items-center bg-zinc-100">
        <div className="p-8 text-zinc-700">
          No business found for domain <code>{scenario.business_domain}</code>.
          Did you run the seed?
        </div>
      </main>
    );
  }

  const templates = await api.listTemplates(biz.id).catch(() => []);
  const template = templates.find((t) => t.is_active) ?? templates[0];
  if (!template) {
    return (
      <main className="min-h-screen grid place-items-center bg-zinc-100">
        <div className="p-8 text-zinc-700">
          No active template for {biz.name}.
        </div>
      </main>
    );
  }

  const customer = await api
    .getCustomerByPhone(scenario.phone, biz.id)
    .catch(() => null);

  return (
    <main className="min-h-screen bg-zinc-100 grid place-items-center py-10">
      <IncomingCallScreen
        phone={scenario.phone}
        business_id={biz.id}
        template_id={template.id}
        customer={customer}
        sampleAudioUrl={scenario.sample_audio_url}
      />
    </main>
  );
}
