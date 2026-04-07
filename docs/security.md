# Security, Privacy, and Data Protection

This document provides guidance on running OER_Phoenix in a way that respects institutional security and privacy requirements.

## Scope

OER_Phoenix primarily processes:

- Metadata about open educational resources  
- URLs pointing to external resources

However, AI‑assisted features and logging can still raise important questions.

## Key principles

- Minimise collection of personal data.  
- Keep AI features optional and configurable.  
- Make data flows to external services explicit.  
- Use standard institutional security controls where possible.

## Checklist

### Application security

- [ ] Run OER_Phoenix behind HTTPS.  
- [ ] Use strong, unique admin passwords.  
- [ ] Restrict Django admin to authorised staff.  
- [ ] Keep dependencies and container images up to date.

### Data protection

- [ ] Avoid storing sensitive personal data in resource metadata.  
- [ ] Review and document any personal data that may appear in logs.  
- [ ] Configure log retention in line with institutional policies.

### AI‑related considerations

- [ ] Decide which AI features are enabled (if any).  
- [ ] Document which services receive what data for enrichment or embeddings.  
- [ ] Review contracts and data‑processing terms for external AI providers.  
- [ ] Prefer self‑hosted or institutionally managed AI services where appropriate.

### Access control

- [ ] Define roles and permissions for staff dashboard access.  
- [ ] Restrict staff‑only tools (e.g. RAG test interface) to appropriate users.  
- [ ] Integrate with institutional authentication if possible.

### Infrastructure

- [ ] Ensure regular backups of the PostgreSQL database.  
- [ ] Test restore procedures.  
- [ ] Monitor system health and error logs.

## Incident response

Institutions should have a plan for:

- Responding to suspected data breaches.  
- Revoking credentials and API keys.  
- Notifying affected stakeholders.

OER_Phoenix does not impose a specific process, but should fit into existing institutional procedures.

## Related documents

- `docs/deployment.md`  
- `docs/enrichment.md`  
- `README.md`