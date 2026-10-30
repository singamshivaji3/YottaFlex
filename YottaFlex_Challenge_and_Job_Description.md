# YottaFlex Associate AI Forward Deployed Engineer
## Job Description and Candidate Project Challenge Reference

> **Source note:** The job-description section summarizes details supplied by the candidate and the public recruitment listing. The project-challenge section is a structured reconstruction of requirements discussed with the candidate; it is **not a verbatim transcript** of the original challenge email. Compare it with the original company-provided challenge statement, FAQ, and submission guidelines before implementation. Where the official materials differ, follow the official materials.

---

# Part A — Job Description

## Role
**Associate AI Forward Deployed Engineer (Associate AI FDE)**

- **Location:** Hyderabad, India
- **Experience:** 0–3 years; freshers may apply
- **Openings:** The candidate-shared listing stated 30 openings
- **Internship:** 6-month paid internship
- **Starting CTC:** ₹7,00,000 per year after conversion, as shown in the candidate-shared listing
- **Service agreement:** The candidate-shared job description mentioned a service agreement; confirm the exact duration and terms in the official offer/role page.

## Role purpose
Build AI-powered applications and deploy real-world solutions. The role emphasizes people who can build, ship, and own end-to-end work.

## Evaluation attributes
1. Communication
2. Technical depth
3. Critical thinking
4. Applied AI
5. Ownership

The recruitment information says candidates need to clear the required bar for each attribute rather than relying on an average score.

## Must-have skills
- Strong Python and comfort with at least one additional programming language
- Full-stack experience covering front end and back end
- SQL and hands-on database experience
- REST API development and integration
- A real, demoable AI application, such as an application using RAG, agents, or an LLM integration
- A GitHub profile containing end-to-end projects the candidate has built and shipped

## Preferred skills
These are listed as advantages rather than mandatory requirements:
- TypeScript
- Cloud platforms such as AWS or GCP
- Docker / Kubernetes
- Vector databases such as Pinecone, Weaviate, or pgvector
- Agent/orchestration frameworks such as LangChain, LangGraph, CrewAI, or LlamaIndex
- LLM evaluation and observability
- MLOps basics such as deployment, versioning, and monitoring
- Experience interacting directly with customers or users

## Selection process
The company materials discussed with the candidate describe stages such as:
1. Application submission
2. Aptitude and/or AI screening
3. 72-hour project-building challenge
4. In-office hackathon
5. Technical evaluation
6. Leadership/executive round

Use the exact sequence and labels in the candidate's current official recruitment communications if they differ.

## Public recruitment references
- Role listing: https://recruitment.yottaflex.ai/jobs/associate-ai-forward-deployed-engineers-1
- Recruitment help: https://recruitment.yottaflex.ai/careers/help

**Compensation note:** Public recruitment pages and the candidate-shared job description have displayed different stipend/service-agreement details at different points. Verify current terms directly in the official role page or recruitment communication.

---

# Part B — Candidate Project Challenge

## Working title
**Synthetic Learning Data and Explainable Learning Recommendation Workflow**

## Objective
Build a reproducible end-to-end workflow that generates synthetic learning-platform data, calculates learner skill mastery, recommends suitable next learning activities, validates data integrity and business rules, and demonstrates system behavior on intentionally constructed anomaly/edge cases.

The goal is not merely to create tables or a dashboard. The implementation should demonstrate data modeling, deterministic generation, time-aware calculations, prerequisite-aware recommendations, validation, testing, evaluation, clear documentation, and ownership of technical decisions.

> Verify the exact wording, requirements, and deliverables against the original challenge statement sent by YottaFlex. The list below reflects challenge details available in the conversation and should not be treated as a replacement for the original.

## Required entities / concepts
The challenge discussion identified:
- `Learner`
- `Course`
- `Skill`
- `SkillPrerequisite`
- `ContentItem`
- `ContentSkill`
- `Attempt`
- `AssessmentResult`
- `LearningPath`
- `Recommendation`

Use primary keys, foreign keys, appropriate constraints, and documented relationships. Use bridge tables where the relationship is many-to-many. Document cardinalities, lifecycle/effective dates, event history, and derived values where applicable.

## Example identifier formats
Use the exact formats from the original challenge document if they differ. Formats discussed include:
- Learners: `LRN-000001`
- Courses: `CRS-000001`
- Skills: `SKL-000001`
- Content items: `CNT-000001`
- Attempts: `ATT-<learner-id>-000001`
- Learning paths: `PATH-2026-000001`

## Target synthetic-data volumes
The challenge details discussed included:
- 10,000 learners
- 500 skills
- 2,000 content items
- 500,000 attempts

Implement a single parameterized generator that supports a small development dataset and the full target dataset. Use a fixed seed (the example discussed was `20261022`) so runs can be reproduced. Start small to validate correctness, then scale up and record actual results and performance. Do not silently substitute smaller volumes for the official target.

