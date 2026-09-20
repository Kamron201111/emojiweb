// Typed endpoint functions grouped by domain.
import { api } from "./client";
import type {
  AdminOverview,
  AdminStatistics,
  AdminUserRow,
  AuthResponse,
  ChannelPublic,
  CreditBalance,
  Lang,
  OrderCheckout,
  OrderPublic,
  PackKind,
  PreviewResponse,
  ProductKind,
  ReferralInfo,
  SettingsPublic,
  SubscriptionStatus,
  TemplateListResponse,
  UserPublic,
  FontItem,
} from "@/types";

export const authApi = {
  login: (init_data: string) =>
    api.post<AuthResponse>("/auth", { init_data }, { auth: false }),
};

export const meApi = {
  get: () => api.get<UserPublic>("/me"),
  setLanguage: (language: Lang) => api.put<UserPublic>("/me/language", { language }),
  credits: () => api.get<CreditBalance>("/credits"),
};

export const catalogApi = {
  templates: (kind: string, page = 1, page_size = 24) =>
    api.get<TemplateListResponse>(`/templates/${kind}?page=${page}&page_size=${page_size}`),
  count: (kind: string) => api.get<{ kind: string; total: number }>(`/templates/${kind}/count`),
  fonts: (profile = false) => api.get<FontItem[]>(`/fonts?profile=${profile}`),
};

export interface PreviewInput {
  kind: ProductKind;
  text: string;
  template: string;
  outer_hex?: string | null;
  inner_hex?: string | null;
  color_hex?: string | null;
  font_key?: string | null;
}

export const renderApi = {
  preview: (input: PreviewInput) => api.post<PreviewResponse>("/render/preview", input),
};

export interface OrderInput {
  kind: ProductKind;
  pack_kind: PackKind;
  text: string;
  templates: string;
  outer_hex?: string | null;
  inner_hex?: string | null;
  color_hex?: string | null;
  font_key?: string | null;
  pack_title?: string;
  existing_pack_nick?: string | null;
  idempotency_key?: string;
}

export const ordersApi = {
  create: (input: OrderInput) => api.post<OrderPublic>("/orders", input),
  checkout: (orderId: number) => api.post<OrderCheckout>(`/orders/${orderId}/checkout`),
  payWithCredit: (orderId: number) =>
    api.post<OrderPublic>("/orders/pay-credit", { order_id: orderId }),
  list: () => api.get<OrderPublic[]>("/orders"),
  get: (id: number) => api.get<OrderPublic>(`/orders/${id}`),
};

export const paymentsApi = {
  gift: (amount: number) => api.post<{ invoice_link: string | null; amount: number }>("/payments/gift", { amount }),
};

export const referralsApi = {
  get: () => api.get<ReferralInfo>("/referrals"),
};

export const settingsApi = {
  get: () => api.get<SettingsPublic>("/settings"),
  subscription: () => api.get<SubscriptionStatus>("/settings/subscription"),
};

export const adminApi = {
  overview: () => api.get<AdminOverview>("/admin/overview"),
  users: (q?: string) => api.get<AdminUserRow[]>(`/admin/users${q ? `?q=${encodeURIComponent(q)}` : ""}`),
  setFreeAccess: (user_id: number, grant: boolean) =>
    api.post("/admin/users/free-access", { user_id, grant }),
  grantCredit: (user_id: number, amount = 1) =>
    api.post(`/admin/users/${user_id}/grant-credit?amount=${amount}`),
  prices: () => api.get<Record<string, number>>("/admin/prices"),
  setPrice: (kind: string, stars: number) => api.put("/admin/prices", { kind, stars }),
  channels: () => api.get<ChannelPublic[]>("/admin/channels"),
  addChannel: (username: string, title?: string) => api.post<ChannelPublic>("/admin/channels", { username, title }),
  deleteChannel: (id: number) => api.del(`/admin/channels/${id}`),
  toggleChannel: (id: number, enabled: boolean) => api.put(`/admin/channels/${id}/toggle?enabled=${enabled}`),
  setSupport: (contact: string) => api.put("/admin/support", { contact }),
  statistics: () => api.get<AdminStatistics>("/admin/statistics"),
  payments: () => api.get<Record<string, unknown>[]>("/admin/payments"),
  refunds: () => api.get<Record<string, unknown>[]>("/admin/refunds"),
  performRefund: (refund_id: number) => api.post("/admin/refunds/perform", { refund_id }),
};
