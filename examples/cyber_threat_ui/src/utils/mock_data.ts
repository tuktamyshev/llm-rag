import type { NewsItem, Threat } from "./types";

export const mockThreats: Threat[] = [
  {
    id: "t1",
    title: "Ransomware campaign targeting logistics",
    severity: "critical",
    description: "Active phishing wave with payload loaders distributed via fake shipment updates."
  },
  {
    id: "t2",
    title: "Credential stuffing against partner portal",
    severity: "high",
    description: "Multiple failed logins from rotating residential proxies indicate automated abuse."
  },
  {
    id: "t3",
    title: "Suspicious C2 beacon in engineering VLAN",
    severity: "medium",
    description: "Periodic encrypted traffic to newly registered domains observed outside office hours."
  }
];

export const mockNews: NewsItem[] = [
  {
    id: "n1",
    title: "New zero-day in edge appliances",
    source: "CyberWire",
    text: "Researchers disclosed an unauthenticated RCE affecting several enterprise edge appliances."
  },
  {
    id: "n2",
    title: "Botnet resumes DDoS extortion",
    source: "DarkReading",
    text: "A known threat actor restarted extortion operations targeting financial organizations."
  },
  {
    id: "n3",
    title: "Stealer malware spread via cracked software",
    source: "BleepingComputer",
    text: "Campaign uses trojanized installers and exfiltrates browser data, cookies and tokens."
  }
];