## Core functional requirements
1. Generate valid baseline synthetic data for the required entities and relationships.
2. Use stable IDs and enforce primary-key/foreign-key integrity.
3. Store or export data in the formats required by the official challenge, discussed as CSV, JSON, and SQL.
4. Calculate learner mastery using only attempts available at the requested “as-of” time. Do not allow future attempts to influence past mastery or recommendations.
5. Identify learning needs from skill mastery and assessment results.
6. Enforce skill prerequisites as a hard eligibility gate before ranking candidate activities.
7. Rank eligible learning activities using explainable factors such as skill gap, difficulty fit, and content relevance.
8. Store recommendation scores, reason codes/rationale, and an algorithm/rule version.
9. Validate identifiers, references, timestamps, prerequisite relationships, and other applicable business rules.
10. Provide a data dictionary and explain the schema, keys, relationships, cardinalities, lifecycle/effective dates, event history, and derived fields.
11. Demonstrate deterministic regeneration with counts and checksums or an equivalent repeatability check.
12. Keep clean baseline data separate from intentionally invalid anomaly fixtures.
13. Maintain a separate ground-truth/label record for injected anomaly cases where appropriate.
14. Include automated tests and an honest evaluation report.
15. Provide a README with installation, configuration, generation, validation, testing, demo, and submission instructions.
16. Include truthful AI prompt history and AI-usage disclosure in line with the company's submission guidance.

## Explicit anomaly / edge cases discussed
Create isolated, labeled test fixtures for the following cases. Confirm the precise expected behavior and naming from the original challenge statement:
1. A recommendation that violates a skill prerequisite.
2. An attempt whose timestamps are in an invalid order.
3. Content mapped to a nonexistent skill.
4. Mastery calculation that incorrectly uses a future attempt.
5. A learning path that loops without making progress.

For each case, document:
- What makes the case invalid or problematic
- Whether the fixture is expected to be rejected, flagged, or handled safely
- The validation or test that detects it
- The expected result
- Ground-truth label and issue type, if applicable

Do not corrupt the clean baseline dataset just to include an anomaly. Keep anomaly fixtures clearly separated and reproducible.

## Evaluation and evidence
Measure and report only metrics that are meaningfully defined and actually calculated. Potential checks include:
- Primary-key uniqueness and foreign-key integrity
- Invalid timestamp detection
- Prerequisite violation rate
- Temporal-leakage detection
- Recommendation coverage
- Ranking metrics such as Precision@K or Recall@K only if suitable independent labels/ground truth exist
- Anomaly precision/recall/F1 if the labels and definitions support them
- Reproducibility of counts and checksums
- Runtime and memory/performance observations at the target scale

Do not fabricate metrics or claim a test passed without running it. Explain assumptions and limitations.

## Suggested technology stack (proposal, not an official company mandate)
- Python for generation, mastery, recommendation, validation, and evaluation
- SQLite for a local relational database
- SQL constraints and queries for data integrity
- pytest for automated tests
- Streamlit for a local interactive demo after the core pipeline works
- Git and GitHub for version control and submission
- Pandas only where it adds practical value

Keep the core workflow local-first and runnable without paid APIs, API keys, cloud hosting, or paid services.

## Suggested repository layout
```text
yottaflex-project/
├── README.md
├── PROJECT_BRIEF.md
├── ANTIGRAVITY_PROMPT.md
├── requirements.txt
├── .gitignore
├── schema.sql
├── app.py
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── generator.py
│   ├── data_access.py
│   ├── mastery.py
│   ├── recommender.py
│   ├── validator.py
│   └── evaluation.py
├── scripts/
│   ├── generate_data.py
│   ├── validate_data.py
│   └── reproducibility_check.py
├── tests/
│   ├── test_generator.py
│   ├── test_mastery.py
│   ├── test_recommendations.py
│   └── test_anomalies.py
├── docs/
│   ├── data_dictionary.md
│   ├── architecture.md
│   ├── REQUIREMENTS_CHECKLIST.md
│   ├── DECISIONS_AND_ASSUMPTIONS.md
│   ├── AI_PROMPT_HISTORY.md
│   └── AI_USAGE_DISCLOSURE.md
├── data/
│   ├── sample/
│   └── ground_truth/
└── exports/
```

## Suggested implementation order
1. Read the original company documents and write a source-backed requirements checklist.
2. Document schema decisions and assumptions.
3. Implement the schema and deterministic small-scale generator.
4. Implement validation and isolated anomaly fixtures.
5. Implement time-aware mastery calculation.
6. Implement prerequisite-aware, explainable recommendation ranking.
7. Add tests for clean behavior, edge cases, and temporal leakage.
8. Add exports and reproducibility verification.
9. Run a medium dataset, then attempt the full target dataset.
10. Add evaluation report and optional Streamlit demo.
11. Complete README, AI prompt history, and AI usage disclosure.
12. Run all verification commands and record actual outputs.

## Submission / transparency reminders discussed
The company-provided FAQ and guidelines are authoritative. Details discussed include:
- The challenge window is 72 hours from the company's recorded send time; verify the actual deadline and time zone in the original message.
- Submit a dedicated public GitHub repository using the same email address used during recruitment, according to the instructions.
- Include executable code and clear install/configure/run/verify instructions.
- Maintain meaningful commits and explain the evolution of the work.
- Include the actual prompts sent to AI tools and an honest account of AI assistance, personal review, modifications, and validation.
- Do not claim independent authorship of AI-generated code.
- Do not commit secrets, credentials, personal information, or unauthorized proprietary code.
- If something is incomplete, state what works, what does not, known limitations, and next steps.
- Do not publish or push the repository until the candidate has reviewed it and explicitly approved.

## Instructions to Antigravity
1. Read this reference and all original company-provided documents.
2. Extract exact requirements from the original challenge and create `docs/REQUIREMENTS_CHECKLIST.md`.
3. Where this reference differs from the original, follow the original and record the difference in `docs/DECISIONS_AND_ASSUMPTIONS.md`.
4. Do not assume the challenge details above are a verbatim official specification.
5. Implement and test incrementally. Report actual evidence and unresolved issues.
