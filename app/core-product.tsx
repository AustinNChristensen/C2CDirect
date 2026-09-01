"use client";
import { useEffect, useMemo, useState } from "react";
import type { ClipboardEvent, KeyboardEvent } from "react";

type QualityLane = "direct_prime" | "needs_verification" | "low_quality";
type Job = {
  id: string;
  company: string;
  title: string;
  description: string;
  rateMin: number;
  rateMax: number;
  location: string;
  term: string;
  score: number;
  c2c: "confirmed" | "likely" | "unknown" | "rejected";
  recruiterEmail?: string | null;
  tags: string[];
  fresh: string;
  why: string[];
  gaps: string[];
  source: string;
  vendor: string;
  status: string;
  qualityLane: QualityLane;
  authority: number;
  confidence: number;
  completeness: number;
  layers: string;
  observations: number;
  url: string | null;
};
type ApiJob = {
  id: string;
  company: string;
  title: string;
  description: string | null;
  rate_min: number | null;
  rate_max: number | null;
  contract_duration: string | null;
  engagement_type: string | null;
  location: string | null;
  fit_score: number;
  c2c_status: Job["c2c"];
  status: string;
  created_at: string;
  quality_lane: QualityLane;
  reasons: string[];
  risks: string[];
  provider_name: string | null;
  end_client_name: string | null;
  source_authority: number;
  provenance_confidence: number | string;
  provenance_completeness: number | string;
  vendor_layer_min: number;
  vendor_layer_max: number;
  observation_count: number | string;
  canonical_url: string | null;
  source_url: string | null;
};
type EmailConnection = {
  id: string;
  provider: "gmail" | "microsoft";
  mailbox_address: string | null;
  status: string;
  last_synced_at: string | null;
};
type EmailOAuthStatus = {
  redirect_base: string;
  providers: {
    gmail: { configured: boolean };
    microsoft: { configured: boolean };
  };
};
type CandidateProfile = {
  display_name: string;
  headline: string;
  bio: string;
  target_roles: string[];
  seniority_levels: string[];
  min_rate: number;
  target_rate: number;
  locations: string[];
  work_modes: string[];
  core_skills: string[];
  ai_skills: string[];
  require_c2c: boolean;
  onboarding_completed: boolean;
  resume: null | {
    file_name: string;
    content_type: string;
    size_bytes: number;
    uploaded_at: string;
  };
};
type JobDecision = {
  id: string;
  outcome: "not_interested" | "denied";
  reason_code: string;
  notes: string | null;
  created_at: string;
};
type ControlRoomData = {
  runtime: {
    provider: string;
    model: string;
    mode: string;
    base_url_configured: boolean;
    api_key_configured: boolean;
    input_cost_per_million: number;
    output_cost_per_million: number;
  };
  policy: {
    daily_limit_usd: number;
    per_run_limit_usd: number;
    max_total_tokens: number;
    max_graph_steps: number;
    max_retries: number;
    require_approval_above_usd: number;
  };
  today_spend: number;
  month_spend: number;
  average_cost: number;
  input_tokens: number;
  output_tokens: number;
  today_runs: number;
  month_runs: number;
  failed_runs: number;
  daily: { date: string; spend: number; runs: number }[];
  recent_runs: {
    id: string;
    operation: string;
    provider: string;
    model: string;
    status: string;
    input_tokens: number;
    output_tokens: number;
    cost_usd: number;
    created_at: string;
  }[];
};
type ModelConnection = {
  provider: "deterministic" | "openai_compatible";
  base_url: string;
  model: string;
  mode: string;
  api_key_configured: boolean;
  input_cost_per_million: number;
  output_cost_per_million: number;
  updated_at?: string | null;
};
type WebSearchConnection = {
  provider: "disabled" | "searxng" | "tavily" | "brave";
  base_url: string;
  api_key_configured: boolean;
  configured: boolean;
  updated_at?: string | null;
};
type AcquisitionRun = {
  id: string;
  kind: string;
  status: "queued" | "running" | "completed" | "failed" | "cancelled";
  result_json: Record<string, number | string> | null;
  error_code: string | null;
  attempts: number;
  cancel_requested?: boolean;
};
type SourceTarget = {
  adapter: string;
  slug: string;
  organization_name: string;
  enabled: boolean;
  priority: number;
};
type ImportJob = {
  source: string;
  source_url?: string | null;
  title: string;
  company: string;
  description: string;
  location?: string;
  rate_min?: number | null;
  rate_max?: number | null;
  contract_duration?: string | null;
  engagement_type?: string | null;
  recruiter_email?: string | null;
};
const DECISION_REASONS = [
  ["c2c_not_accepted", "C2C not accepted"],
  ["rate_below_floor", "Rate below floor"],
  ["skill_mismatch", "Skill mismatch"],
  ["location_mismatch", "Location or work setup"],
  ["seniority_mismatch", "Seniority mismatch"],
  ["vendor_chain_concern", "Vendor-chain concern"],
  ["role_not_compelling", "Role is not compelling"],
  ["expired_or_filled", "Expired or already filled"],
  ["denied_by_client", "Denied by client or vendor"],
  ["no_response", "No response"],
  ["timing", "Timing changed"],
  ["other", "Other"],
] as const;
const DEFAULT_PROFILE: CandidateProfile = {
  display_name: "Independent Engineer",
  headline: "Independent consultant",
  bio: "",
  target_roles: [],
  seniority_levels: [],
  min_rate: 75,
  target_rate: 100,
  locations: [],
  work_modes: ["remote"],
  core_skills: [],
  ai_skills: [],
  require_c2c: true,
  onboarding_completed: false,
  resume: null,
};
const PROJECTS = [
  {
    title: "Agentic recruiter intelligence workflow",
    match: 4,
    stack: "FastAPI · Pydantic · LangGraph · MCP",
    next: "Implement human approval + durable checkpoints",
    progress: 68,
  },
  {
    title: "Evidence-first RAG job matcher",
    match: 3,
    stack: "Python · pgvector · hybrid search · evals",
    next: "Add reranker and grounded citations",
    progress: 42,
  },
  {
    title: "AI opportunity control plane",
    match: 3,
    stack: "Next.js · tracing · cost controls · n8n",
    next: "Ship webhook run history",
    progress: 24,
  },
];
const SOURCE_URL = process.env.NEXT_PUBLIC_SOURCE_URL ?? "";
const SHOW_EXPERIMENTAL_TABS =
  process.env.NEXT_PUBLIC_SHOW_EXPERIMENTAL_TABS === "true";
type RoleFamily = "all" | "ai" | "javascript";
type WorkMode = "all" | "remote" | "hybrid" | "onsite";
type Seniority =
  | "all"
  | "entry"
  | "mid"
  | "senior"
  | "lead"
  | "staff"
  | "principal"
  | "architect";
const TECHNOLOGIES = [
  "React",
  "TypeScript",
  "JavaScript",
  "Node.js",
  "Next.js",
  "Angular",
  "Vue",
  "Python",
  "GenAI",
  "LLM",
  "Agentic AI",
  "RAG",
  "LangChain",
  "LangGraph",
  "AWS",
  "Azure",
  "GCP",
  "FastAPI",
  "MCP",
  "Evals",
  "PostgreSQL",
  "SQL",
  "Docker",
  "Kubernetes",
  "Terraform",
  "Redis",
  "GraphQL",
  "Java",
  ".NET",
] as const;
const AI_TECHNOLOGIES = new Set([
  "Python",
  "GenAI",
  "LLM",
  "Agentic AI",
  "RAG",
  "LangChain",
  "LangGraph",
  "FastAPI",
  "MCP",
  "Evals",
]);
const technologyTags = (text: string) =>
  TECHNOLOGIES.filter((technology) => {
    const patterns: Record<string, RegExp> = {
      "Node.js": /\bnode(?:\.js|js)?\b/i,
      "Next.js": /\bnext(?:\.js|js)?\b/i,
      GenAI: /\b(?:genai|generative ai)\b/i,
      "Agentic AI": /\b(?:agentic ai|ai agents?)\b/i,
      GCP: /\b(?:gcp|google cloud)\b/i,
      FastAPI: /\bfastapi\b/i,
      ".NET": /\b(?:\.net|dotnet)\b/i,
    };
    return (
      patterns[technology] ??
      new RegExp(`\\b${technology.replace(".", "\\.")}\\b`, "i")
    ).test(text);
  });
const recruiterEmail = (description: string | null) =>
  description?.match(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i)?.[0] ?? null;
const seniorityLevel = (title: string): Exclude<Seniority, "all"> | null => {
  const text = title.toLowerCase();
  if (/\b(principal|distinguished)\b/.test(text)) return "principal";
  if (/\barchitect\b/.test(text)) return "architect";
  if (/\bstaff\b/.test(text)) return "staff";
  if (/\b(lead|manager|head)\b/.test(text)) return "lead";
  if (/\b(senior|sr\.?|level\s*[34]|iii|iv)\b/.test(text)) return "senior";
  if (/\b(mid|intermediate|level\s*2|ii)\b/.test(text)) return "mid";
  if (/\b(junior|jr\.?|entry|graduate|associate|level\s*1)\b/.test(text))
    return "entry";
  return null;
};
const roleFamily = (job: Job): Exclude<RoleFamily, "all"> | null => {
  const text = `${job.title} ${job.tags.join(" ")}`.toLowerCase();
  if (
    /\b(ai|ml|llm|genai|agentic|machine learning|data scientist|prompt)\b/.test(
      text,
    )
  )
    return "ai";
  if (
    /javascript|typescript|react|node\.?js|angular|vue|next\.?js|front.?end|full.?stack|mern/.test(
      text,
    )
  )
    return "javascript";
  return null;
};
const workMode = (location: string): Exclude<WorkMode, "all"> | null => {
  const text = location.toLowerCase();
  if (/hybrid/.test(text)) return "hybrid";
  if (/^remote$|\b100% remote\b|\bfully remote\b|\bremote\s*[-–—]/.test(text))
    return "remote";
  if (/onsite|on-site|in person|in-person/.test(text)) return "onsite";
  return null;
};

const csvRows = (text: string): string[][] => {
  const rows: string[][] = [];
  let row: string[] = [];
  let cell = "";
  let quoted = false;
  for (let index = 0; index < text.length; index += 1) {
    const character = text[index];
    if (character === '"') {
      if (quoted && text[index + 1] === '"') {
        cell += '"';
        index += 1;
      } else quoted = !quoted;
    } else if (character === "," && !quoted) {
      row.push(cell.trim());
      cell = "";
    } else if ((character === "\n" || character === "\r") && !quoted) {
      if (character === "\r" && text[index + 1] === "\n") index += 1;
      row.push(cell.trim());
      if (row.some(Boolean)) rows.push(row);
      row = [];
      cell = "";
    } else cell += character;
  }
  row.push(cell.trim());
  if (row.some(Boolean)) rows.push(row);
  return rows;
};

