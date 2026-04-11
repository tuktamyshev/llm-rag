export type Threat = {
  id: string;
  title: string;
  severity: "low" | "medium" | "high" | "critical";
  description: string;
};

export type NewsItem = {
  id: string;
  title: string;
  source: string;
  text: string;
};

export type ChatRole = "user" | "assistant";

export type ChatEntry = {
  id: string;
  role: ChatRole;
  text: string;
  sources?: string[];
};
