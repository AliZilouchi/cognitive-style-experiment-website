// These browser-facing values are intentionally public. Override them in
// .env.local when connecting this copy to a different Supabase project.
export const SUPABASE_URL =
  process.env.NEXT_PUBLIC_SUPABASE_URL || "https://fqtczhahhtotsixvdlgm.supabase.co";

export const SUPABASE_KEY =
  process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY ||
  "sb_publishable_pcHSrMzWKw1LNLe3VKahsw_2X7J1t29";