const importJobsFromText = (text: string): ImportJob[] => {
  const clean = text.trim();
  if (!clean) return [];
  let records: Record<string, unknown>[];
  if (clean.startsWith("[") || clean.startsWith("{")) {
    const parsed = JSON.parse(clean);
    const items = Array.isArray(parsed) ? parsed : parsed.jobs;
    if (!Array.isArray(items)) throw new Error("JSON must be an array or contain a jobs array");
    records = items;
  } else {
    const [headers, ...rows] = csvRows(clean);
    if (!headers?.length) return [];
    records = rows.map((values) =>
      Object.fromEntries(headers.map((header, index) => [header.trim().toLowerCase(), values[index] ?? ""])),
    );
  }
  const numberValue = (value: unknown) => {
    if (value === null || value === undefined || value === "") return null;
    const parsed = Number(String(value).replace(/[^0-9.]/g, ""));
    return Number.isFinite(parsed) ? parsed : null;
  };
  return records.map((record, index) => {
    const title = String(record.title ?? "").trim();
    const company = String(record.company ?? "").trim();
    const description = String(record.description ?? "").trim();
    if (!title || !company || description.length < 40)
      throw new Error(`Row ${index + 1} needs title, company, and a description of at least 40 characters`);
    return {
      source: String(record.source ?? "manual-import").trim() || "manual-import",
      source_url: record.source_url ? String(record.source_url) : null,
      title,
      company,
      description,
      location: String(record.location ?? "Unknown"),
      rate_min: numberValue(record.rate_min),
      rate_max: numberValue(record.rate_max),
      contract_duration: record.contract_duration ? String(record.contract_duration) : null,
      engagement_type: record.engagement_type ? String(record.engagement_type) : null,
      recruiter_email: record.recruiter_email ? String(record.recruiter_email) : null,
    };
  });
};

type ChipInputProps = {
  label: string;
  values: string[];
  suggestions: string[];
  placeholder: string;
  onChange: (values: string[]) => void;
};

