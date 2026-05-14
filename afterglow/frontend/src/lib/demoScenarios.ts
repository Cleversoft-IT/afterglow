// Demo scenarios mapped to a slug used in /dialer/incoming/[callId].
// On day 2-3 these will be expanded with the real Speechmatics-generated audio.

export interface DemoScenario {
  slug: string;
  phone: string;
  business_domain: "restaurant" | "dentist" | "bodyshop";
  sample_audio_url: string;
  label: string;
}

export const DEMO_SCENARIOS: Record<string, DemoScenario> = {
  "demo-restaurant-known": {
    slug: "demo-restaurant-known",
    phone: "+393331112233",
    business_domain: "restaurant",
    sample_audio_url: "/audio-samples/silence.wav",
    label: "Restaurant — returning customer (IT)",
  },
  "demo-restaurant-new": {
    slug: "demo-restaurant-new",
    phone: "+393999998888",
    business_domain: "restaurant",
    sample_audio_url: "/audio-samples/silence.wav",
    label: "Restaurant — new customer (IT)",
  },
  "demo-dentist": {
    slug: "demo-dentist",
    phone: "+393339991122",
    business_domain: "dentist",
    sample_audio_url: "/audio-samples/silence.wav",
    label: "Dental clinic — appointment (IT)",
  },
  "demo-bodyshop": {
    slug: "demo-bodyshop",
    phone: "+393338883344",
    business_domain: "bodyshop",
    sample_audio_url: "/audio-samples/silence.wav",
    label: "Body shop — damage quote (IT)",
  },
};

export function listScenarios(): DemoScenario[] {
  return Object.values(DEMO_SCENARIOS);
}

export function getScenario(slug: string): DemoScenario | null {
  return DEMO_SCENARIOS[slug] ?? null;
}
