export type ChatRole = "user" | "assistant";

export interface ChatMessage {
  role: ChatRole;
  content: string;
}

export interface Citation {
  title: string;
  law_name: string;
  source_file: string;
  content: string;
  score: number;
}

export interface ChatResponse {
  answer: string;
  citations: Citation[];
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export async function sendQuestion(
  question: string,
  history: ChatMessage[]
): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE_URL}/api/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ question, history })
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || "请求失败，请稍后再试。");
  }

  return response.json();
}
