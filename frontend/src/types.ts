export type Role = "manager" | "hr";
export interface Me { username: string; display_name: string; role: Role }

export interface Option { label: string; value: string | boolean | null }
export interface Message {
  role: "user" | "assistant";
  text: string;
  ask?: { fact: string; kind: "choices" | "dates"; options?: Option[] };
  show_result?: boolean;
}
export interface Case {
  id: string; owner: string; title: string; created_at: string;
  facts: Record<string, unknown>; messages: Message[]; has_result: boolean;
}
export interface CaseSummary { id: string; owner: string; title: string; created_at: string }

export type SourceType = "law" | "policy" | "hr_email" | "chat";
export interface SourceRef {
  id: string; title: string; type: SourceType; authority_label: string; date: string;
  owner: string | null; summary: string; raw_text?: string;
}
export type Status = "REQUIRED_LEGAL" | "NEW_SINCE" | "REQUIRED_PRACTICE" | "CONDITIONAL" | "NOT_NEEDED";
export interface Item {
  document: string; name: string; provided_by: "intern" | "school" | "manager";
  status: Status; status_label: string; reason: string;
  headline_source: SourceRef; supporting_sources: SourceRef[];
  condition: null | {
    fact: string; question: string; if_yes: string; if_no: string;
    ask_person: { id: string; name: string; role: string };
  };
  deadline: null | { date: string; label: string; flag: "ok" | "at_risk" | "overdue" };
}
export interface StaleWarning {
  source_id: string; title: string; type: SourceType; date: string; owner: string;
  missing_documents: string[]; explanation: string; summary: string; raw_text?: string;
}
export interface Excluded {
  source_id: string; title: string; type: SourceType; reason: string;
  mentions_documents: string[]; summary: string; raw_text?: string;
}
export interface Result {
  facts: Record<string, unknown>; items: Item[]; stale_warnings: StaleWarning[];
  excluded: Excluded[]; summary: string;
  counts: Record<string, number>;
}
export interface Turn { case: Case; new_messages: Message[]; result: Result | null }
export interface Flag {
  id: string; source_id: string; source_title: string; source_owner_name: string | null;
  flagged_by_name: string; note: string; created_at: string; resolved: boolean;
}
