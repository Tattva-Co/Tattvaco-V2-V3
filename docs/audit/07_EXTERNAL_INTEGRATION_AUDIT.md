# 07 — External Integration Audit

**Doc ID:** TFD-AUDIT-007 · **Audit date:** 2026-11-05

## 1. What exists
| Integration | Code evidence | Status |
|---|---|---|
| LLM providers (OpenAI / Anthropic / Gemini) | `packages/core/config.py` key fields; comment "not yet consumed by any code path"; `model_gateway_provider: Literal["mock"]` | NOT_IMPL (config only) |
| Higgsfield | `higgsfield_integration_mode: Literal["manual_export"]`, URL and key fields | NOT_IMPL (config intent only) |
| Object storage | `StorageService` ABC; `factory.get_storage` accepts only `"local"` | Local only; abstraction exists (good) |
| Image / video / voice / lip-sync / mocap / body-scan providers | none | NOT_IMPL |
| MCP clients | none | NOT_IMPL |
| Manual export package / import mapping | none | NOT_IMPL |
| Webhooks (inbound) | none | NOT_IMPL |

**No code path calls any external network service.** Nothing in the repository should be described as "connected", "integrated" or "export-ready".

## 2. Candidate ecosystem (Master Prompt §12.2)
All 14 candidates are **UNVERIFIED** as of this audit:
- FLUX.2, Midjourney
- Higgsfield, Seedance, Kling, Runway (incl. Act-Two), Wan
- Autodesk Flow Studio, HeyGen
- Rokoko, Move AI, Size Stream
- ElevenLabs, Sync Labs

Phase B `INTEGRATION_ARCHITECTURE.md` carries the verification register. Each entry records the official URL, API/MCP availability, auth, limits, commercial terms, consent implications and manual alternative, with source and date. Anything not confirmed from an official source stays UNVERIFIED and is not built against.

Carried forward from Gap Report v1.0 (policy positions; re-verify at implementation time):
- **Midjourney:** manual handoff only. Its Terms of Service prohibit automated access (Gap Report source S1). Do not build browser or Discord automation.
- **Higgsfield:** API and MCP are separate contracts and need separate adapters. Start with manual package mode (Gap Report S2/S3).

## 3. Architectural readiness
| Required element | Present? |
|---|---|
| Provider-neutral Shot Specification | No |
| Provider capability registry with versioned snapshots | No |
| Adapter interface (compile, validate, submit, poll, normalize) | No |
| Separate API vs MCP vs manual adapters | No |
| Generation job / attempt / unknown-outcome model | No (`workflow_runs` is internal-graph only) |
| Cost estimate + explicit spend approval gate | No |
| Consent gate before likeness/voice use | No |
| Credential vault / per-org provider connections | No |
| Contract tests against recorded provider fixtures | No |

## 4. Recommendation
Build the **manual execution loop first** (V1-25/26/27): Shot Spec → package compiler → manifest + checksum export → manual run → import → map to shot → review. It is required regardless of any provider, is permanent, and exercises the entire provenance and approval chain. Connected adapters (V2) then plug into the same package and import contracts.
