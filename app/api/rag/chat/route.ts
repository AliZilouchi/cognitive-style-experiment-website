import { proxyRagChat } from "../_proxy";

export const dynamic = "force-dynamic";
export const maxDuration = 90;

export async function POST(request: Request) {
  return proxyRagChat(request);
}
