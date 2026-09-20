import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ordersApi, type OrderInput } from "@/api/endpoints";
import type { OrderCheckout, OrderPublic } from "@/types";
import { Sheet, Spinner } from "./ui";
import { useI18n } from "@/i18n";
import { useAppStore } from "@/store/appStore";
import { haptic, openInvoice } from "@/lib/telegram";
import { ApiError } from "@/api/client";

type Phase = "summary" | "processing" | "waiting_payment" | "generating" | "done" | "error";

export function CheckoutSheet({
  open,
  onClose,
  buildInput,
  itemCount,
}: {
  open: boolean;
  onClose: () => void;
  buildInput: () => OrderInput;
  itemCount: number;
}) {
  const { t } = useI18n();
  const qc = useQueryClient();
  const { patchCredits } = useAppStore();
  const [phase, setPhase] = useState<Phase>("summary");
  const [checkout, setCheckout] = useState<OrderCheckout | null>(null);
  const [order, setOrder] = useState<OrderPublic | null>(null);
  const [error, setError] = useState("");

  const reset = () => {
    setPhase("summary");
    setCheckout(null);
    setOrder(null);
    setError("");
  };

  const prepare = async () => {
    setPhase("processing");
    setError("");
    try {
      const input = buildInput();
      if (!input.idempotency_key) input.idempotency_key = crypto.randomUUID();
      const created = await ordersApi.create(input);
      const co = await ordersApi.checkout(created.id);
      setOrder(created);
      setCheckout(co);
      setPhase("summary");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t("error"));
      setPhase("error");
    }
  };

  const finalize = async (o: OrderPublic) => {
    setOrder(o);
    if (o.status === "completed") {
      patchCredits(0);
      qc.invalidateQueries({ queryKey: ["orders"] });
      qc.invalidateQueries({ queryKey: ["me"] });
      setPhase("done");
      haptic("success");
    } else if (o.status === "failed" || o.status === "cancelled") {
      setError(o.error_message || t("error"));
      setPhase("error");
      haptic("error");
    }
  };

  const payCredit = async () => {
    if (!order) return;
    setPhase("generating");
    try {
      const o = await ordersApi.payWithCredit(order.id);
      if (o.payment_method === "credit") patchCredits(-1);
      await finalize(o);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t("error"));
      setPhase("error");
      haptic("error");
    }
  };

  const payStars = async () => {
    if (!checkout?.invoice_link) {
      setError("Invoice link not available");
      setPhase("error");
      return;
    }
    setPhase("waiting_payment");
    const status = await openInvoice(checkout.invoice_link);
    if (status === "paid") {
      // The backend fulfills via webhook; poll the order for completion.
      setPhase("generating");
      pollOrder(order!.id);
    } else if (status === "cancelled" || status === "failed") {
      setPhase("summary");
    } else {
      setPhase("summary");
    }
  };

  const pollOrder = async (id: number, tries = 0) => {
    try {
      const o = await ordersApi.get(id);
      if (o.status === "completed" || o.status === "failed" || o.status === "cancelled") {
        await finalize(o);
        return;
      }
    } catch {
      /* ignore */
    }
    if (tries < 30) setTimeout(() => pollOrder(id, tries + 1), 2000);
    else {
      setError("Timeout — /packs bo'limini tekshiring");
      setPhase("error");
    }
  };

  // Kick off preparation when opened.
  if (open && phase === "summary" && !checkout && !error) {
    prepare();
  }

  return (
    <Sheet
      open={open}
      onClose={() => {
        if (phase === "generating" || phase === "waiting_payment") return;
        reset();
        onClose();
      }}
      title={phase === "done" ? t("success_title") : t("order_summary")}
    >
      {phase === "processing" && (
        <div className="py-10 flex flex-col items-center gap-3">
          <Spinner className="h-8 w-8 text-brand-500" />
          <p className="text-tg-hint text-sm">{t("loading")}</p>
        </div>
      )}

      {(phase === "summary" || phase === "waiting_payment") && checkout && (
        <div className="space-y-4">
          <div className="card p-4 bg-tg-card-2 space-y-2">
            <Row label={t("total")} value={`${itemCount} × ${checkout.unit_price} ⭐`} />
            <div className="h-px bg-tg-border" />
            <Row label={t("total")} value={`${checkout.total_price} ⭐`} strong />
          </div>

          {checkout.is_free_user ? (
            <button className="btn-primary w-full" onClick={payCredit}>
              {t("free_generate")}
            </button>
          ) : (
            <>
              {checkout.can_use_credit && (
                <button className="btn-gold w-full" onClick={payCredit}>
                  🎁 {t("use_credit")} ({t("credits_left", { n: checkout.credits_available })})
                </button>
              )}
              <button className="btn-primary w-full" onClick={payStars} disabled={!checkout.invoice_link}>
                {t("pay_stars", { n: checkout.total_price })}
              </button>
              {!checkout.invoice_link && (
                <p className="text-xs text-center text-tg-hint">
                  ⚠️ Invoice yaratilmadi — BOT_TOKEN / server sozlamalarini tekshiring
                </p>
              )}
            </>
          )}
        </div>
      )}

      {phase === "generating" && (
        <div className="py-10 flex flex-col items-center gap-3">
          <Spinner className="h-10 w-10 text-brand-500" />
          <p className="font-semibold">{t("rendering")}</p>
          <p className="text-tg-hint text-sm">{t("generating", { c: "•", t: itemCount })}</p>
        </div>
      )}

      {phase === "done" && order && (
        <div className="py-4 flex flex-col items-center gap-3 text-center animate-scale-in">
          <div className="text-6xl">🎉</div>
          <p className="font-bold text-lg">{t("pack_created")}</p>
          <p className="text-tg-hint text-sm">{t("items_generated", { n: order.item_count })}</p>
          {order.pack_url && (
            <a className="btn-primary w-full" href={order.pack_url} target="_blank" rel="noreferrer">
              {t("open_telegram")} ↗
            </a>
          )}
          <button
            className="btn-ghost w-full"
            onClick={() => {
              reset();
              onClose();
            }}
          >
            {t("create_another")}
          </button>
        </div>
      )}

      {phase === "error" && (
        <div className="py-6 flex flex-col items-center gap-3 text-center">
          <div className="text-5xl">⚠️</div>
          <p className="font-semibold max-w-xs">{error}</p>
          <button className="btn-ghost w-full" onClick={reset}>
            {t("retry")}
          </button>
        </div>
      )}
    </Sheet>
  );
}

function Row({ label, value, strong }: { label: string; value: string; strong?: boolean }) {
  return (
    <div className="flex items-center justify-between">
      <span className={strong ? "font-bold" : "text-tg-hint text-sm"}>{label}</span>
      <span className={strong ? "font-extrabold text-brand-400" : "font-medium"}>{value}</span>
    </div>
  );
}
