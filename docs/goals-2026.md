A. Goals for 2026 – full text (for docs/goals-2026.md)
OER_Phoenix: Goals for 2026 (draft)
OER_Phoenix is an open‑source discovery and curation platform that helps academic libraries and teaching teams find, evaluate, and integrate Open Educational Resources (OER) into institutional workflows.

It combines standard library technologies with carefully controlled use of AI so that institutions can benefit from newer tools without giving up professional judgement, transparency, or local policy control.

1. Support OER discovery across fragmented sources
Provide a single search and management surface over OER drawn from multiple repositories, catalogues, and APIs (for example OAI‑PMH feeds, REST APIs, MARCXML exports, and CSV/KBART files).

Offer reusable “source presets” so a typical academic library can connect known OER providers with configuration rather than custom code.

2. Improve metadata so OER is easier to judge and reuse
Enrich and normalise records to make OER more findable and understandable, especially where original metadata is sparse or inconsistent.

Use optional AI assistance for tasks such as generating short summaries or suggesting subjects, while always keeping the original source fields visible and unchanged.

3. Make search and AI behaviour inspectable
Show clearly which parts of each record come from the original source and which were added or suggested by enrichment, including AI‑generated fields.

Provide “Why this result?” explanations so staff and students can see whether a result appeared because of keyword matches, conceptual similarity, quality signals, or other ranking factors.

4. Put human and institutional judgement first
Treat AI outputs as hints for professional judgement, not as authoritative decisions; librarians and educators remain responsible for selection, recommendation, and contextualisation.

Encourage critical reading of AI‑generated text (for example quality scores and summaries) by explaining how these are produced and by linking back to the underlying records.

Design features so that local policies on AI, academic integrity, and resource selection can be applied consistently, and so that AI use can be discussed explicitly with staff and students where needed.

5. Offer policy‑aligned, optional AI profiles
Allow institutions to run OER_Phoenix in a minimal mode with no AI services (harvesting plus keyword search), or in a fuller mode that enables semantic search and enrichment where policies permit.

Support different technical and policy contexts by making enrichment and search backends pluggable, so libraries can use commercial APIs, institutional services, or non‑AI rules‑based approaches as appropriate.

Minimise unnecessary data exposure to third‑party AI services by keeping enrichment pipelines configurable, documenting what is sent where, and making it straightforward to keep all processing on institutional infrastructure if required.

6. Fit into real library and teaching workflows
Support end‑to‑end workflows around collection building, reading‑list support (including Talis‑friendly exports and push jobs), and local review or governance processes.

Provide a librarian‑friendly staff dashboard for common operational tasks, keeping Django admin available for deeper configuration and troubleshooting where needed.

7. Strengthen information literacy and AI literacy
Help students and staff see how search systems, metadata, and AI‑assisted tools shape what they find, by labelling AI use clearly and exposing ranking and quality signals.

Enable institutions to align OER_Phoenix with their own information‑literacy and AI‑usage guidance, for example by linking to local policies and configuring which features are visible to which audiences.

Support concrete teaching use‑cases (for example workshops where librarians show how changing metadata or ranking settings alters results, or sessions comparing AI‑generated summaries with original resources) to build critical understanding rather than passive reliance.

8. Remain open, extensible, and auditable infrastructure
Keep harvesting, indexing/search, and user interfaces as distinct but well‑documented layers so that institutions can extend or swap components without forking the whole project.

Use open formats and commonly available open‑source tooling (Docker, Postgres, Redis, Celery) so deployments are inspectable, repeatable, and maintainable by typical institutional teams.