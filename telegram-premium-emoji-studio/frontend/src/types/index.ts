// Shared TypeScript types mirroring the backend schemas.

export type Lang = "uz" | "ru" | "en";
export type ProductKind = "name" | "logo" | "logo2" | "logo3" | "pf";
export type PackKind = "emoji" | "sticker";

export interface UserPublic {
  id: number;
  username: string | null;
  first_name: string | null;
  last_name: string | null;
  full_name: string;
  language: Lang;
  is_premium: boolean;
  photo_url: string | null;
  credits: number;
  free_access: boolean;
  is_admin: boolean;
  packs_created: number;
  stars_spent: number;
}

export interface AuthResponse {
  token: string;
  user: UserPublic;
}

export interface TemplateItem {
  id: string;
  number: number | null;
  label: string;
  kind: string;
  custom_emoji_id: string | null;
}

export interface TemplateListResponse {
  kind: string;
  total: number;
  page: number;
  page_size: number;
  items: TemplateItem[];
}

export interface FontItem {
  key: string;
  label: string;
}

export interface PreviewResponse {
  lottie: Record<string, unknown>;
  kind: string;
  template: string;
  watermark: boolean;
}

export interface OrderPublic {
  id: number;
  kind: string;
  pack_kind: string;
  template_selection: string;
  item_count: number;
  unit_price: number;
  total_price: number;
  payment_method: string | null;
  status: string;
  pack_url: string | null;
  pack_title: string | null;
  error_message: string | null;
  created_at: string | null;
}

export interface OrderCheckout {
  order_id: number;
  unit_price: number;
  total_price: number;
  item_count: number;
  currency: string;
  can_use_credit: boolean;
  credits_available: number;
  is_free_user: boolean;
  invoice_link: string | null;
}

export interface ChannelPublic {
  id: number;
  username: string;
  title: string | null;
  enabled: boolean;
  url: string;
}

export interface SettingsPublic {
  support_contact: string;
  required_channels: ChannelPublic[];
  prices: Record<string, number>;
  gift_min_amount: number;
  gift_max_amount: number;
  name_max_len: number;
  pf_max_len: number;
}

export interface SubscriptionStatus {
  subscribed: boolean;
  channels: ChannelPublic[];
}

export interface ReferralInfo {
  link: string;
  invited_count: number;
  successful_count: number;
  earned_credits: number;
}

export interface CreditTxn {
  amount: number;
  reason: string;
  balance_after: number;
  created_at: string | null;
}

export interface CreditBalance {
  credits: number;
  transactions: CreditTxn[];
}

// Admin
export interface AdminOverview {
  total_users: number;
  active_users_7d: number;
  total_generations: number;
  total_packs: number;
  stars_revenue: number;
  credits_consumed: number;
  recent_orders: OrderPublic[];
}

export interface AdminUserRow {
  id: number;
  username: string | null;
  created_at: string | null;
  packs_created: number;
  stars_spent: number;
  credits: number;
  free_access: boolean;
}

export interface AdminStatistics {
  top_by_packs: { id: number; username: string | null; packs: number }[];
  top_by_stars: { id: number; username: string | null; stars: number }[];
  popular_templates: { selection: string; count: number }[];
  daily_activity: { date: string; count: number }[];
}
