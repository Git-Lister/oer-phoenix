# Talis and Reading‑List Workflows

This document outlines how OER_Phoenix can support reading‑list workflows, with a focus on Talis.

## Goals

- Help librarians and teaching staff move selected OER into existing reading‑list systems.  
- Reduce duplication of effort when curating and maintaining lists.

## Exporting to CSV

OER_Phoenix can export selected records as CSV in a Talis‑friendly format.

Typical steps:

1. Use search and filters to identify relevant resources.  
2. Select records to export.  
3. Choose a CSV export option for Talis.  
4. Download and import the CSV into Talis according to local practice.

Fields typically included:

- Title  
- Author / creator  
- Publication details  
- URL  
- Licence  
- Resource type

## Talis push jobs

For deeper integration, OER_Phoenix can create push jobs that send metadata directly to Talis.

Typical steps:

1. Configure Talis API credentials in settings.  
2. Select resources or a collection in OER_Phoenix.  
3. Create a Talis push job.  
4. Monitor the job status and review results.

## Collections and lists

Planned functionality includes:

- Creating named collections within OER_Phoenix.  
- Using collections as the basis for exports or push jobs.

This would allow staff to build and maintain OER sets that correspond to modules, programmes, or themes.

## Governance and review

Institutions should decide:

- Who can initiate exports and push jobs.  
- How OER selections are reviewed before being added to official reading lists.  
- How updates and removals are handled over time.

## Related documents

- `README.md`  
- `docs/architecture.md`  
- `docs/deployment.md`