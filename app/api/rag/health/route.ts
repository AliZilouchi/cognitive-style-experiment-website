import { proxyRagHealth } from "../_proxy";

export const dynamic = "force-dynamic";
export const maxDuration = 60;

export async function GET() {
  return proxyRagHealth();
}
