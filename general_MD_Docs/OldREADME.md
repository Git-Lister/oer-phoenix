I'll help enhance the README.md by incorporating details from the provided markdown files and the Meta-RAG agent configuration. The goal is to create a more comprehensive and technically robust documentation that better reflects the cutting-edge nature of the project.

Here's the enhanced version:

---

# Open Educational Resourcer

**AI-Powered Semantic Search Platform for OER**

A Django-based platform supporting advanced AI search, multi-source OER harvesting, vector search via pgvector/Qdrant, and Talis reading list export. Containerized for quick deployment with Docker, with async pipelines via Celery + Redis.

---

## 🚀 Core Architecture

- **Backend:** Django 5.x
- **Database:** PostgreSQL 14+ (with pgvector)
- **AI/ML:** HuggingFace/SentenceTransformers (`all-MiniLM-L6-v2`)
- **Vector Search:** pgvector (default), Qdrant optional
- **Task Queue:** Celery + Redis (async processing)
- **Containerization:** Docker Compose
- **Frontend:** Django templates + Bootstrap

---

## ✨ Features

- 🔍 **AI-Powered Semantic Search**: Find resources with natural language queries
- 📚 **OER Harvesting**: Automated ingestion from OER Commons, OpenStax, MARCXML, or CSV
- 🎯 **Vector Similarity Search**: Semantic relevance via pgvector/Qdrant
- 📤 **Talis Reading List Export**: Send collections to Talis Aspire
- 📊 **Admin Dashboard**: Manage sources, mappings, and ingest jobs
- 🔄 **Async Task Processing**: Embeddings/indexing offloaded to Celery
- 🗃 **Batch Upload**: Import resources in bulk from CSV
- 📝 **Extensible API**: Designed for easy integration

---

## 🟢 Quick Start

### Prerequisites

This file is deprecated: the up-to-date documentation lives in [README.md](README.md).

Retain this file only if you need historical notes. For onboarding and
deployment steps, follow the instructions in [README.md](README.md).


