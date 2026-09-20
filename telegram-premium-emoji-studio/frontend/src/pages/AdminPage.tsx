import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { adminApi } from "@/api/endpoints";
import { useI18n } from "@/i18n";
import { useAppStore } from "@/store/appStore";
import { Skeleton, Spinner, EmptyState } from "@/components/ui";
import { haptic } from "@/lib/telegram";

type Tab = "overview" | "users" | "prices" | "channels" | "support" | "stats" | "payments" | "refunds";

export default function AdminPage() {
  const { t } = useI18n();
  const isAdmin = useAppStore((s) => s.user?.is_admin);
  const [tab, setTab] = useState<Tab>("overview");

  if (!isAdmin) {
    return <EmptyState title="403" hint="Faqat administratorlar uchun" />;
  }

  const tabs: { key: Tab; label: string }[] = [
    { key: "overview", label: t("admin_overview") },
    { key: "users", label: t("admin_users") },
    { key: "prices", label: t("admin_prices") },
    { key: "channels", label: t("admin_channels") },
    { key: "support", label: t("admin_support") },
    { key: "stats", label: t("admin_stats") },
    { key: "payments", label: t("admin_payments") },
    { key: "refunds", label: t("admin_refunds") },
  ];

  return (
    <div className="px-4 pt-5">
      <h1 className="text-2xl font-extrabold mb-4">🛡️ Admin</h1>
      <div className="flex gap-2 overflow-x-auto no-scrollbar pb-2 mb-4">
        {tabs.map((tb) => (
          <button
            key={tb.key}
            onClick={() => {
              haptic("select");
              setTab(tb.key);
            }}
            className={`chip whitespace-nowrap border ${tab === tb.key ? "border-brand-500 bg-brand-500/10 text-brand-400" : "border-tg-border"}`}
          >
            {tb.label}
          </button>
        ))}
      </div>

      {tab === "overview" && <Overview />}
      {tab === "users" && <Users />}
      {tab === "prices" && <Prices />}
      {tab === "channels" && <Channels />}
      {tab === "support" && <Support />}
      {tab === "stats" && <Stats />}
      {tab === "payments" && <Payments />}
      {tab === "refunds" && <Refunds />}
    </div>
  );
}

