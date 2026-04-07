# Enrichment and AI Features

This document explains how OER_Phoenix uses enrichment, embeddings, and optional AI-assisted features in a way that is understandable for library teams.

The aim is to make these features useful without making them opaque. In OER_Phoenix, AI is optional, inspectable, and intended to support professional judgement rather than replace it.

## What “enrichment” means

In OER_Phoenix, enrichment means adding helpful derived information to a record after it has been harvested from its original source.

Examples may include:

- A short summary generated from existing metadata.
- Suggested subjects or keywords.
- A quality or completeness score based on defined criteria.
- Additional normalised fields that improve filtering and discovery.

Enrichment should never overwrite or hide the original source metadata. Source fields and derived fields should remain distinguishable in both the data model and the user interface.

## Types of enrichment

### Rules-based enrichment

Rules-based enrichment uses deterministic logic rather than an LLM.

Examples:

- Mapping source-specific values into normalised categories.
- Extracting keywords from controlled fields.
- Inferring record completeness from the presence or absence of expected metadata.

This approach is often easier to audit and may be preferred where institutions want minimal AI usage.

### AI-assisted enrichment

AI-assisted enrichment uses an LLM or similar service to generate or suggest additional metadata.

Examples:

- Generating a plain-language summary.
- Suggesting subjects from a title and description.
- Rewriting a noisy description into a cleaner short abstract.

These outputs should be treated as suggestions, not authoritative metadata.

## Embeddings and semantic search

An embedding is a numeric representation of text. In practice, this allows the system to compare records by meaning as well as by exact words.

This helps users find resources that are conceptually related even when they do not share the same keywords.

Example:

- A search for “introductory statistics” might also retrieve records described as “basic data analysis” if embeddings are enabled.

Embeddings support semantic search, but they should be documented clearly because their effect on ranking can be less obvious to users than keyword matching.

## Retrieve-and-generate features

OER_Phoenix may optionally support retrieve-and-generate workflows, often abbreviated as RAG.

In plain language, this means the system:

1. Retrieves a set of records from search results.
2. Passes those records to an LLM.
3. Produces a synthesised answer, summary, or overview.

These responses should be clearly labelled as generated text and should link back to the underlying records where possible.

## Provenance and labelling

Every enriched field should be traceable.

Recommended provenance labels include:

- Source metadata
- Normalised metadata
- Rules-based enrichment
- AI-generated enrichment
- Quality assessment output

The user interface should make these distinctions visible so that staff and learners can understand what they are looking at.

## Quality scoring

Quality scores should be interpretable and documented.

A score may reflect factors such as:

- Metadata completeness
- Presence of licence information
- Presence of subject information
- Availability of descriptive text
- Technical accessibility indicators

These scores should support review and triage, not act as final judgements on pedagogical value.

## Deployment profiles

### Minimal profile

Recommended when an institution wants a low-risk baseline.

Typical characteristics:

- Harvesting enabled.
- Keyword search enabled.
- Rules-based enrichment only, or no enrichment.
- No external LLM calls.
- No embeddings.

### Full profile

Recommended when an institution wants to explore enhanced discovery and enrichment.

Typical characteristics:

- Harvesting enabled.
- Keyword and semantic search enabled.
- AI-assisted enrichment enabled.
- Optional retrieve-and-generate tools for staff.
- Strong provenance labels and policy controls.

## Governance and privacy

Institutions should decide:

- Which AI features are enabled.
- Which users can access staff-only tools.
- Whether external AI providers are acceptable.
- What data can be sent to third-party services.
- How prompts, outputs, and logs are retained.

As a general principle, OER_Phoenix should minimise unnecessary data sharing and document what each backend receives.

## Good practice for library teams

- Start with a minimal profile and introduce AI features gradually.
- Test enriched metadata against real library use-cases.
- Review AI-generated summaries and subjects before relying on them operationally.
- Keep local policies and user guidance close to the interface.
- Use explanation and labelling features as part of information literacy and AI literacy teaching.

## Related documents

- `docs/goals-2026.md`
- `docs/architecture.md`
- `docs/security.md`
- `docs/dashboard.md`
- `docs/deployment.md`
