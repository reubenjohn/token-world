---
phase: 01
slug: graph-foundation
status: verified
threats_open: 0
asvs_level: 1
created: 2026-04-11
---

# Phase 01 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Mechanic -> KnowledgeGraph API | Mechanics (untrusted in later phases — LLM-generated code) mutate graph through the API | Node/edge properties (JSON-serializable primitives) |
| SQLite file I/O | Graph state read/written to SQLite on local filesystem | Serialized graph JSON blobs, event records |
| Snapshot summary input | Summary strings come from tick summaries (potentially LLM-generated content) | Plain text strings |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-01-01 | Tampering | KnowledgeGraph.set() | mitigate | Validate property values against ALLOWED_PROPERTY_TYPES before storing; deepcopy mutable values to prevent reference mutation | closed |
| T-01-02 | Tampering | GraphPersistence.load() | mitigate | Use allow_nan=False in JSON serialization to reject invalid values; always pass directed=True, multigraph=False to node_link_graph | closed |
| T-01-03 | Information Disclosure | GraphPersistence SQLite | accept | See Accepted Risks Log | closed |
| T-01-04 | Denial of Service | KnowledgeGraph.add_node() | accept | See Accepted Risks Log | closed |
| T-01-05 | Elevation of Privilege | claim_id() | mitigate | claim_id only returns string IDs — used as dict keys in NetworkX, no path traversal or injection possible | closed |
| T-01-06 | Tampering | snapshot summary | accept | See Accepted Risks Log | closed |
| T-01-07 | Denial of Service | snapshot bloat | mitigate | Count-based retention (max 50 snapshots). prune_snapshots() deletes oldest when limit exceeded. Event compaction removes pre-snapshot events. | closed |
| T-01-08 | Tampering | restore() | mitigate | Snapshot data serialized by our own save_snapshot(). Always deserialize with directed=True, multigraph=False to prevent graph type confusion. | closed |
| T-01-09 | Information Disclosure | CLAUDE.md | accept | See Accepted Risks Log | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-01 | T-01-03 | SQLite file on local filesystem, single-user hobby project. File permissions inherited from OS. No encryption needed for v1. | Plan threat model | 2026-04-12 |
| AR-02 | T-01-04 | No node count limits for v1. Graph expected to be small (< 1000 nodes). Monitor in Phase 3 if needed. | Plan threat model | 2026-04-12 |
| AR-03 | T-01-06 | Summary is display-only metadata, not executable. No injection risk since stored as parameterized SQL TEXT. | Plan threat model | 2026-04-12 |
| AR-04 | T-01-09 | CLAUDE.md is a public repo file. No secrets or credentials documented. All content is architectural documentation. | Plan threat model | 2026-04-12 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-04-11 | 9 | 9 | 0 | gsd-secure-phase |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-04-11
