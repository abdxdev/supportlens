const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function throwIfError(res) {
  if (res.ok) return;
  let detail;
  try {
    const body = await res.json();
    detail = body?.detail ?? JSON.stringify(body);
  } catch {
    detail = await res.text();
  }
  const err = new Error(detail);
  err.status = res.status;
  throw err;
}

export async function sendChat(message) {
  const res = await fetch(`${BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  await throwIfError(res);
  return res.json(); // { response, categories, response_time_ms }
}

export async function saveTrace({ user_message, bot_response, response_time_ms, categories }) {
  const res = await fetch(`${BASE}/traces`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_message, bot_response, response_time_ms, categories }),
  });
  await throwIfError(res);
  return res.json();
}

export async function getTraces(category = null) {
  const url = category
    ? `${BASE}/traces?category=${encodeURIComponent(category)}`
    : `${BASE}/traces`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getAnalytics() {
  const res = await fetch(`${BASE}/analytics`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getHealth() {
  const res = await fetch(`${BASE}/health`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