function Overview() {
  const { t } = useI18n();
  const { data, isLoading } = useQuery({ queryKey: ["admin", "overview"], queryFn: adminApi.overview });
  if (isLoading) return <Skeleton className="h-40" />;
  if (!data) return null;
  const cards = [
    { label: t("total_users"), value: data.total_users },
    { label: t("active_users"), value: data.active_users_7d },
    { label: t("total_gen"), value: data.total_generations },
    { label: t("total_packs"), value: data.total_packs },
    { label: t("revenue"), value: data.stars_revenue },
    { label: "Credits used", value: data.credits_consumed },
  ];
  return (
    <div>
      <div className="grid grid-cols-2 gap-3 mb-5">
        {cards.map((c) => (
          <div key={c.label} className="card p-4">
            <p className="text-2xl font-extrabold text-brand-400">{c.value}</p>
            <p className="text-xs text-tg-hint mt-1">{c.label}</p>
          </div>
        ))}
      </div>
      <h3 className="font-bold mb-2 text-sm">Recent orders</h3>
      <div className="space-y-2">
        {data.recent_orders.map((o) => (
          <div key={o.id} className="card p-3 flex justify-between text-sm">
            <span>#{o.id} {o.kind}</span>
            <span className="text-tg-hint">{o.status} • {o.total_price}⭐</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function Users() {
  const { t } = useI18n();
  const qc = useQueryClient();
  const [q, setQ] = useState("");
  const { data, isLoading } = useQuery({ queryKey: ["admin", "users", q], queryFn: () => adminApi.users(q || undefined) });

  const toggleFree = async (id: number, grant: boolean) => {
    await adminApi.setFreeAccess(id, grant);
    qc.invalidateQueries({ queryKey: ["admin", "users"] });
  };
  const grantCredit = async (id: number) => {
    await adminApi.grantCredit(id, 1);
    qc.invalidateQueries({ queryKey: ["admin", "users"] });
  };

  return (
    <div>
      <input className="input mb-3" placeholder="@username yoki ID" value={q} onChange={(e) => setQ(e.target.value)} />
      {isLoading ? (
        <Skeleton className="h-40" />
      ) : (
        <div className="space-y-2">
          {data?.map((u) => (
            <div key={u.id} className="card p-3">
              <div className="flex justify-between">
                <div>
                  <p className="font-semibold text-sm">{u.username ? `@${u.username}` : u.id}</p>
                  <p className="text-xs text-tg-hint">🗂️ {u.packs_created} • ⭐ {u.stars_spent} • 🎁 {u.credits}</p>
                </div>
                {u.free_access && <span className="chip border border-emerald-500/40 text-emerald-400 h-fit">FREE</span>}
              </div>
              <div className="grid grid-cols-2 gap-2 mt-2">
                <button className="btn-ghost !py-2 text-xs" onClick={() => toggleFree(u.id, !u.free_access)}>
                  {u.free_access ? t("revoke") : t("grant")} free
                </button>
                <button className="btn-ghost !py-2 text-xs" onClick={() => grantCredit(u.id)}>
                  +1 🎁
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function Prices() {
  const { t } = useI18n();
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["admin", "prices"], queryFn: adminApi.prices });
  const [edits, setEdits] = useState<Record<string, number>>({});
  const [saving, setSaving] = useState<string | null>(null);

  const save = async (kind: string) => {
    const val = edits[kind] ?? data?.[kind];
    if (val == null) return;
    setSaving(kind);
    await adminApi.setPrice(kind, val);
    await qc.invalidateQueries({ queryKey: ["admin", "prices"] });
    await qc.invalidateQueries({ queryKey: ["settings"] });
    setSaving(null);
  };

  if (isLoading) return <Skeleton className="h-40" />;
  const kinds = ["name", "logo", "logo2", "logo3", "pf", "code"];
  return (
    <div className="space-y-2">
      {kinds.map((k) => (
        <div key={k} className="card p-3 flex items-center gap-3">
          <span className="font-semibold text-sm w-16">{k}</span>
          <input
            type="number"
            className="input flex-1 !py-2"
            defaultValue={data?.[k]}
            onChange={(e) => setEdits((s) => ({ ...s, [k]: Number(e.target.value) }))}
          />
          <button className="btn-primary !py-2 !px-4" onClick={() => save(k)}>
            {saving === k ? <Spinner className="h-4 w-4" /> : t("save")}
          </button>
        </div>
      ))}
    </div>
  );
}

function Channels() {
  const { t } = useI18n();
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["admin", "channels"], queryFn: adminApi.channels });
  const [username, setUsername] = useState("");

  const add = async () => {
    if (!username.trim()) return;
    await adminApi.addChannel(username.trim());
    setUsername("");
    qc.invalidateQueries({ queryKey: ["admin", "channels"] });
  };
  const remove = async (id: number) => {
    await adminApi.deleteChannel(id);
    qc.invalidateQueries({ queryKey: ["admin", "channels"] });
  };
  const toggle = async (id: number, enabled: boolean) => {
    await adminApi.toggleChannel(id, enabled);
    qc.invalidateQueries({ queryKey: ["admin", "channels"] });
  };

  return (
    <div>
      <div className="flex gap-2 mb-3">
        <input className="input flex-1" placeholder="@channel" value={username} onChange={(e) => setUsername(e.target.value)} />
        <button className="btn-primary" onClick={add}>{t("add")}</button>
      </div>
      {isLoading ? (
        <Skeleton className="h-24" />
      ) : (
        <div className="space-y-2">
          {data?.map((c) => (
            <div key={c.id} className="card p-3 flex items-center justify-between">
              <span className="text-sm font-medium">{c.username}</span>
              <div className="flex gap-2">
                <button className="btn-ghost !py-1.5 !px-3 text-xs" onClick={() => toggle(c.id, !c.enabled)}>
                  {c.enabled ? "ON" : "OFF"}
                </button>
                <button className="btn-ghost !py-1.5 !px-3 text-xs" onClick={() => remove(c.id)}>
                  {t("remove")}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function Support() {
  const { t } = useI18n();
  const qc = useQueryClient();
  const [contact, setContact] = useState("");
  const [saved, setSaved] = useState(false);
  const save = async () => {
    if (!contact.trim()) return;
    await adminApi.setSupport(contact.trim());
    qc.invalidateQueries({ queryKey: ["settings"] });
    setSaved(true);
    setTimeout(() => setSaved(false), 1500);
  };
  return (
    <div className="card p-4">
      <p className="text-sm font-semibold mb-2">{t("support_contact")}</p>
      <input className="input mb-3" placeholder="@support" value={contact} onChange={(e) => setContact(e.target.value)} />
      <button className="btn-primary w-full" onClick={save}>{saved ? "✓" : t("save")}</button>
    </div>
  );
}

function Stats() {
  const { data, isLoading } = useQuery({ queryKey: ["admin", "stats"], queryFn: adminApi.statistics });
  if (isLoading) return <Skeleton className="h-40" />;
  if (!data) return null;
  return (
    <div className="space-y-4">
      <div className="card p-4">
        <h3 className="font-bold text-sm mb-2">Top by packs</h3>
        {data.top_by_packs.map((u) => (
          <div key={u.id} className="flex justify-between text-sm py-1">
            <span>{u.username ? `@${u.username}` : u.id}</span>
            <span className="text-tg-hint">{u.packs}</span>
          </div>
        ))}
      </div>
      <div className="card p-4">
        <h3 className="font-bold text-sm mb-2">Top by stars</h3>
        {data.top_by_stars.map((u) => (
          <div key={u.id} className="flex justify-between text-sm py-1">
            <span>{u.username ? `@${u.username}` : u.id}</span>
            <span className="text-tg-hint">{u.stars} ⭐</span>
          </div>
        ))}
      </div>
      <div className="card p-4">
        <h3 className="font-bold text-sm mb-2">Daily activity (14d)</h3>
        <div className="flex items-end gap-1 h-24">
          {data.daily_activity.map((d) => {
            const max = Math.max(...data.daily_activity.map((x) => x.count), 1);
            return (
              <div key={d.date} className="flex-1 bg-brand-500/70 rounded-t" style={{ height: `${(d.count / max) * 100}%` }} title={`${d.date}: ${d.count}`} />
            );
          })}
        </div>
      </div>
    </div>
  );
}

function Payments() {
  const { data, isLoading } = useQuery({ queryKey: ["admin", "payments"], queryFn: adminApi.payments });
  if (isLoading) return <Skeleton className="h-40" />;
  return (
    <div className="space-y-2">
      {(data as Array<Record<string, unknown>>)?.map((p) => (
        <div key={String(p.id)} className="card p-3 text-sm flex justify-between">
          <span>#{String(p.id)} {String(p.purpose)}</span>
          <span className="text-tg-hint">{String(p.amount)}⭐ • {String(p.status)}</span>
        </div>
      ))}
    </div>
  );
}

function Refunds() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["admin", "refunds"], queryFn: adminApi.refunds });
  const perform = async (id: number) => {
    await adminApi.performRefund(id);
    qc.invalidateQueries({ queryKey: ["admin", "refunds"] });
  };
  if (isLoading) return <Skeleton className="h-40" />;
  return (
    <div className="space-y-2">
      {(data as Array<Record<string, unknown>>)?.map((r) => (
        <div key={String(r.id)} className="card p-3 text-sm flex items-center justify-between">
          <div>
            <p>#{String(r.id)} • user {String(r.user_id)}</p>
            <p className="text-tg-hint text-xs">{String(r.amount)}⭐ • {String(r.status)}</p>
          </div>
          {r.status !== "done" && (
            <button className="btn-ghost !py-1.5 !px-3 text-xs" onClick={() => perform(Number(r.id))}>
              Refund
            </button>
          )}
        </div>
      ))}
    </div>
  );
}