function ChipInput({
  label,
  values,
  suggestions,
  placeholder,
  onChange,
}: ChipInputProps) {
  const [draft, setDraft] = useState("");
  const [open, setOpen] = useState(false);
  const matches = suggestions
    .filter(
      (suggestion) =>
        !values.some(
          (value) => value.toLowerCase() === suggestion.toLowerCase(),
        ) && suggestion.toLowerCase().includes(draft.trim().toLowerCase()),
    )
    .slice(0, 8);

  const add = (raw: string) => {
    const value = raw.trim().replace(/,$/, "");
    if (
      value &&
      !values.some((existing) => existing.toLowerCase() === value.toLowerCase())
    ) {
      onChange([...values, value]);
    }
    setDraft("");
    setOpen(false);
  };
  const remove = (value: string) =>
    onChange(values.filter((existing) => existing !== value));
  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if ((event.key === "Enter" || event.key === ",") && draft.trim()) {
      event.preventDefault();
      add(draft);
    } else if (event.key === "Backspace" && !draft && values.length) {
      remove(values[values.length - 1]);
    } else if (event.key === "Escape") {
      setOpen(false);
    }
  };
  const onPaste = (event: ClipboardEvent<HTMLInputElement>) => {
    const pasted = event.clipboardData.getData("text");
    if (!/[,\n]/.test(pasted)) return;
    event.preventDefault();
    const additions = pasted
      .split(/[,\n]/)
      .map((value) => value.trim())
      .filter(Boolean);
    const unique = [...values];
    for (const value of additions) {
      if (!unique.some((item) => item.toLowerCase() === value.toLowerCase()))
        unique.push(value);
    }
    onChange(unique);
    setDraft("");
  };

  return (
    <div className="chipField">
      <span className="chipLabel">{label}</span>
      <div
        className="chipInput"
        onClick={(event) =>
          event.currentTarget.querySelector("input")?.focus()
        }
      >
        {values.map((value) => (
          <span className="profileChip" key={value}>
            {value}
            <button
              type="button"
              aria-label={`Remove ${value}`}
              onClick={(event) => {
                event.stopPropagation();
                remove(value);
              }}
            >
              ×
            </button>
          </span>
        ))}
        <input
          aria-label={`Add ${label.toLowerCase()}`}
          value={draft}
          placeholder={values.length ? "Add another…" : placeholder}
          onChange={(event) => {
            setDraft(event.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onBlur={() => window.setTimeout(() => setOpen(false), 120)}
          onKeyDown={onKeyDown}
          onPaste={onPaste}
        />
      </div>
      {open && matches.length > 0 && (
        <div className="chipSuggestions" role="listbox">
          {matches.map((suggestion) => (
            <button
              type="button"
              role="option"
              aria-selected="false"
              key={suggestion}
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => add(suggestion)}
            >
              <span>{suggestion}</span>
              <small>From opportunities</small>
            </button>
          ))}
        </div>
      )}
      <small className="chipHelp">
        Press Enter or comma to add. Suggestions come from ingested jobs.
      </small>
    </div>
  );
}

export default function CoreProduct() {
  const [tab, setTab] = useState<
    "jobs" | "pipeline" | "lab" | "control" | "profile" | "workspace" | "setup"
  >("jobs");
  const [minRate, setMinRate] = useState(130);
  const [query, setQuery] = useState("");
  const [lane, setLane] = useState<"all" | QualityLane>("all");
  const [c2c, setC2c] = useState<"all" | Job["c2c"]>("confirmed");
  const [role, setRole] = useState<RoleFamily>("all");
  const [technology, setTechnology] = useState("all");
  const [seniority, setSeniority] = useState<Seniority>("all");
  const [mode, setMode] = useState<WorkMode>("all");
  const [status, setStatus] = useState("all");
  const [disclosedOnly, setDisclosedOnly] = useState(false);
  const [catalog, setCatalog] = useState<Job[]>([]);
  const [selected, setSelected] = useState<Job | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [correctionOpen, setCorrectionOpen] = useState(false);
  const [correctionRateMin, setCorrectionRateMin] = useState(0);
  const [correctionRateMax, setCorrectionRateMax] = useState(0);
  const [correctionLocation, setCorrectionLocation] = useState("");
  const [scanning, setScanning] = useState(false);
  const [apiState, setApiState] = useState("Connecting to local API…");
  const [sourceTargets, setSourceTargets] = useState<SourceTarget[]>([]);
  const [selectedSources, setSelectedSources] = useState<string[]>([]);
  const [emailConnections, setEmailConnections] = useState<EmailConnection[]>(
    [],
  );
  const [emailState, setEmailState] = useState(
    "OAuth mailbox access is not connected",
  );
  const [emailOAuthStatus, setEmailOAuthStatus] = useState<EmailOAuthStatus | null>(null);
  const [profile, setProfile] = useState<CandidateProfile>(DEFAULT_PROFILE);
  const [profileState, setProfileState] = useState("Loading profile…");
  const [decisionReason, setDecisionReason] = useState("role_not_compelling");
  const [decisionNotes, setDecisionNotes] = useState("");
  const [decisionState, setDecisionState] = useState("");
  const [decisionHistory, setDecisionHistory] = useState<JobDecision[]>([]);
  const [controlRoom, setControlRoom] = useState<ControlRoomData | null>(null);
  const [controlState, setControlState] = useState("Loading usage…");
  const [controlRefresh, setControlRefresh] = useState(0);
  const [modelConnection, setModelConnection] = useState<ModelConnection | null>(null);
  const [modelProvider, setModelProvider] = useState<ModelConnection["provider"]>("deterministic");
  const [modelBaseUrl, setModelBaseUrl] = useState("");
  const [modelName, setModelName] = useState("local-rules");
  const [modelApiKey, setModelApiKey] = useState("");
  const [modelInputCost, setModelInputCost] = useState(0);
  const [modelOutputCost, setModelOutputCost] = useState(0);
  const [modelState, setModelState] = useState("Checking model connection…");
  const [webSearchConnection, setWebSearchConnection] = useState<WebSearchConnection | null>(null);
  const [webSearchProvider, setWebSearchProvider] = useState<WebSearchConnection["provider"]>("disabled");
  const [webSearchBaseUrl, setWebSearchBaseUrl] = useState("");
  const [webSearchApiKey, setWebSearchApiKey] = useState("");
  const [webSearchFocus, setWebSearchFocus] = useState("");
  const [webSearchState, setWebSearchState] = useState("Checking web discovery…");
  const [webSearching, setWebSearching] = useState(false);
  const [acquisitionRuns, setAcquisitionRuns] = useState<AcquisitionRun[]>([]);
  const [importText, setImportText] = useState("");
  const [importCount, setImportCount] = useState(0);
  const [importState, setImportState] = useState("Paste CSV or JSON, or choose a file");
  const profileSuggestions = useMemo(() => {
    const unique = (items: string[]) =>
      [...new Set(items.map((item) => item.trim()).filter(Boolean))].sort(
        (left, right) => left.localeCompare(right),
      );
    const technologies = unique(catalog.flatMap((job) => job.tags));
    return {
      roles: unique(catalog.map((job) => job.title)),
      locations: unique(catalog.map((job) => job.location)),
      coreSkills: technologies.filter(
        (technology) => !AI_TECHNOLOGIES.has(technology),
      ),
      aiSkills: technologies.filter((technology) =>
        AI_TECHNOLOGIES.has(technology),
      ),
    };
  }, [catalog]);
  const profileReady = Boolean(
    profile.onboarding_completed &&
      profile.target_roles.length &&
      profile.locations.length &&
      profile.core_skills.length + profile.ai_skills.length,
  );
  async function fetchJobs(): Promise<Job[]> {
    const response = await fetch("/api/v1/jobs");
    if (!response.ok) throw new Error(`API ${response.status}`);
    const rows: ApiJob[] = await response.json();
    return rows.map((row) => ({
      id: row.id,
      company: row.company,
      title: row.title,
      description: row.description ?? "No job description was retained.",
      rateMin: row.rate_min ?? 0,
      rateMax: row.rate_max ?? 0,
      location: row.location ?? "Not specified",
      term:
        row.contract_duration ??
        row.engagement_type ??
        "Terms need verification",
      score: row.fit_score,
      c2c: row.c2c_status,
      recruiterEmail: recruiterEmail(row.description),
      tags: technologyTags(`${row.title} ${row.description ?? ""}`),
      fresh: new Date(row.created_at).toLocaleString(),
      why:
        Array.isArray(row.reasons) && row.reasons.length
          ? row.reasons
          : ["Screened and persisted by the local C2CDirect API"],
      gaps: Array.isArray(row.risks) ? row.risks : [],
      source: row.provider_name ?? "Local intake",
      vendor: row.end_client_name
        ? `End client: ${row.end_client_name}`
        : "End client needs verification",
      status: row.status.charAt(0).toUpperCase() + row.status.slice(1),
      qualityLane: row.quality_lane,
      authority: row.source_authority,
      confidence: Number(row.provenance_confidence),
      completeness: Number(row.provenance_completeness),
      layers:
        row.vendor_layer_min === row.vendor_layer_max
          ? String(row.vendor_layer_min)
          : `${row.vendor_layer_min}–${row.vendor_layer_max}`,
      observations: Number(row.observation_count),
      url: row.canonical_url ?? row.source_url,
    }));
  }
  async function fetchEmailConnections(): Promise<EmailConnection[]> {
    const response = await fetch("/api/v1/email/connections");
    if (!response.ok) throw new Error();
    return response.json();
  }
  useEffect(() => {
    fetchJobs()
      .then((live) => {
        setCatalog(live);
        setSelected(live[0] ?? null);
        setApiState(`Live local API · ${live.length} persisted`);
      })
      .catch(() => {
        setCatalog([]);
        setSelected(null);
        setApiState("Local API unavailable · no jobs loaded");
      });
  }, []);
  useEffect(() => {
    if (tab !== "setup" && tab !== "control") return;
    let mounted = true;
    const load = () => fetch("/api/v1/acquisition-runs")
      .then(async (response) => response.ok ? response.json() : [])
      .then((runs: AcquisitionRun[]) => { if (mounted) setAcquisitionRuns(runs); })
      .catch(() => undefined);
    void load();
    const timer = window.setInterval(load, 3000);
    return () => {
      mounted = false;
      window.clearInterval(timer);
    };
  }, [tab]);
  useEffect(() => {
    fetch("/api/v1/email/oauth/status")
      .then(async (response) => {
        if (!response.ok) throw new Error();
        return response.json();
      })
      .then(setEmailOAuthStatus)
      .catch(() => setEmailOAuthStatus(null));
  }, []);
  useEffect(() => {
    fetch("/api/v1/sources")
      .then(async (response) => {
        if (!response.ok) throw new Error();
        return response.json();
      })
      .then((data: { sources: SourceTarget[] }) => {
        const ready = data.sources.filter((source) => source.enabled && source.priority <= 3);
        setSourceTargets(ready);
        setSelectedSources(ready.map((source) => source.slug));
      })
      .catch(() => setSourceTargets([]));
  }, []);
  useEffect(() => {
    fetch("/api/v1/web-search-connection")
      .then(async (response) => {
        if (!response.ok) throw new Error(`API ${response.status}`);
        return response.json();
      })
      .then((connection: WebSearchConnection) => {
        setWebSearchConnection(connection);
        setWebSearchProvider(connection.provider);
        setWebSearchBaseUrl(connection.base_url ?? "");
        setWebSearchState(
          connection.configured
            ? `${connection.provider} web discovery is ready`
            : "Choose a search service to enable Web Scout",
        );
      })
      .catch(() => setWebSearchState("Web discovery configuration is unavailable"));
  }, []);
  useEffect(() => {
    if (tab !== "control") return;
    fetch("/api/v1/control-room")
      .then(async (response) => {
        if (!response.ok) throw new Error(`API ${response.status}`);
        return response.json();
      })
      .then((data: ControlRoomData) => {
        setControlRoom(data);
        setControlState("Live tenant usage");
      })
      .catch(() => setControlState("Usage data unavailable"));
  }, [tab, controlRefresh]);
  useEffect(() => {
    fetch("/api/v1/model-connection")
      .then(async (response) => {
        if (!response.ok) throw new Error(`API ${response.status}`);
        return response.json();
      })
      .then((connection: ModelConnection) => {
        setModelConnection(connection);
        setModelProvider(connection.provider);
        setModelBaseUrl(connection.base_url ?? "");
        setModelName(connection.model);
        setModelInputCost(connection.input_cost_per_million);
        setModelOutputCost(connection.output_cost_per_million);
        setModelState(
          connection.mode === "model-assisted"
            ? `Connected to ${connection.model}`
            : "Deterministic local screening is ready",
        );
      })
      .catch(() => setModelState("Model configuration is unavailable"));
  }, []);
  useEffect(() => {
    fetch("/api/v1/profile")
      .then(async (response) => {
        if (!response.ok) throw new Error();
        return response.json();
      })
      .then((data) => {
        setProfile(data);
        setMinRate(data.min_rate);
        setProfileState("Profile loaded");
      })
      .catch(() => setProfileState("Profile unavailable"));
  }, []);
  useEffect(() => {
    const apply = (connections: EmailConnection[]) => {
      setEmailConnections(connections);
      setEmailState(
        connections.length
          ? `${connections.length} authorized mailbox${connections.length === 1 ? "" : "es"}`
          : "OAuth mailbox access is not connected",
      );
    };
    fetchEmailConnections()
      .then(apply)
      .catch(() => setEmailState("Mailbox status unavailable"));
    const authorized = (event: MessageEvent) => {
      if (
        event.origin === window.location.origin &&
        event.data?.type === "c2c-email-connected"
      ) {
        fetchEmailConnections()
          .then(apply)
          .catch(() =>
            setEmailState("Mailbox connected; refresh to view status"),
          );
      }
    };
    window.addEventListener("message", authorized);
    return () => window.removeEventListener("message", authorized);
  }, []);
  const jobs = useMemo(
    () =>
      catalog.filter(
        (j) =>
          (j.rateMax === 0 || j.rateMax >= minRate) &&
          (!disclosedOnly || j.rateMax > 0) &&
          (lane === "all" || j.qualityLane === lane) &&
          (c2c === "all" || j.c2c === c2c) &&
          (role === "all" || roleFamily(j) === role) &&
          (technology === "all" || j.tags.includes(technology)) &&
          (seniority === "all" || seniorityLevel(j.title) === seniority) &&
          (mode === "all" || workMode(j.location) === mode) &&
          (status === "all" || j.status === status) &&
          (j.title + j.company + j.location + j.tags.join(" "))
            .toLowerCase()
            .includes(query.toLowerCase()),
      ),
    [
      catalog,
      minRate,
      query,
      lane,
      c2c,
      role,
      technology,
      seniority,
      mode,
      status,
      disclosedOnly,
    ],
  );
  const activeFilters = [
    c2c !== "all",
    role !== "all",
    technology !== "all",
    seniority !== "all",
    mode !== "all",
    status !== "all",
    lane !== "all",
    disclosedOnly,
    minRate !== 130,
    query.trim() !== "",
  ].filter(Boolean).length;
  function clearFilters() {
    setMinRate(130);
    setQuery("");
    setLane("all");
    setC2c("all");
    setRole("all");
    setTechnology("all");
    setSeniority("all");
    setMode("all");
    setStatus("all");
    setDisclosedOnly(false);
  }
  async function queueAndWait(
    kind: AcquisitionRun["kind"],
    request: Record<string, unknown>,
    progress: (message: string) => void,
  ): Promise<Record<string, number | string>> {
    const queued = await fetch("/api/v1/acquisition-runs", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ kind, request }),
    });
    const accepted = await queued.json();
    if (!queued.ok) throw new Error(accepted.detail ?? "Could not queue acquisition run");
    for (let attempt = 0; attempt < 900; attempt += 1) {
      await new Promise((resolve) => window.setTimeout(resolve, 1000));
      const response = await fetch(`/api/v1/acquisition-runs/${accepted.id}`);
      const run: AcquisitionRun = await response.json();
      if (!response.ok) throw new Error("Could not read acquisition progress");
      if (run.status === "queued") progress("Queued safely · waiting for the Core worker…");
      if (run.status === "running") progress("Running in the background · you may leave this page");
      if (run.status === "completed") return run.result_json ?? {};
      if (run.status === "failed") throw new Error(`Run failed safely · ${run.error_code ?? "unknown error"}`);
      if (run.status === "cancelled") throw new Error("Run was cancelled");
    }
    throw new Error("Run is still active · check acquisition history later");
  }
  async function retryAcquisition(run: AcquisitionRun) {
    await fetch(`/api/v1/acquisition-runs/${run.id}/retry`, { method: "POST" });
    setApiState("Retry queued safely");
  }
  async function cancelAcquisition(run: AcquisitionRun) {
    await fetch(`/api/v1/acquisition-runs/${run.id}`, { method: "DELETE" });
    setApiState(run.status === "running" ? "Stop requested · finishing the current item safely" : "Queued run cancelled");
  }
  async function scan() {
    if (!profileReady) {
      setApiState("Complete and save your matching profile before sourcing jobs");
      setTab("profile");
      return;
    }
    setScanning(true);
    setApiState("Scanning reviewed direct sources…");
    try {
      const result = await queueAndWait(
        "public_sources",
        {
          priorities: [1, 2, 3],
          source_slugs: selectedSources,
          total_limit: 200,
          per_target_limit: 20,
        },
        setApiState,
      );
      const live = await fetchJobs();
      setCatalog(live);
      setSelected(live[0] ?? null);
      setApiState(
        `Scan complete · ${result.created} new · ${result.enriched} refreshed`,
      );
    } catch {
      setApiState("Scan failed safely · no public exposure changed");
    } finally {
      setScanning(false);
    }
  }
  async function connectEmail(provider: "gmail" | "microsoft") {
    setEmailState(`Preparing ${provider} authorization…`);
    try {
      const response = await fetch(`/api/v1/email/oauth/${provider}/start`);
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail ?? "OAuth unavailable");
      window.open(
        result.authorization_url,
        "c2c-email-oauth",
        "width=620,height=760",
      );
      setEmailState("Complete authorization in the secure provider window");
    } catch (error) {
      setEmailState(
        error instanceof Error
          ? error.message
          : "OAuth setup is not yet configured",
      );
    }
  }
  async function syncEmail(provider: "gmail" | "microsoft") {
    if (!profileReady) {
      setEmailState("Complete and save your matching profile before syncing mail");
      setTab("profile");
      return;
    }
    setEmailState(`Checking recent ${provider} job mail…`);
    try {
      const result = await queueAndWait(
        "email_sync",
        { provider, limit: 50 },
        setEmailState,
      );
      const live = await fetchJobs();
      setCatalog(live);
      setSelected(live[0] ?? null);
      setEmailState(
        `${provider} sync complete · ${result.created} new · ${result.duplicate} already seen`,
      );
    } catch (error) {
      setEmailState(
        error instanceof Error ? error.message : "Mailbox sync failed safely",
      );
    }
  }
  const modelPayload = () => ({
    provider: modelProvider,
    base_url: modelProvider === "deterministic" ? "" : modelBaseUrl.trim(),
    model_name: modelProvider === "deterministic" ? "local-rules" : modelName.trim(),
    api_key: modelApiKey || null,
    input_cost_per_million: modelInputCost,
    output_cost_per_million: modelOutputCost,
  });
  function chooseModelPreset(preset: string) {
    if (preset === "deterministic") {
      setModelProvider("deterministic");
      setModelBaseUrl("");
      setModelName("local-rules");
    } else if (preset === "ollama") {
      setModelProvider("openai_compatible");
      setModelBaseUrl("http://host.docker.internal:11434/v1");
      setModelName("llama3.1:8b");
    } else if (preset === "lmstudio") {
      setModelProvider("openai_compatible");
      setModelBaseUrl("http://host.docker.internal:1234/v1");
      setModelName("local-model");
    } else {
      setModelProvider("openai_compatible");
      setModelBaseUrl("");
      setModelName("");
    }
    setModelState("Enter the connection details, then test the endpoint");
  }
  async function testModel() {
    setModelState("Testing the private model connection…");
    try {
      const response = await fetch("/api/v1/model-connection/test", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(modelPayload()),
      });
      const result = await response.json();
      if (!response.ok || !result.ok)
        throw new Error(result.detail ?? result.message ?? "Connection failed");
      setModelState(
        result.model_visible === false
          ? "Endpoint connected, but the model name was not listed"
          : result.message,
      );
    } catch (error) {
      setModelState(error instanceof Error ? error.message : "Connection failed");
    }
  }
  async function saveModel() {
    setModelState("Saving encrypted model configuration…");
    try {
      const response = await fetch("/api/v1/model-connection", {
        method: "PUT",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(modelPayload()),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail ?? "Could not save model connection");
      setModelConnection(result);
      setModelApiKey("");
      setModelState(
        result.mode === "model-assisted"
          ? `Saved · ${result.model} is now the active AI brain`
          : "Saved · deterministic local screening is active",
      );
      setControlRefresh((current) => current + 1);
    } catch (error) {
      setModelState(error instanceof Error ? error.message : "Could not save model connection");
    }
  }
  const webSearchPayload = () => ({
    provider: webSearchProvider,
    base_url: webSearchProvider === "disabled" ? "" : webSearchBaseUrl.trim(),
    api_key: webSearchApiKey || null,
  });
  async function testWebSearch() {
    setWebSearchState("Testing web discovery…");
    try {
      const response = await fetch("/api/v1/web-search-connection/test", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(webSearchPayload()),
      });
      const result = await response.json();
      if (!response.ok || !result.ok)
        throw new Error(result.detail ?? result.message ?? "Connection failed");
      setWebSearchState(result.message);
    } catch (error) {
      setWebSearchState(error instanceof Error ? error.message : "Connection failed");
    }
  }
  async function saveWebSearch() {
    setWebSearchState("Saving encrypted search configuration…");
    try {
      const response = await fetch("/api/v1/web-search-connection", {
        method: "PUT",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(webSearchPayload()),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail ?? "Could not save web discovery");
      setWebSearchConnection(result);
      setWebSearchApiKey("");
      setWebSearchState(
        result.configured
          ? `Saved · ${result.provider} powers Web Scout`
          : "Saved · web discovery is off",
      );
    } catch (error) {
      setWebSearchState(error instanceof Error ? error.message : "Could not save web discovery");
    }
  }
  async function runWebScout() {
    if (!profileReady) {
      setWebSearchState("Complete and save your matching profile before running Web Scout");
      setTab("profile");
      return;
    }
    setWebSearching(true);
    setWebSearchState("Your AI brain is gathering and screening public requisitions…");
    try {
      const result = await queueAndWait(
        "web_scout",
        { focus: webSearchFocus, max_results: 25, domains: [] },
        setWebSearchState,
      );
      const live = await fetchJobs();
      setCatalog(live);
      setSelected(live[0] ?? null);
      setWebSearchState(
        `Web Scout found ${result.discovered} · imported ${result.persisted ?? 0} · ${result.duplicates ?? 0} duplicates`,
      );
      setApiState(`Live local API · ${live.length} persisted`);
    } catch (error) {
      setWebSearchState(error instanceof Error ? error.message : "Web Scout failed safely");
    } finally {
      setWebSearching(false);
    }
  }
  function inspectImport(text: string) {
    setImportText(text);
    try {
      const jobs = importJobsFromText(text);
      setImportCount(jobs.length);
      setImportState(jobs.length ? `${jobs.length} valid job${jobs.length === 1 ? "" : "s"} ready` : "Paste CSV or JSON, or choose a file");
    } catch (error) {
      setImportCount(0);
      setImportState(error instanceof Error ? error.message : "Could not read this import");
    }
  }
  async function importJobs() {
    if (!profileReady) {
      setImportState("Complete and save your matching profile before importing jobs");
      setTab("profile");
      return;
    }
    let jobs: ImportJob[];
    try {
      jobs = importJobsFromText(importText);
      if (!jobs.length) throw new Error("Add at least one job first");
    } catch (error) {
      setImportState(error instanceof Error ? error.message : "Could not read this import");
      return;
    }
    setImportState(`Screening and importing ${jobs.length} job${jobs.length === 1 ? "" : "s"}…`);
    try {
      const result = await queueAndWait(
        "import",
        { jobs, retain_all_in_pipeline: true },
        setImportState,
      );
      const live = await fetchJobs();
      setCatalog(live);
      setSelected(live[0] ?? null);
      setImportText("");
      setImportCount(0);
      setImportState(`Imported ${result.persisted} · ${result.duplicates} duplicate${result.duplicates === 1 ? "" : "s"}`);
      setApiState(`Live local API · ${live.length} persisted`);
    } catch (error) {
      setImportState(error instanceof Error ? error.message : "Import failed safely");
    }
  }
  async function saveProfile() {
    if (!profile.target_roles.length || !profile.locations.length || !(profile.core_skills.length + profile.ai_skills.length)) {
      setProfileState("Add a target role, preferred location, and at least one skill");
      return;
    }
    setProfileState("Saving…");
    try {
      const completed = { ...profile, onboarding_completed: true };
      const response = await fetch("/api/v1/profile", {
        method: "PUT",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(completed),
      });
      const result = await response.json();
      if (!response.ok)
        throw new Error(result.detail ?? "Could not save profile");
      setProfile({ ...result, onboarding_completed: true });
      setMinRate(result.min_rate);
      setProfileState("Profile complete · sourcing is unlocked");
    } catch (error) {
      setProfileState(
        error instanceof Error ? error.message : "Could not save profile",
      );
    }
  }
  async function uploadResume(file: File) {
    setProfileState("Uploading résumé…");
    const body = new FormData();
    body.append("resume", file);
    try {
      const response = await fetch("/api/v1/profile/resume", {
        method: "POST",
        body,
      });
      const result = await response.json();
      if (!response.ok)
        throw new Error(result.detail ?? "Could not upload résumé");
      setProfile(result);
      setProfileState("Résumé uploaded");
    } catch (error) {
      setProfileState(
        error instanceof Error ? error.message : "Could not upload résumé",
      );
    }
  }
  async function removeResume() {
    setProfileState("Removing résumé…");
    const response = await fetch("/api/v1/profile/resume", {
      method: "DELETE",
    });
    if (response.ok) {
      setProfile((current) => ({ ...current, resume: null }));
      setProfileState("Résumé removed");
    } else setProfileState("Could not remove résumé");
  }
  async function updateJobStatus(job: Job, nextStatus: string) {
    setDecisionState("Saving stage…");
    try {
      const response = await fetch(`/api/v1/jobs/${job.id}/status`, {
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ status: nextStatus.toLowerCase() }),
      });
      if (!response.ok) throw new Error("Could not update the pipeline stage");
      const display = nextStatus.charAt(0).toUpperCase() + nextStatus.slice(1);
      setCatalog((current) =>
        current.map((item) =>
          item.id === job.id ? { ...item, status: display } : item,
        ),
      );
      setSelected((current) =>
        current?.id === job.id ? { ...current, status: display } : current,
      );
      setDecisionState(`Moved to ${display}`);
    } catch (error) {
      setDecisionState(
        error instanceof Error ? error.message : "Could not update the stage",
      );
    }
  }
  async function rescreen(job: Job) {
    setDecisionState("Re-screening with your current profile and feedback…");
    try {
      const response = await fetch(`/api/v1/jobs/${job.id}/rescreen`, { method: "POST" });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail ?? "Re-screening failed");
      const live = await fetchJobs();
      setCatalog(live);
      setSelected(live.find((item) => item.id === job.id) ?? null);
      setDecisionState("Re-screened with current preferences");
    } catch (error) {
      setDecisionState(error instanceof Error ? error.message : "Re-screening failed");
    }
  }
  async function saveJobCorrection(job: Job) {
    setDecisionState("Saving corrected commercial terms…");
    try {
      const response = await fetch(`/api/v1/jobs/${job.id}/corrections`, {
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          rate_min: correctionRateMin || null,
          rate_max: correctionRateMax || null,
          location: correctionLocation || null,
        }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail ?? "Could not save corrections");
      setCorrectionOpen(false);
      await rescreen(job);
    } catch (error) {
      setDecisionState(error instanceof Error ? error.message : "Could not save corrections");
    }
  }
  async function loadDecisionHistory(jobId: string) {
    try {
      const response = await fetch(`/api/v1/jobs/${jobId}/decisions`);
      if (!response.ok) throw new Error();
      setDecisionHistory(await response.json());
    } catch {
      setDecisionHistory([]);
    }
  }
  async function recordDecision(
    job: Job,
    outcome: JobDecision["outcome"],
  ) {
    setDecisionState("Recording feedback…");
    try {
      const response = await fetch(`/api/v1/jobs/${job.id}/decisions`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          outcome,
          reason_code: decisionReason,
          notes: decisionNotes.trim() || null,
        }),
      });
      const result = await response.json();
      if (!response.ok)
        throw new Error(result.detail ?? "Could not record feedback");
      const nextStatus = outcome === "denied" ? "Rejected" : "Passed";
      setCatalog((current) =>
        current.map((item) =>
          item.id === job.id ? { ...item, status: nextStatus } : item,
        ),
      );
      setSelected((current) =>
        current?.id === job.id ? { ...current, status: nextStatus } : current,
      );
      setDecisionHistory((current) => [result, ...current]);
      setDecisionNotes("");
      setDecisionState(
        outcome === "denied"
          ? "Denial recorded as model feedback"
          : "Interest decision recorded as model feedback",
      );
    } catch (error) {
      setDecisionState(
        error instanceof Error ? error.message : "Could not record feedback",
      );
    }
  }
  function openPipelineJob(job: Job) {
    setSelected(job);
    setDetailOpen(true);
    setDecisionState("");
    setDecisionNotes("");
    void loadDecisionHistory(job.id);
  }
  function findRecruiter(job: Job) {
    const specialty =
      roleFamily(job) === "ai" ? "AI engineering" : "software engineering";
    const query = `site:linkedin.com/in \"${job.company}\" (recruiter OR talent OR staffing) \"${specialty}\"`;
    window.open(
      `https://www.google.com/search?q=${encodeURIComponent(query)}`,
      "_blank",
      "noopener,noreferrer",
    );
  }
  return (
    <main>
      <header className="topbar">
        <div className="brand">
          <span className="brandMark">D</span>
          <span>C2CDirect</span>
        </div>
        <nav>
          <button
            onClick={() => setTab("jobs")}
            className={tab === "jobs" ? "navActive" : ""}
          >
            Opportunities
          </button>
          <button
            onClick={() => setTab("pipeline")}
            className={tab === "pipeline" ? "navActive" : ""}
          >
            Pipeline
          </button>
          {SHOW_EXPERIMENTAL_TABS && (
            <button
              onClick={() => setTab("lab")}
              className={tab === "lab" ? "navActive" : ""}
            >
              Build Lab
            </button>
          )}
          <button
            onClick={() => setTab("control")}
            className={tab === "control" ? "navActive" : ""}
          >
            Control Room
          </button>
          <button
            onClick={() => setTab("profile")}
            className={tab === "profile" ? "navActive" : ""}
          >
            Profile
          </button>
          <button
            onClick={() => setTab("setup")}
            className={tab === "setup" ? "navActive" : ""}
          >
            Setup
          </button>
          {SHOW_EXPERIMENTAL_TABS && (
            <button
              onClick={() => setTab("workspace")}
              className={tab === "workspace" ? "navActive" : ""}
            >
              Workspace
            </button>
          )}
        </nav>
        <div className="status">
          <span /> {apiState}
        </div>
      </header>
      {tab === "jobs" && (
        <>
          <section className="hero shell">
            <div>
              <p className="eyebrow">DIRECT OPPORTUNITY INTELLIGENCE</p>
              <h1>
                Find the contract.{" "}
                <br />
                <em>Win the work.</em>
              </h1>
              <p className="lede">
                Verify the chain behind high-rate C2C opportunities, match them
                to your profile, and run every pursuit from one workspace.
              </p>
            </div>
            <div className="heroScore">
              <span>Best live match</span>
              <strong>{jobs[0]?.score ?? "—"}</strong>
              <small>{jobs[0]?.company ?? "No jobs yet"}</small>
            </div>
          </section>
          <section className="shell workspace">
            <div className="quickFilters">
              <div>
                <label htmlFor="technology-filter">Technology</label>
                <select
                  id="technology-filter"
                  value={technology}
                  onChange={(e) => setTechnology(e.target.value)}
                >
                  <option value="all">Any technology</option>
                  {TECHNOLOGIES.map((item) => (
                    <option value={item} key={item}>
                      {item}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label htmlFor="seniority-filter">Seniority</label>
                <select
                  id="seniority-filter"
                  value={seniority}
                  onChange={(e) => setSeniority(e.target.value as Seniority)}
                >
                  <option value="all">Any seniority</option>
                  <option value="entry">Entry / junior</option>
                  <option value="mid">Mid-level</option>
                  <option value="senior">Senior</option>
                  <option value="lead">Lead / manager</option>
                  <option value="staff">Staff</option>
                  <option value="principal">Principal / distinguished</option>
                  <option value="architect">Architect</option>
                </select>
              </div>
            </div>
            <aside className="filters">
              <div className="filterTitle">
                <p className="sectionLabel">FILTER OPPORTUNITIES</p>
                {activeFilters > 0 && (
                  <button onClick={clearFilters}>Clear {activeFilters}</button>
                )}
              </div>
              <label>C2C verification</label>
              <select
                aria-label="C2C verification"
                value={c2c}
                onChange={(e) => setC2c(e.target.value as "all" | Job["c2c"])}
              >
                <option value="all">Any C2C status</option>
                <option value="confirmed">Confirmed C2C only</option>
                <option value="likely">Likely C2C</option>
                <option value="unknown">Unverified</option>
                <option value="rejected">Rejected</option>
              </select>
              <label>Role family</label>
              <select
                aria-label="Role family"
                value={role}
                onChange={(e) => setRole(e.target.value as RoleFamily)}
              >
                <option value="all">AI + JavaScript roles</option>
                <option value="ai">AI / ML / LLM</option>
                <option value="javascript">JavaScript / TypeScript</option>
              </select>
              <label>Work arrangement</label>
              <select
                aria-label="Work arrangement"
                value={mode}
                onChange={(e) => setMode(e.target.value as WorkMode)}
              >
                <option value="all">Remote, hybrid, or onsite</option>
                <option value="remote">Remote</option>
                <option value="hybrid">Hybrid</option>
                <option value="onsite">Onsite</option>
              </select>
              <label>Pipeline status</label>
              <select
                aria-label="Pipeline status"
                value={status}
                onChange={(e) => setStatus(e.target.value)}
              >
                <option value="all">Any status</option>
                <option value="New">New</option>
                <option value="Saved">Saved</option>
                <option value="Contacted">Contacted</option>
                <option value="Submitted">Submitted</option>
              </select>
              <label>
                Minimum rate <b>${minRate}/hr</b>
              </label>
              <input
                aria-label="Minimum hourly rate"
                type="range"
                min="90"
                max="200"
                value={minRate}
                onChange={(e) => setMinRate(+e.target.value)}
              />
              <label className="check">
                <input
                  type="checkbox"
                  checked={disclosedOnly}
                  onChange={(e) => setDisclosedOnly(e.target.checked)}
                />{" "}
                Disclosed pay only
              </label>
              <label>Source quality</label>
              <select
                aria-label="Source quality"
                value={lane}
                onChange={(e) => setLane(e.target.value as "all" | QualityLane)}
              >
                <option value="all">All reviewed lanes</option>
                <option value="direct_prime">Direct / prime</option>
                <option value="needs_verification">Needs verification</option>
                <option value="low_quality">Low quality</option>
              </select>
              <p className="filterNote">
                Undisclosed rates remain visible unless “Disclosed pay only” is
                selected.
              </p>
        <div className="profileBox">
          <span>Target identity</span>
          <b>{profile.headline}</b>
          <small>
            {[...profile.core_skills, ...profile.ai_skills]
              .slice(0, 6)
              .join(" · ")}
          </small>
        </div>
            </aside>
            <div className="feed">
              <div className="feedHead">
                <div>
                  <p className="sectionLabel">QUALITY-RANKED SHORTLIST</p>
                  <h2>{jobs.length} reviewed opportunities</h2>
                </div>
                <button
                  className="primary scanButton"
                  onClick={scan}
                  disabled={scanning}
                >
                  {scanning ? "Scanning…" : "Run fresh scan"}
                </button>
              </div>
              <input
                className="search"
                aria-label="Search opportunities"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search skills, title, or company…"
              />
              {catalog.length === 0 && (
                <div className="emptyState firstRunEmpty">
                  <b>Your Core workspace starts empty.</b>
                  <span>
                    C2CDirect Core does not ship with a managed job feed. Use
                    your profile and AI brain to scan public company boards,
                    connect a recruiter inbox, or import your own list.
                  </span>
                  <div>
                    <button className="primary" onClick={() => setTab("setup")}>
                      Choose job sources
                    </button>
                    <button className="secondary" onClick={scan} disabled={scanning}>
                      {scanning ? "Scanning…" : "Scan public boards"}
                    </button>
                  </div>
                </div>
              )}
              {catalog.length > 0 && jobs.length === 0 && (
                <div className="emptyState">
                  <b>No opportunities match these filters.</b>
                  <span>
                    Try broadening C2C status, work arrangement, or rate.
                  </span>
                  <button className="secondary" onClick={clearFilters}>
                    Clear all filters
                  </button>
                </div>
              )}
              {jobs.map((job) => (
                <article
                  onClick={() => {
                    setSelected(job);
                    setDetailOpen(true);
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      setSelected(job);
                      setDetailOpen(true);
                    }
                  }}
                  role="button"
                  tabIndex={0}
                  aria-label={`View evidence for ${job.title} at ${job.company}`}
                  className={`job ${selected?.id === job.id ? "selected" : ""}`}
                  key={job.id}
                >
                  <div className="score">
                    <strong>{job.score}</strong>
                    <span>FIT</span>
                  </div>
                  <div className="jobBody">
                    <div className="jobTop">
                      <div>
                        <p>{job.company}</p>
                        <h3>{job.title}</h3>
                      </div>
                      <time>{job.fresh}</time>
                    </div>
                    <b className="rate">
                      {job.rateMax
                        ? job.rateMin === job.rateMax
                          ? `$${job.rateMax}/hr`
                          : `$${job.rateMin}–${job.rateMax}/hr`
                        : "Rate not disclosed"}
                    </b>
                    <span className="meta">
                      C2C {job.c2c} · {job.location} · {job.term} · authority{" "}
                      {job.authority}
                    </span>
                    <div className="tags">
                      <span className={`lane ${job.qualityLane}`}>
                        {job.qualityLane.replaceAll("_", " ")}
                      </span>
                      <span>{job.layers} vendor layers</span>
                      <span>
                        {job.observations} source observation
                        {job.observations === 1 ? "" : "s"}
                      </span>
                    </div>
                    <span className="viewEvidence">View evidence →</span>
                  </div>
                  <button
                    className="save"
                    onClick={(e) => {
                      e.stopPropagation();
                      void updateJobStatus(
                        job,
                        job.status === "Saved" ? "new" : "saved",
                      );
                    }}
                    aria-label={`${job.status === "Saved" ? "Remove saved" : "Save"} ${job.title}`}
                  >
                    {job.status === "Saved" ? "✓" : "+"}
                  </button>
                </article>
              ))}
            </div>
            {detailOpen && (
              <button
                className="detailBackdrop"
                aria-label="Close evidence panel"
                onClick={() => setDetailOpen(false)}
              />
            )}
            {selected && (
              <aside
                className={`detail ${detailOpen ? "isOpen" : ""}`}
                aria-label={`Evidence for ${selected.title}`}
              >
                <button
                  className="close"
                  aria-label="Close evidence panel"
                  onClick={() => setDetailOpen(false)}
                >
                  ×
                </button>
                <p className="sectionLabel">EVIDENCE-BASED SCREENING</p>
                <h2>{selected.title}</h2>
                <p className="company">
                  {selected.company} · {selected.source}
                </p>
                <div className="detailRate">
                  <strong>{selected.score}</strong>
                  <span>match score</span>
                  <b>
                    {selected.rateMax
                      ? selected.rateMin === selected.rateMax
                        ? `$${selected.rateMax}/hr`
                        : `$${selected.rateMin}–${selected.rateMax}/hr`
                      : "Verify rate"}
                  </b>
                </div>
                <h4>Why it made the cut</h4>
                {selected.why.map((x) => (
                  <p className="reason" key={x}>
                    ✓ {x}
                  </p>
                ))}
                <h4>Open verification work</h4>
                {selected.gaps.map((x) => (
                  <p className="gap" key={x}>
                    ↗ {x}
                  </p>
                ))}
                <h4>Provenance</h4>
                <div className="provenanceGrid">
                  <span>
                    Quality lane
                    <b>{selected.qualityLane.replaceAll("_", " ")}</b>
                  </span>
                  <span>
                    Authority<b>{selected.authority}/100</b>
                  </span>
                  <span>
                    Confidence<b>{Math.round(selected.confidence * 100)}%</b>
                  </span>
                  <span>
                    Completeness
                    <b>{Math.round(selected.completeness * 100)}%</b>
                  </span>
                </div>
                <p>
                  {selected.vendor} · {selected.layers} known vendor layers ·{" "}
                  {selected.observations} observation
                  {selected.observations === 1 ? "" : "s"}
                </p>
                {selected.url && (
                  <a
                    className="sourceLink"
                    href={selected.url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Open original posting ↗
                  </a>
                )}
                <button
                  className="primary full"
                  onClick={() => void updateJobStatus(selected, "saved")}
                >
                  {selected.status === "Saved" ? "Saved to pipeline" : "Move to pipeline"}
                </button>
                <button className="secondary full" onClick={() => void rescreen(selected)}>
                  Re-screen with current profile
                </button>
                <button
                  className="secondary full"
                  onClick={() => {
                    setCorrectionRateMin(selected.rateMin);
                    setCorrectionRateMax(selected.rateMax);
                    setCorrectionLocation(selected.location);
                    setCorrectionOpen((current) => !current);
                  }}
                >
                  Correct extracted terms
                </button>
                {correctionOpen && (
                  <div className="correctionForm">
                    <label>Minimum rate<input type="number" min="20" max="500" value={correctionRateMin || ""} onChange={(event) => setCorrectionRateMin(+event.target.value)} /></label>
                    <label>Maximum rate<input type="number" min="20" max="500" value={correctionRateMax || ""} onChange={(event) => setCorrectionRateMax(+event.target.value)} /></label>
                    <label>Location<input value={correctionLocation} onChange={(event) => setCorrectionLocation(event.target.value)} /></label>
                    <button className="primary full" onClick={() => void saveJobCorrection(selected)}>Save and re-screen</button>
                  </div>
                )}
                <button className="secondary full">
                  Generate recruiter message
                </button>
              </aside>
            )}
          </section>
          {detailOpen && selected && (
            <div className="recruiterFinder">
              <span>
                {selected.recruiterEmail
                  ? "Contact found in posting"
                  : "Recruiter not named yet"}
              </span>
              {selected.recruiterEmail ? (
                <a href={`mailto:${selected.recruiterEmail}`}>
                  {selected.recruiterEmail}
                </a>
              ) : (
                <button onClick={() => findRecruiter(selected)}>
                  Find likely recruiter ↗
                </button>
              )}
              <small>
                {selected.recruiterEmail
                  ? "Posting-supplied evidence"
                  : "Searches public professional profiles; verify identity before outreach."}
              </small>
            </div>
          )}
        </>
      )}
      {tab === "pipeline" && (
        <section className="shell subpage">
          <p className="eyebrow">RELATIONSHIP-LED SEARCH</p>
          <h1>Opportunity pipeline</h1>
          <p className="lede">
            Track the recruiter, vendor chain, rate anchor, and next move—not
            just the application.
          </p>
          <div className="kanban">
            {["New", "Saved", "Contacted", "Submitted", "Interview", "Offer"].map((stage) => (
              <section key={stage}>
                <div className="columnHead">
                  <b>{stage}</b>
                  <span>
                    {catalog.filter((j) => j.status === stage).length}
                  </span>
                </div>
                {catalog
                  .filter((j) => j.status === stage)
                  .map((j) => (
                    <article
                      className="mini"
                      key={j.id}
                      role="button"
                      tabIndex={0}
                      aria-label={`Open ${j.title} at ${j.company}`}
                      onClick={() => openPipelineJob(j)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter" || event.key === " ") {
                          event.preventDefault();
                          openPipelineJob(j);
                        }
                      }}
                    >
                      <small>{j.company}</small>
                      <h3>{j.title}</h3>
                      <b>{j.rateMax ? `$${j.rateMin}–${j.rateMax}/hr` : "Rate undisclosed"}</b>
                      <p>{j.vendor}</p>
                      <span className="openOpportunity">Open opportunity →</span>
                    </article>
                  ))}
              </section>
            ))}
          </div>
          {detailOpen && selected && (
            <>
              <button
                className="pipelineBackdrop"
                aria-label="Close pipeline opportunity"
                onClick={() => setDetailOpen(false)}
              />
              <aside
                className="pipelineDrawer"
                aria-label={`Pipeline details for ${selected.title}`}
              >
                <button
                  className="pipelineClose"
                  aria-label="Close pipeline opportunity"
                  onClick={() => setDetailOpen(false)}
                >
                  ×
                </button>
                <p className="sectionLabel">PIPELINE OPPORTUNITY</p>
                <h2>{selected.title}</h2>
                <p className="company">{selected.company} · {selected.source}</p>
                <div className="pipelineFacts">
                  <span><b>{selected.score}</b> match</span>
                  <span><b>{selected.rateMax ? `$${selected.rateMin}–${selected.rateMax}/hr` : "Undisclosed"}</b> rate</span>
                  <span><b>{selected.c2c}</b> C2C</span>
                  <span><b>{selected.location}</b> location</span>
                </div>
                {selected.status === "Passed" || selected.status === "Rejected" ? (
                  <div className="archivedOutcome">
                    <span>
                      Archived outcome <b>{selected.status}</b>
                    </span>
                    <button
                      className="secondary"
                      type="button"
                      onClick={() => void updateJobStatus(selected, "saved")}
                    >
                      Reopen as saved
                    </button>
                  </div>
                ) : (
                  <label className="pipelineStage">
                    Pipeline stage
                    <select
                      value={selected.status.toLowerCase()}
                      onChange={(event) =>
                        void updateJobStatus(selected, event.target.value)
                      }
                    >
                      {[
                        "new",
                        "saved",
                        "contacted",
                        "submitted",
                        "interview",
                        "offer",
                      ].map((stage) => (
                        <option value={stage} key={stage}>
                          {stage.charAt(0).toUpperCase() + stage.slice(1)}
                        </option>
                      ))}
                    </select>
                  </label>
                )}
                <h4>Job description</h4>
                <div className="pipelineDescription">{selected.description}</div>
                {selected.url && (
                  <a
                    className="sourceLink"
                    href={selected.url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Open original posting ↗
                  </a>
                )}
                <section className="decisionPanel">
                  <p className="sectionLabel">OUTCOME FEEDBACK</p>
                  <h3>Close this pursuit with context</h3>
                  <p>
                    Structured reasons become tenant-isolated evaluation data for
                    future ranking improvements.
                  </p>
                  <label>
                    Primary reason
                    <select
                      value={decisionReason}
                      onChange={(event) => setDecisionReason(event.target.value)}
                    >
                      {DECISION_REASONS.map(([value, label]) => (
                        <option value={value} key={value}>{label}</option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Notes <small>Optional, up to 2,000 characters</small>
                    <textarea
                      rows={3}
                      maxLength={2000}
                      value={decisionNotes}
                      onChange={(event) => setDecisionNotes(event.target.value)}
                      placeholder="What should future ranking learn from this outcome?"
                    />
                  </label>
                  <div className="decisionActions">
                    <button
                      className="secondary"
                      onClick={() => void recordDecision(selected, "not_interested")}
                    >
                      No longer interested
                    </button>
                    <button
                      className="primary"
                      onClick={() => void recordDecision(selected, "denied")}
                    >
                      Log denial
                    </button>
                  </div>
                  <span className="saveState">{decisionState}</span>
                </section>
                {decisionHistory.length > 0 && (
                  <section className="decisionHistory">
                    <h4>Decision history</h4>
                    {decisionHistory.map((decision) => (
                      <article key={decision.id}>
                        <b>{decision.outcome === "denied" ? "Denied" : "Not interested"}</b>
                        <span>
                          {DECISION_REASONS.find(([value]) => value === decision.reason_code)?.[1] ?? decision.reason_code}
                        </span>
                        {decision.notes && <p>{decision.notes}</p>}
                        <small>{new Date(decision.created_at).toLocaleString()}</small>
                      </article>
                    ))}
                  </section>
                )}
              </aside>
            </>
          )}
        </section>
      )}
      {tab === "setup" && (
        <section className="shell subpage coreSetupPage">
          <p className="eyebrow">FIRST-RUN CORE SETUP</p>
          <h1>Connect your brain. Build your feed.</h1>
          <p className="lede">
            C2CDirect can run with local rules, a model on your machine, or any
            OpenAI-compatible endpoint. Core starts with no jobs: you decide
            which public boards, authorized inboxes, and private files enter
            the screening pipeline.
          </p>
          <div className="setupProgress">
            <span className={profileReady ? "done" : ""}><b>1</b> Profile</span>
            <span className={modelConnection ? "done" : ""}><b>2</b> AI brain</span>
            <span className={apiState.startsWith("Live") && catalog.length ? "done" : ""}><b>3</b> Job feed</span>
          </div>
          <div className="coreSetupGrid">
            <section className="setupCard profileSetupCard">
              <div className="setupCardHead"><i>01</i><div><p className="sectionLabel">MATCHING CONTEXT</p><h2>Tell it what good looks like</h2></div></div>
              <p>
                Your target roles, rates, location, skills, and résumé drive
                every fit score. You can start importing before uploading a résumé.
              </p>
              <div className="setupSummary">
                <span><b>${profile.target_rate}/hr</b> target rate</span>
                <span><b>{profile.target_roles.length}</b> target roles</span>
                <span><b>{profile.core_skills.length + profile.ai_skills.length}</b> skills</span>
              </div>
              <button className="secondary full" onClick={() => setTab("profile")}>Edit matching profile</button>
            </section>
            <section className="setupCard modelConnectionCard">
              <div className="setupCardHead"><i>02</i><div><p className="sectionLabel">BRING YOUR OWN AI</p><h2>Choose the brain</h2></div></div>
              <label>
                Quick choice
                <select
                  value={modelProvider === "deterministic" ? "deterministic" : modelBaseUrl.includes(":11434") ? "ollama" : modelBaseUrl.includes(":1234") ? "lmstudio" : "custom"}
                  onChange={(event) => chooseModelPreset(event.target.value)}
                >
                  <option value="deterministic">Local rules · no AI cost</option>
                  <option value="ollama">Ollama on this machine</option>
                  <option value="lmstudio">LM Studio on this machine</option>
                  <option value="custom">OpenAI-compatible endpoint</option>
                </select>
              </label>
              {modelProvider === "openai_compatible" && (
                <div className="modelFields">
                  <label>Endpoint URL<input value={modelBaseUrl} placeholder="https://provider.example/v1" onChange={(event) => setModelBaseUrl(event.target.value)} /></label>
                  <label>Model name<input value={modelName} placeholder="model-name" onChange={(event) => setModelName(event.target.value)} /></label>
                  <label>API key<input type="password" autoComplete="new-password" value={modelApiKey} placeholder={modelConnection?.api_key_configured ? "Saved securely · leave blank to keep" : "Optional for local models"} onChange={(event) => setModelApiKey(event.target.value)} /></label>
                  <div className="priceFields">
                    <label>Input $ / 1M<input type="number" min="0" step="0.01" value={modelInputCost} onChange={(event) => setModelInputCost(+event.target.value)} /></label>
                    <label>Output $ / 1M<input type="number" min="0" step="0.01" value={modelOutputCost} onChange={(event) => setModelOutputCost(+event.target.value)} /></label>
                  </div>
                </div>
              )}
              <div className="setupActions">
                <button className="secondary" onClick={testModel}>Test connection</button>
                <button className="primary" onClick={saveModel}>Save AI brain</button>
              </div>
              <span className="setupState">{modelState}</span>
              <small>Credentials are encrypted before storage and are never returned to the browser.</small>
            </section>
            <section className="setupCard importCard">
              <div className="setupCardHead"><i>03</i><div><p className="sectionLabel">YOUR OPPORTUNITIES</p><h2>Build your private job feed</h2></div></div>
              <p>
                Core never arrives with pre-filled jobs or a managed feed. Pull
                from the sources you authorize, then let your AI brain extract,
                rank, and explain the work that fits.
              </p>
              {!profileReady && (
                <div className="setupGate">
                  <b>Finish your matching profile first.</b>
                  <span>Core will not acquire or screen jobs against placeholder preferences.</span>
                  <button className="secondary" onClick={() => setTab("profile")}>Complete profile</button>
                </div>
              )}
              <div className="sourceMethods">
                <article>
                  <span>PUBLIC FIRST-PARTY BOARDS</span>
                  <h3>Run a profile-guided scan</h3>
                  <p>Query reviewed Greenhouse, Ashby, and Lever boards only when you ask. Your profile narrows the results before model screening.</p>
                  {sourceTargets.length > 0 && (
                    <details className="sourcePicker">
                      <summary>{selectedSources.length} of {sourceTargets.length} sources selected</summary>
                      <div>
                        {sourceTargets.map((source) => (
                          <label key={`${source.adapter}:${source.slug}`}>
                            <input
                              type="checkbox"
                              checked={selectedSources.includes(source.slug)}
                              onChange={(event) => setSelectedSources((current) =>
                                event.target.checked
                                  ? [...current, source.slug]
                                  : current.filter((slug) => slug !== source.slug),
                              )}
                            />
                            {source.organization_name}
                          </label>
                        ))}
                      </div>
                    </details>
                  )}
                  <button className="primary" onClick={scan} disabled={scanning || !profileReady}>{scanning ? "Scanning public boards…" : "Find jobs with my brain"}</button>
                  <small>{apiState}</small>
                </article>
                <article>
                  <span>AUTHORIZED RECRUITER INBOX</span>
                  <h3>Pull alerts and recruiter mail</h3>
                  <p>Connect a read-only mailbox. C2CDirect imports job messages, ignores unrelated mail, and deduplicates repeat alerts.</p>
                  {emailConnections.map((connection) => (
                    <button className="primary" disabled={!profileReady} key={connection.id} onClick={() => syncEmail(connection.provider)}>Sync {connection.provider === "gmail" ? "Gmail" : "Outlook"} now</button>
                  ))}
                  {!emailConnections.length && (
                    <div className="mailConnectActions">
                      <button className="secondary" disabled={emailOAuthStatus?.providers.gmail.configured === false} onClick={() => connectEmail("gmail")}>Connect Gmail</button>
                      <button className="secondary" disabled={emailOAuthStatus?.providers.microsoft.configured === false} onClick={() => connectEmail("microsoft")}>Connect Outlook</button>
                    </div>
                  )}
                  {emailOAuthStatus && !emailOAuthStatus.providers.gmail.configured && !emailOAuthStatus.providers.microsoft.configured && (
                    <small>Mailbox OAuth is optional and not configured by this Core operator yet.</small>
                  )}
                  <small>{emailState}</small>
                </article>
                <article className="webScoutCard">
                  <span>AI-POWERED WEB DISCOVERY</span>
                  <h3>Scout the open web for requisitions</h3>
                  <p>Build a search from your roles and skills, gather public results only when you ask, then let your AI brain extract terms and rank every requisition.</p>
                  <label>
                    Search service
                    <select
                      value={webSearchProvider}
                      onChange={(event) => {
                        const provider = event.target.value as WebSearchConnection["provider"];
                        setWebSearchProvider(provider);
                        setWebSearchBaseUrl(provider === "searxng" ? "http://searxng:8080" : "");
                        setWebSearchState("Enter the search connection, then test it");
                      }}
                    >
                      <option value="disabled">Off</option>
                      <option value="searxng">SearXNG · self-hosted</option>
                      <option value="tavily">Tavily</option>
                      <option value="brave">Brave Search</option>
                    </select>
                  </label>
                  {webSearchProvider !== "disabled" && (
                    <div className="webScoutFields">
                      {webSearchProvider === "searxng" && (
                        <label>Search endpoint<input value={webSearchBaseUrl} onChange={(event) => setWebSearchBaseUrl(event.target.value)} placeholder="http://searxng:8080" /></label>
                      )}
                      {webSearchProvider !== "searxng" && (
                        <label>API key<input type="password" autoComplete="new-password" value={webSearchApiKey} onChange={(event) => setWebSearchApiKey(event.target.value)} placeholder={webSearchConnection?.api_key_configured ? "Saved securely · leave blank to keep" : "Search API key"} /></label>
                      )}
                      <div className="webScoutActions">
                        <button className="secondary" onClick={testWebSearch}>Test search</button>
                        <button className="secondary" onClick={saveWebSearch}>Save search</button>
                      </div>
                      <label>Optional search focus<input value={webSearchFocus} onChange={(event) => setWebSearchFocus(event.target.value)} placeholder="Agentic AI engineer, remote C2C" /></label>
                      <button className="primary" onClick={runWebScout} disabled={!profileReady || !webSearchConnection?.configured || webSearching}>{webSearching ? "Scouting the web…" : "Run Web Scout"}</button>
                    </div>
                  )}
                  <small>{webSearchState}</small>
                </article>
              </div>
              <div className="importDivider"><span>OR IMPORT A LIST YOU ALREADY HAVE</span></div>
              <label className="importDrop">
                Choose a .csv or .json file
                <input
                  type="file"
                  accept=".csv,.json,text/csv,application/json"
                  onChange={async (event) => {
                    const file = event.target.files?.[0];
                    if (file) inspectImport(await file.text());
                  }}
                />
              </label>
              <textarea
                rows={8}
                value={importText}
                onChange={(event) => inspectImport(event.target.value)}
                placeholder={'title,company,description,location,rate_min,rate_max,source_url\n"AI Engineer","Acme","Contract role with C2C terms and enough detail for screening.","Remote",130,160,"https://example.com/job"'}
              />
              <div className="importFooter">
                <span className={importCount ? "ready" : ""}>{importState}</span>
                <button className="primary" disabled={!profileReady || !importCount} onClick={importJobs}>Import and screen</button>
              </div>
              <small>Maximum 250 jobs per batch. Imported descriptions stay in your own Core database.</small>
              <section className="runHistory">
                <div><p className="sectionLabel">ACQUISITION HISTORY</p><h3>Background runs</h3></div>
                {acquisitionRuns.length ? acquisitionRuns.slice(0, 8).map((run) => (
                  <article key={run.id}>
                    <b>{run.kind.replaceAll("_", " ")}</b>
                    <span className={`runStatus ${run.status}`}>{run.status}</span>
                    <small>{run.error_code ? `Stopped safely · ${run.error_code}` : `${run.attempts ?? 0} attempt${run.attempts === 1 ? "" : "s"}`}</small>
                    {run.status === "failed" || run.status === "cancelled" ? <button className="secondary" onClick={() => void retryAcquisition(run)}>Retry</button> : null}
                    {run.status === "queued" || (run.status === "running" && !run.cancel_requested) ? <button className="secondary" onClick={() => void cancelAcquisition(run)}>{run.status === "running" ? "Stop safely" : "Cancel"}</button> : null}
                    {run.cancel_requested && run.status === "running" ? <small>Stopping after the current item…</small> : null}
                  </article>
                )) : <p>No acquisition runs yet.</p>}
              </section>
            </section>
          </div>
        </section>
      )}
      {SHOW_EXPERIMENTAL_TABS && tab === "lab" && (
        <section className="shell subpage">
          <p className="eyebrow">MARKET-DEMAND → PORTFOLIO PROOF</p>
          <h1>AI Build Lab</h1>
          <p className="lede">
            Every project closes a skill gap found in real high-rate
            postings—and doubles as proof that you can ship production AI
            systems.
          </p>
          <div className="labGrid">
            {PROJECTS.map((p) => (
              <article className="project" key={p.title}>
                <div className="match">
                  Seen in <b>{p.match}</b> target roles
                </div>
                <h2>{p.title}</h2>
                <p className="stack">{p.stack}</p>
                <div className="progress">
                  <span style={{ width: `${p.progress}%` }} />
                </div>
                <small>{p.progress}% portfolio-ready</small>
                <h4>Next high-signal proof</h4>
                <p>{p.next}</p>
                <button className="secondary">Open build brief →</button>
              </article>
            ))}
          </div>
          <div className="architecture">
            <div>
              <p className="sectionLabel">REFERENCE ARCHITECTURE</p>
              <h2>The product is the portfolio.</h2>
              <p>
                n8n schedules source ingestion → FastAPI validates inputs →
                LangGraph orchestrates screening → retrieval grounds fit
                explanations → Pydantic returns structured results → this
                dashboard drives action.
              </p>
            </div>
            {["n8n", "FastAPI", "Pydantic", "LangGraph", "RAG", "Next.js"].map(
              (x) => (
                <span key={x}>{x}</span>
              ),
            )}
          </div>
        </section>
      )}
      {tab === "control" && (
        <section className="shell subpage control">
          <p className="eyebrow">SELF-HOSTED AI OPERATIONS</p>
          <h1>Control Room</h1>
          <p className="lede">
            See which model C2CDirect is using, what every run costs, and how
            today&apos;s usage compares with your budget.
          </p>
          <div className="controlStatus">
            <span className={controlRoom ? "healthy" : "pending"}>
              {controlState}
            </span>
            <button
              className="secondary"
              type="button"
              onClick={() => {
                setControlRefresh((current) => current + 1);
              }}
            >
              Refresh
            </button>
            <a className="secondary" href="/api/v1/export" download>Export my Core data</a>
          </div>
          <div className="metricGrid">
            {[
              [
                `$${(controlRoom?.today_spend ?? 0).toFixed(4)}`,
                "AI spend today",
                `of $${(controlRoom?.policy.daily_limit_usd ?? 0).toFixed(2)} daily budget`,
              ],
              [
                `$${(controlRoom?.month_spend ?? 0).toFixed(4)}`,
                "Last 30 days",
                `${controlRoom?.month_runs ?? 0} metered ${(controlRoom?.month_runs ?? 0) === 1 ? "run" : "runs"}`,
              ],
              [
                `$${(controlRoom?.average_cost ?? 0).toFixed(4)}`,
                "Average run cost",
                `${((controlRoom?.input_tokens ?? 0) + (controlRoom?.output_tokens ?? 0)).toLocaleString()} tokens`,
              ],
              [
                controlRoom?.runtime.mode === "model-assisted" ? "Configured" : "Local rules",
                "Model runtime",
                controlRoom?.runtime.model ?? "Loading configuration",
              ],
            ].map((x) => (
              <article key={x[1]}>
                <strong>{x[0]}</strong>
                <b>{x[1]}</b>
                <small>{x[2]}</small>
              </article>
            ))}
          </div>
          <section className="spendChart">
            <div className="panelHead">
              <div>
                <p className="sectionLabel">14-DAY SPEND</p>
                <h2>Daily model cost</h2>
              </div>
              <small>Provider-reported tokens when available</small>
            </div>
            <div className="spendBars" aria-label="Daily AI spending">
              {(controlRoom?.daily.length
                ? controlRoom.daily
                : [{ date: new Date().toISOString().slice(0, 10), spend: 0, runs: 0 }]
              ).map((day) => {
                const maximum = Math.max(
                  0.000001,
                  ...(controlRoom?.daily.map((item) => item.spend) ?? [0]),
                );
                return (
                  <div key={day.date} title={`${day.date}: $${day.spend.toFixed(4)} · ${day.runs} runs`}>
                    <i style={{ height: `${Math.max(3, (day.spend / maximum) * 100)}%` }} />
                    <span>{new Date(`${day.date}T12:00:00`).toLocaleDateString(undefined, { month: "short", day: "numeric" })}</span>
                  </div>
                );
              })}
            </div>
          </section>
          <div className="controlGrid">
            <section className="tracePanel">
              <div className="panelHead">
                <div>
                  <p className="sectionLabel">RECENT METERED RUNS</p>
                  <h2>Usage ledger</h2>
                </div>
                <span className="healthy">Tenant isolated</span>
              </div>
              {controlRoom?.recent_runs.length ? (
                controlRoom.recent_runs.map((run, index) => (
                  <div className="traceRow" key={run.id}>
                    <i>{index + 1}</i>
                    <b>{run.operation.replaceAll("_", " ")}</b>
                    <span>{run.model}</span>
                    <em>${run.cost_usd.toFixed(4)}</em>
                  </div>
                ))
              ) : (
                <div className="controlEmpty">
                  No model usage yet. Screening runs will appear here.
                </div>
              )}
            </section>
            <section className="policyPanel">
              <p className="sectionLabel">ACTIVE COST POLICY</p>
              <h2>Budget gates</h2>
              {[
                ["Tenant daily limit", `$${(controlRoom?.policy.daily_limit_usd ?? 0).toFixed(2)}`],
                ["Maximum run cost", `$${(controlRoom?.policy.per_run_limit_usd ?? 0).toFixed(2)}`],
                ["Approval threshold", `$${(controlRoom?.policy.require_approval_above_usd ?? 0).toFixed(2)}`],
                ["Maximum tokens", (controlRoom?.policy.max_total_tokens ?? 0).toLocaleString()],
                ["Maximum graph steps", String(controlRoom?.policy.max_graph_steps ?? 0)],
                ["Maximum retries", String(controlRoom?.policy.max_retries ?? 0)],
              ].map((x) => (
                <div className="policy" key={x[0]}>
                  <span>{x[0]}</span>
                  <b>{x[1]}</b>
                </div>
              ))}
              <small className="policyHint">
                Self-hosted limits are set in your private environment file.
              </small>
            </section>
          </div>
          <section className="modelSetup">
            <div>
              <p className="sectionLabel">BRING YOUR OWN MODEL</p>
              <h2>{controlRoom?.runtime.mode === "model-assisted" ? "Your model is configured" : "Connect an OpenAI-compatible model"}</h2>
              <p>
                C2CDirect Core works with Ollama, vLLM, LM Studio, LocalAI, or
                any hosted endpoint that implements <code>/v1/chat/completions</code>.
                If the endpoint fails, deterministic screening remains available.
              </p>
            </div>
            <div className="runtimeFacts">
              <span>Mode <b>{controlRoom?.runtime.mode ?? "checking"}</b></span>
              <span>Provider <b>{controlRoom?.runtime.provider ?? "checking"}</b></span>
              <span>Model <b>{controlRoom?.runtime.model ?? "checking"}</b></span>
              <span>Endpoint <b>{controlRoom?.runtime.base_url_configured ? "configured" : "not configured"}</b></span>
              <span>Input price <b>${(controlRoom?.runtime.input_cost_per_million ?? 0).toFixed(2)} / 1M</b></span>
              <span>Output price <b>${(controlRoom?.runtime.output_cost_per_million ?? 0).toFixed(2)} / 1M</b></span>
            </div>
            <ol>
              <li>Open Setup and choose local rules, Ollama, LM Studio, or a compatible endpoint.</li>
              <li>Test the private connection and save the encrypted configuration.</li>
              <li>Import jobs; every model run and cost appears here.</li>
            </ol>
            <button className="primary" type="button" onClick={() => setTab("setup")}>Open guided setup</button>
          </section>
        </section>
      )}
      {SHOW_EXPERIMENTAL_TABS && tab === "workspace" && (
        <section className="shell subpage workspacePage">
          <p className="eyebrow">FROM FIRST SIGNAL TO PAID ENGAGEMENT</p>
          <h1>Workspace setup</h1>
          <p className="lede">
            Connect your professional evidence and approved opportunity sources.
            C2CDirect handles normalization, screening, governance, and the
            next-action queue.
          </p>
          <div className="setupGrid">
            <section>
              <p className="sectionLabel">LAUNCH CHECKLIST</p>
              {[
                [
                  "Candidate profile",
                  "Complete",
                  "Resume, rate floor, target roles",
                ],
                [
                  "Direct ATS intake",
                  "20 connected",
                  "Reviewed first-party boards",
                ],
                [
                  "Mailbox intake",
                  emailConnections.length
                    ? "Connected"
                    : "Authorization needed",
                  emailState,
                ],
                ["Recruiter workflow", "Ready", "n8n webhook verified"],
                [
                  "Public exposure",
                  "Disabled",
                  "Local safety gates remain active",
                ],
              ].map((x, i) => (
                <article className="setupRow" key={x[0]}>
                  <i>{i + 1}</i>
                  <div>
                    <b>{x[0]}</b>
                    <small>{x[2]}</small>
                  </div>
                  <span>{x[1]}</span>
                </article>
              ))}
            </section>
            <section className="sourcePanel">
              <p className="sectionLabel">AUTHORIZED MAILBOX INTAKE</p>
              <h2>Recruiter and alert email</h2>
              <p className="mailState">{emailState}</p>
              {emailConnections.map((connection) => (
                <div className="source" key={connection.id}>
                  <div>
                    <b>
                      {connection.provider === "gmail"
                        ? "Gmail"
                        : "Microsoft Outlook"}
                    </b>
                    <small>
                      {connection.mailbox_address ?? "Authorized mailbox"}
                    </small>
                  </div>
                  <button
                    className="sourceSync"
                    onClick={() => syncEmail(connection.provider)}
                  >
                    Sync now
                  </button>
                </div>
              ))}
              <button
                className="primary full"
                onClick={() => connectEmail("gmail")}
              >
                Connect Gmail securely
              </button>
              <button
                className="secondary full"
                onClick={() => connectEmail("microsoft")}
              >
                Connect Outlook securely
              </button>
              <small className="privacyNote">
                Read-only OAuth access. Tokens are encrypted locally. No
                passwords or private keys belong in chat.
              </small>
            </section>
          </div>
          <div className="pricing">
            <div>
              <p className="sectionLabel">
                PLANS BUILT FOR INDEPENDENT ENGINEERS
              </p>
              <h2>Start open. Pay for leverage.</h2>
              <p>
                Self-host the core for free, or use the managed cloud for
                automation, data operations, and support.
              </p>
            </div>
            {[
              ["Community", "$0", "100 screenings · BYO model · self-hosted"],
              ["Solo", "$39", "2,000 screenings · 3 sources · outreach"],
              ["Pro", "$99", "10,000 screenings · observability · 10 profiles"],
              ["Team", "$299", "50,000 screenings · 25 seats · governance"],
            ].map((x, i) => (
              <article className={i === 2 ? "featured" : ""} key={x[0]}>
                <b>{x[0]}</b>
                <strong>
                  {x[1]}
                  <small>/mo</small>
                </strong>
                <p>{x[2]}</p>
                <button className={i === 2 ? "primary" : "secondary"}>
                  {i === 0 ? "View source" : "Choose plan"}
                </button>
              </article>
            ))}
          </div>
          <div className="privacyStrip">
            <b>Your evidence stays yours.</b>
            <span>Tenant-isolated storage</span>
            <span>Encrypted OAuth tokens</span>
            <span>Read-only mailbox scopes</span>
            <span>Bring-your-own-model ready</span>
          </div>
        </section>
      )}
      {tab === "profile" && (
        <section className="shell subpage profilePage">
          <p className="eyebrow">YOUR MATCHING IDENTITY</p>
          <h1>Candidate profile</h1>
          <p className="lede">
            Keep the résumé, commercial targets, preferred work setup, and
            skills that drive screening in one private profile.
          </p>
          <div className="profileGrid">
            <section className="profileForm">
              <p className="sectionLabel">PROFILE DETAILS</p>
              <label>
                Display name
                <input
                  value={profile.display_name}
                  onChange={(e) =>
                    setProfile({ ...profile, display_name: e.target.value })
                  }
                />
              </label>
              <label>
                Professional headline
                <input
                  value={profile.headline}
                  onChange={(e) =>
                    setProfile({ ...profile, headline: e.target.value })
                  }
                />
              </label>
              <label>
                Short bio
                <textarea
                  rows={4}
                  value={profile.bio}
                  onChange={(e) =>
                    setProfile({ ...profile, bio: e.target.value })
                  }
                />
              </label>
              <div className="profileFields">
                <label>
                  Minimum hourly rate
                  <input
                    type="number"
                    min="20"
                    max="500"
                    value={profile.min_rate}
                    onChange={(e) =>
                      setProfile({ ...profile, min_rate: +e.target.value })
                    }
                  />
                </label>
                <label>
                  Target hourly rate
                  <input
                    type="number"
                    min="20"
                    max="500"
                    value={profile.target_rate}
                    onChange={(e) =>
                      setProfile({ ...profile, target_rate: +e.target.value })
                    }
                  />
                </label>
              </div>
              <ChipInput
                label="Target roles"
                values={profile.target_roles}
                suggestions={profileSuggestions.roles}
                placeholder="Add a target role"
                onChange={(target_roles) =>
                  setProfile({ ...profile, target_roles })
                }
              />
              <ChipInput
                label="Preferred locations"
                values={profile.locations}
                suggestions={profileSuggestions.locations}
                placeholder="Add a location"
                onChange={(locations) =>
                  setProfile({ ...profile, locations })
                }
              />
              <ChipInput
                label="Core technologies"
                values={profile.core_skills}
                suggestions={profileSuggestions.coreSkills}
                placeholder="Add a technology"
                onChange={(core_skills) =>
                  setProfile({ ...profile, core_skills })
                }
              />
              <ChipInput
                label="AI technologies"
                values={profile.ai_skills}
                suggestions={profileSuggestions.aiSkills}
                placeholder="Add an AI technology"
                onChange={(ai_skills) =>
                  setProfile({ ...profile, ai_skills })
                }
              />
            <div className="choiceGroup">
              <span>Seniority</span>
              {[
                "entry",
                "mid",
                "senior",
                "lead",
                "staff",
                "principal",
                "architect",
              ].map((item) => (
                <label key={item}>
                  <input
                    type="checkbox"
                    checked={profile.seniority_levels.includes(item)}
                    onChange={(e) =>
                      setProfile({
                        ...profile,
                        seniority_levels: e.target.checked
                          ? [...profile.seniority_levels, item]
                          : profile.seniority_levels.filter(
                              (value) => value !== item,
                            ),
                      })
                    }
                  />
                  {item}
                </label>
              ))}
            </div>
            <div className="choiceGroup">
              <span>Work arrangement</span>
                {["remote", "hybrid", "onsite"].map((item) => (
                  <label key={item}>
                    <input
                      type="checkbox"
                      checked={profile.work_modes.includes(item)}
                      onChange={(e) =>
                        setProfile({
                          ...profile,
                          work_modes: e.target.checked
                            ? [...profile.work_modes, item]
                            : profile.work_modes.filter(
                                (value) => value !== item,
                              ),
                        })
                      }
                    />
                    {item}
                  </label>
                ))}
              </div>
              <label className="profileCheck">
                <input
                  type="checkbox"
                  checked={profile.require_c2c}
                  onChange={(e) =>
                    setProfile({ ...profile, require_c2c: e.target.checked })
                  }
                />{" "}
                Require C2C-compatible opportunities
              </label>
              <button className="primary" onClick={saveProfile}>
                Save profile
              </button>
              <span className="saveState">{profileState}</span>
            </section>
            <aside className="resumePanel">
              <p className="sectionLabel">PRIMARY RÉSUMÉ</p>
              <h2>{profile.resume?.file_name ?? "No résumé uploaded"}</h2>
              {profile.resume && (
                <p>
                  {Math.ceil(profile.resume.size_bytes / 1024)} KB · private
                  tenant storage
                </p>
              )}
              <label className="uploadButton">
                {profile.resume ? "Replace résumé" : "Upload résumé"}
                <input
                  type="file"
                  accept=".pdf,.docx,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) uploadResume(file);
                  }}
                />
              </label>
              {profile.resume && (
                <button className="secondary full" onClick={removeResume}>
                  Remove résumé
                </button>
              )}
              <small>
                PDF, DOCX, or TXT · 5 MB maximum. The file remains
                tenant-isolated and is never included in public examples or
                unrestricted telemetry.
              </small>
            </aside>
          </div>
        </section>
      )}
      <footer className="licenseFooter">
        <span>
          © 2026 C2CDirect contributors · AGPL-3.0-only · No warranty
        </span>
        {SOURCE_URL ? (
          <a href={SOURCE_URL} target="_blank" rel="noreferrer">
            View corresponding source ↗
          </a>
        ) : (
          <span>Public source repository · Coming soon</span>
        )}
      </footer>
    </main>
  );
}
