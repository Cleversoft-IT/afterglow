"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { api } from "@/lib/api";
import type { CustomerCard } from "@/lib/types";
import { BluePhoneButton } from "./BluePhoneButton";
import { CallerMemoryCard } from "./CallerMemoryCard";

interface Props {
  phone: string;
  business_id: string;
  template_id: string;
  customer: CustomerCard | null;
  sampleAudioUrl: string;
}

export function IncomingCallScreen({
  phone,
  business_id,
  template_id,
  customer,
  sampleAudioUrl,
}: Props) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function activateAiMode() {
    setBusy(true);
    setErr(null);
    try {
      const audioRes = await fetch(sampleAudioUrl);
      if (!audioRes.ok) throw new Error(`audio fetch ${audioRes.status}`);
      const blob = await audioRes.blob();
      const form = new FormData();
      form.append("audio", blob, "demo.wav");
      form.append("business_id", business_id);
      form.append("template_id", template_id);
      form.append("phone_e164", phone);

      const { call_id } = await api.submitAudio(form);
      router.push(`/dialer/post-call/${call_id}`);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
      setBusy(false);
    }
  }

  return (
    <div className="phone-shell mx-auto px-6 pt-14 pb-8 flex flex-col">
      <div className="text-[11px] uppercase tracking-widest text-zinc-300">
        Incoming call
      </div>
      <div className="mt-3 text-3xl font-semibold tracking-tight">{phone}</div>
      <div className="mt-1 text-sm text-zinc-400">
        {customer?.display_name ?? "Unknown caller"}
      </div>

      <div className="mt-6">
        <CallerMemoryCard customer={customer} phone={phone} />
      </div>

      <div className="flex-1" />

      <div className="grid grid-cols-3 gap-4 items-end">
        <ButtonRound color="bg-rose-500/90" label="Decline" />
        <div className="flex flex-col items-center gap-2">
          <BluePhoneButton size="lg" onPress={activateAiMode} busy={busy} />
          <div className="text-xs text-zinc-200 text-center">
            {busy ? "Listening…" : "AI memory mode"}
          </div>
        </div>
        <ButtonRound color="bg-emerald-500/90" label="Answer" />
      </div>

      {err && (
        <p className="mt-4 text-xs text-rose-300 text-center">Error: {err}</p>
      )}
    </div>
  );
}

function ButtonRound({ color, label }: { color: string; label: string }) {
  return (
    <div className="flex flex-col items-center gap-2">
      <div
        className={`${color} w-14 h-14 rounded-full grid place-items-center text-white shadow-lg`}
      >
        ●
      </div>
      <div className="text-xs text-zinc-300">{label}</div>
    </div>
  );
}
