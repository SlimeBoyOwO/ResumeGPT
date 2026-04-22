# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
ResumeGPT is an AI-powered resume review system. It uses NLP models (BERT for NER) and LLMs (WebLLM/DeepSeek) for resume parsing, information extraction, semantic matching with Job Descriptions (RAG), and expert scoring via an Agent-based Mixture of Experts (MoE) / Tree of Thoughts (ToT) architecture.

## Repository Structure
This is a monorepo consisting of:
- `frontend/`: Vue 3, TypeScript, Tailwind CSS, Pinia, Vite frontend.
- `backend/`: Python, FastAPI backend.
- `docs/`: Design and architecture documentation.
- `nlp_train/`: Code for training NLP models (e.g., BERT-based NER).
- `scripts/`: Scripts for database initialization, data generation, etc.

## Setup and Commands

### Backend (Python/FastAPI)
The backend uses `uv` for package management.
- **Run Dev Server**:
  ```bash
  cd backend
  uvicorn main:app --reload
  ```
- **Database Initialization**: Ensure MySQL is running on `localhost:3306` with user `root`/`password`. Run the init script:
  ```bash
  mysql -u root -p < scripts/init_db.sql
  ```

### Frontend (Vue 3/Vite)
The frontend uses `pnpm` for package management.
- **Install Dependencies**:
  ```bash
  cd frontend
  pnpm install
  ```
- **Run Dev Server**:
  ```bash
  cd frontend
  pnpm dev
  ```
- **Build for Production**:
  ```bash
  cd frontend
  pnpm build
  ```
- **Lint Code**:
  ```bash
  cd frontend
  pnpm lint
  ```
- **Type Check**:
  ```bash
  cd frontend
  pnpm type-check
  ```

## Architecture and Key Components

### Database
- Uses MySQL for relational data and ChromaDB for vector storage (RAG).
- **Core Entities**: Users (HR/candidates), Resumes (with parsed info and vector IDs), Job Descriptions, Experts (Agent configs), and Match Records.
- See `docs/database_design.md` for the full ER diagram and table definitions.

### Backend Architecture
- **API Routes**: Located in `backend/app/api/` (auth, users, resumes, experts, job_descriptions).
- **Services (`backend/app/services/`)**:
  - `ner_engine.py`: Handles structured resume analysis using the trained NLP model.
  - `llm_resume_extractor.py`: Fallback extraction and PII anonymization using LLMs.
  - `rag_service.py`: Interfaces with ChromaDB for vector similarity matching between resumes and JDs.
  - `moe_router.py` & `workflow_engine.py`: Implements the MoE and ToT evaluation flows, selecting experts and aggregating their feedback.

### Frontend Architecture
- **Routing**: `frontend/src/router/index.ts` defines layout-based routing (Auth, Main Dashboard, Admin Panel).
- **State Management**: Uses Pinia (stores in `frontend/src/stores/`).
- **API Client**: Axios instance in `frontend/src/utils/api.ts` with JWT interception.

## Credentials
Default Admin Account (from `init_db.sql`):
- **Username/Email**: admin / admin@resumegpt.com
- **Password**: admin123