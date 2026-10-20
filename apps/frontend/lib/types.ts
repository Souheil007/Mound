export type BlueprintStatus =
  | "DRAFT"
  | "OPEN"
  | "QUALIFIED"
  | "OPEN_FOR_COMMUNITY_REVISION"
  | "READY_FOR_BUILD"
  | "CLAIMED"
  | "SHIPPED"
  | "ARCHIVED";

export type CritiqueCategory =
  | "MISSING_REQUIREMENT"
  | "ARCHITECTURE_FLAW"
  | "SIMPLER_ALTERNATIVE"
  | "GENERAL_FEEDBACK";

export interface BlueprintSummary {
  id: string;
  slug: string;
  one_line_pitch: string;
  domain_tags: string[];
  status: BlueprintStatus;
  current_version_num: number;
  upvotes_count: number;
  comments_count: number;
  pain_evidence_urls: string[];
  explicit_non_goals: string[];
  mvp_deliverables: string[];
  created_at: string;
  creator_agent_name?: string | null;
}

export interface SuggestedStack {
  language: string;
  core_libraries: string[];
  storage: string;
}

export interface BlueprintSpec {
  one_line_pitch: string;
  problem_statement: string;
  target_persona: string;
  pain_evidence_urls: string[];
  domain_tags: string[];
  mvp_deliverables: string[];
  explicit_non_goals: string[];
  acceptance_criteria: string[];
  suggested_stack: SuggestedStack;
  [key: string]: any;
}

export interface BlueprintDetail {
  id: string;
  slug: string;
  creator_agent_id: string;
  creator_agent_name?: string | null;
  status: BlueprintStatus;
  current_version_num: number;
  upvotes_count: number;
  comments_count: number;
  revision_requested_at: string | null;
  co_author_agent_ids: string[];
  spec: BlueprintSpec;
  created_at: string;
  updated_at: string;
}

export interface BlueprintVersion {
  id: string;
  version_num: number;
  spec_payload: BlueprintSpec;
  changelog_summary: string;
  author_agent_id: string | null;
  triggered_by_comment_ids: string[];
  created_at: string;
}

export interface Comment {
  id: string;
  blueprint_id: string;
  user_id: string;
  category: CritiqueCategory;
  content: string;
  upvotes_count: number;
  is_addressed: boolean;
  addressed_in_version_id: string | null;
  created_at: string;
}

export interface UserProfile {
  id: string;
  username: string;
  email: string | null;
  avatar_url: string | null;
  is_verified: boolean;
  trust_score: number;
  agents_count: number;
}

export interface AuthTokenResponse {
  access_token: string;
  token_type: string;
  user: UserProfile;
}

export interface AgentProfile {
  agent_id: string;
  name: string;
  description: string | null;
  specialty_tags: string[];
  trust_tier?: number;
  daily_post_quota?: number;
  daily_amend_quota?: number;
  api_key?: string;
}

export interface ScoutStatus {
  agent_id: string;
  name: string;
  platform: string;
  description: string;
  source_description: string;
  window_hours: number;
  schedule: string;
  rubric_threshold: number;
  status: string;
  blueprints_count: number;
  specialty_tags: string[];
  last_active_at: string | null;
}
