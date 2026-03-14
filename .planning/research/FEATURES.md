# Feature Research

**Domain:** RAG-based AI study application (syllabus-first course material navigation + AI tutor + quiz generator)
**Researched:** 2026-03-14
**Confidence:** MEDIUM — core patterns verified across multiple sources; specific UX thresholds from industry surveys and competitor analysis

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete or broken.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Auth / private course data | Students upload personal notes and course materials — they expect their data to be private and tied to an account | LOW | Email/password sufficient at MVP; JWT sessions. No OAuth needed. FERPA compliance is not required for a personal tool but data isolation per user is non-negotiable |
| File upload (PDF, slides) | Every competitor (NotebookLM, Quizlet, Laxu AI) accepts PDF upload as the baseline interaction | LOW-MEDIUM | Already partially exists (S3 + DynamoDB). Need UI flow and validation |
| Course structure visibility | Students need to see what's been uploaded and how it maps to their syllabus — missing this = confusion about what AI "knows" | MEDIUM | The week_map is already parsed; the library navigator surfaces it |
| AI chat grounded in course materials | The core promise — users expect answers to come from their uploaded content, not the LLM's generic training | HIGH | RAG pipeline: embed materials, retrieve relevant chunks, answer with context. This is the core build |
| Inline source citations | Users expect to verify AI answers. NotebookLM's most-praised feature is clickable citations back to source passages. Without this, trust breaks down | MEDIUM | Must show which document/week the answer came from. Full page-level citation is sufficient at MVP; inline highlight is a differentiator |
| Quiz generation scoped to a unit | Users expect to generate practice questions for a specific week/unit, not only the full course | MEDIUM | Scope parameter (unit vs full course) must be exposed in UI. Question types: multiple choice + short answer at minimum |
| Instant feedback on quiz answers | Every AI quiz tool users have tested provides immediate right/wrong feedback with explanation. Delayed or absent feedback is a top complaint | LOW-MEDIUM | LLM can explain correct answer after submission. Stateless at MVP (no score tracking) |
| Loading / progress indicators | Uploads and AI queries take time. Users abandon flows that feel frozen | LOW | Streaming responses for AI chat reduces perceived latency significantly |
| Error states that explain what went wrong | If a file fails to parse or a query returns nothing, users need actionable feedback, not a generic error | LOW | "No content found for Week 3" is better than a 500 |

---

### Differentiators (Competitive Advantage)

Features that set the product apart from generic chat-with-PDF tools.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Syllabus-first organization | Generic tools dump all PDFs into a flat list. Sylli organizes by unit/week automatically, giving students a mental model that mirrors their actual course | MEDIUM | Already exists on backend (week_map). The UI navigator is the differentiating surface |
| Week-aware AI tutor context | The AI knows "we are in Week 4" and can prioritize recent materials over older ones, answer questions like "what did we cover in the first unit?" | MEDIUM-HIGH | Requires injecting week_map context into RAG retrieval — not just semantic similarity but structured scoping |
| Auto-categorization of uploads | When a student uploads a new file, the AI suggests which unit/week it belongs to based on content — student confirms or corrects | MEDIUM | Bedrock already handles Syllabus parsing; same pattern extended to classify individual files. Reduces manual tagging friction |
| Cross-material synthesis | AI tutor can answer questions that span multiple weeks' materials ("How does the Week 2 concept relate to Week 5's topic?") — generic PDF chatbots lose cross-document context | HIGH | Requires good chunk retrieval across all embedded materials in the course |
| Quiz scoped to any time window | Generate a quiz for "Weeks 3-5" or "everything before the midterm" — not just per-document | MEDIUM | Requires structured metadata on embeddings (week tag) so retrieval can filter by range |
| Explanation drill-down on quiz | NotebookLM's most-praised quiz feature: click "explain" on any answer to get a deeper explanation with the source passage | LOW-MEDIUM | After a quiz answer, offer "why?" to get a source-cited explanation. High value-to-effort ratio |

---

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but should be deliberately excluded at MVP.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Spaced repetition / adaptive quiz scheduling | Quizlet and Anki have conditioned students to expect this | Requires persistent performance tracking, complex scheduling algorithm, and significant data model changes. Adds weeks of scope without validating the core premise first | Generate quizzes on demand. Students can re-run anytime. Add adaptive scheduling in v2 after usage patterns are understood |
| Flashcard mode | Quizlet mental model — students think "study tool = flashcards" | Flashcards are a different interaction paradigm from quiz generation and require card management UI (create, edit, delete, deck organization). High surface area for MVP | The quiz generator covers the same recall mechanism. Defer flashcards unless user research shows strong demand |
| Multi-course support | Students have multiple courses | Requires course-switching UI, per-course data isolation, course management (archive, delete), and significantly complicates all data access patterns | One course per user at MVP. Constraint forces focus on doing one course extremely well |
| Progress / grade tracking | Students want to know how they're doing | Score history requires persistent storage per quiz attempt, aggregate analytics, and trend visualization. None of this validates the core AI tutor value | Quiz answers are stateless at MVP. Add tracking once quiz quality is validated |
| Collaborative / shared courses | Group study, sharing notes with classmates | Auth model becomes multi-tenant, sharing permissions add complexity, and collaborative editing creates conflict scenarios | Private courses only at MVP |
| Real-time streaming for all operations | Feels fast and modern | Quiz generation mid-stream requires buffering and state management. Only AI chat benefits materially from streaming | Stream AI chat responses. Quiz generation can be a single blocking request since it's infrequent |
| Mobile app | Students study on phones | Web-responsive design covers 80% of mobile use. A native app is a separate engineering workstream | Build web-responsive first. Native app is a v2+ decision |
| Voice / audio interface | NotebookLM's audio overview is a marquee feature | Audio generation (TTS) is a separate technical track. Student expectations for audio quality are high. One bad audio experience damages trust | Text-only at MVP. Audio is a clear differentiator for v2 if NotebookLM-style audio proves popular |

---

## Feature Dependencies

```
[Auth / account system]
    └──required by──> [Private course data]
    └──required by──> [File upload tied to user]
    └──required by──> [AI tutor session context]

[File upload]
    └──required by──> [Auto-categorization]
    └──required by──> [Library navigator]
                          └──required by──> [Week-scoped quiz]
                          └──required by──> [Week-aware AI tutor]

[RAG pipeline (embed + retrieve)]
    └──required by──> [AI tutor with citations]
    └──required by──> [Quiz generator]
    └──required by──> [Cross-material synthesis]

[Syllabus week_map (ALREADY EXISTS)]
    └──enables──> [Auto-categorization]
    └──enables──> [Library navigator]
    └──enables──> [Week-scoped retrieval]
    └──enables──> [Week-aware AI tutor]

[Quiz generator]
    └──enhanced by──> [Explanation drill-down]
    └──enhanced by──> [Week/range scoping]

[Inline citations]
    ──enhances──> [AI tutor trust]
    ──enhances──> [Quiz explanation drill-down]
```

### Dependency Notes

- **Auth is a prerequisite for everything**: Without user accounts, all course data is global. Must be Phase 1.
- **File upload requires Auth**: Files must be associated with a user and course. Cannot build the library without this.
- **RAG pipeline is the critical path**: AI tutor and quiz generator both depend on embeddings being generated for uploaded materials. The pipeline (upload → extract text → embed → store) must be built before any AI features.
- **week_map is the existing accelerator**: Because syllabus parsing already produces a structured week_map, auto-categorization and library navigation are cheaper to build than they would be from scratch. This is Sylli's head start.
- **Quiz quality depends on RAG quality**: A weak embedding/retrieval pipeline will produce off-topic or hallucinated quiz questions. The RAG pipeline must be solid before quiz generation is surfaced to users.

---

## MVP Definition

### Launch With (v1)

Minimum viable — validates "AI tutor that understands your course structure."

- [ ] Email/password auth with JWT sessions — gates all data behind user accounts
- [ ] Material upload (PDF, PPTX) with S3 storage — extends existing syllabus upload to lecture materials
- [ ] Auto-categorization of uploaded materials → week suggestion → student confirms — reduces friction, leverages existing Bedrock integration
- [ ] Library navigator — chronological, organized by week_map — the surface that differentiates from flat PDF chatbots
- [ ] RAG pipeline — embed uploaded materials, store vectors, semantic retrieval — the technical foundation everything else depends on
- [ ] AI tutor chat — week-aware context injection, inline citations to source document — core value proposition
- [ ] Quiz generator — multiple choice + short answer, scoped to a unit or full course, immediate answer feedback — second major value prop

### Add After Validation (v1.x)

Add when core is confirmed working and users express demand.

- [ ] Explanation drill-down on quiz answers — add when quiz is being actively used and users ask "why was that the answer?"
- [ ] Quiz scoped to week ranges (e.g., "Weeks 3-5") — add when students studying for midterms/finals express frustration at unit-only scoping
- [ ] Streaming AI responses — add if perceived latency is a complaint; chat response time is the trigger
- [ ] Password reset flow — add before any public launch; students will forget passwords

### Future Consideration (v2+)

Defer until product-market fit is established.

- [ ] Multi-course support — massive data model complexity; only worth it after single-course usage is proven valuable
- [ ] Spaced repetition / adaptive quiz scheduling — requires performance tracking infrastructure; defer until quiz usage is validated
- [ ] Flashcard mode — defer unless user research shows the quiz format is insufficient
- [ ] Audio / voice interface — high production effort; reassess if NotebookLM audio proves the market
- [ ] Collaborative courses / shared materials — requires multi-tenant auth; only relevant after individual use is validated
- [ ] Mobile native app — web-responsive first; native only if mobile usage data justifies it

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Auth (email/password) | HIGH | LOW | P1 |
| Material upload | HIGH | LOW | P1 |
| Library navigator (week view) | HIGH | LOW-MEDIUM | P1 |
| RAG pipeline | HIGH | HIGH | P1 |
| AI tutor with citations | HIGH | MEDIUM | P1 |
| Auto-categorization | MEDIUM-HIGH | MEDIUM | P1 |
| Quiz generator (unit scope) | HIGH | MEDIUM | P1 |
| Quiz instant feedback + explanation | MEDIUM | LOW | P1 |
| Streaming AI chat responses | MEDIUM | LOW-MEDIUM | P2 |
| Quiz week-range scoping | MEDIUM | LOW | P2 |
| Password reset | LOW (launch gate) | LOW | P2 |
| Explanation drill-down on quiz | MEDIUM | LOW | P2 |
| Spaced repetition | MEDIUM | HIGH | P3 |
| Multi-course support | HIGH (future) | HIGH | P3 |
| Flashcard mode | MEDIUM | MEDIUM | P3 |
| Audio overview | LOW-MEDIUM | HIGH | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

---

## Competitor Feature Analysis

| Feature | NotebookLM (Google) | Quizlet AI | Generic Chat-PDF Tools | Sylli Approach |
|---------|---------------------|------------|------------------------|----------------|
| Source grounding | Yes — answers cite specific source docs | Partial — flashcard sources are manual | Varies — often no citation | Yes — inline citation to document + week required |
| Course/syllabus structure | No — flat notebook model | No — flat deck model | No | Yes — syllabus-first week_map is the differentiator |
| Quiz generation | Yes — from all sources | Yes — flashcard to test conversion | Limited | Yes — scoped to week or full course |
| Adaptive learning | No (audio overview, not adaptive) | Yes (Learn mode) | No | No at MVP; defer |
| Auth / private | Yes (Google account) | Yes | Varies | Yes — email/password |
| Multi-source cross-synthesis | Yes — across uploaded docs | No | No | Yes — across all materials in the course |
| Organization / navigation | Flat list in notebook | Flat deck lists | Flat | Chronological week-based navigator |
| Audio / voice | Yes (Audio Overview) | No | No | Not at MVP |

---

## Sources

- [6 NotebookLM features to help students learn (Google Blog)](https://blog.google/innovation-and-ai/models-and-research/google-labs/notebooklm-student-features/)
- [NotebookLM: Exploring a source-grounded AI tool](https://insidescienceresources.wordpress.com/2025/12/16/notebooklm-exploring-a-source-grounded-ai-tool/)
- [Best AI Study Tools in 2026 — Laxu AI](https://laxuai.com/blog/best-ai-study-tools-2026)
- [Top 10 AI Quiz Generators 2026](https://www.bestdevops.com/top-10-ai-quiz-generators-tools-in-2025-features-pros-cons-comparison/)
- [Best Flashcard Apps 2025: Anki vs RemNote vs Quizlet](https://notigo.ai/blog/best-flashcard-apps-students-anki-remnote-quizlet-2025)
- [RAG in Education — ScienceDirect systematic survey](https://www.sciencedirect.com/science/article/pii/S2666920X25000578)
- [RAG Chatbots for Education: A Survey (ResearchGate)](https://www.researchgate.net/publication/390700272_Retrieval-Augmented_Generation_RAG_Chatbots_for_Education_A_Survey_of_Applications)
- [AI and student data privacy — Curriculum Associates](https://www.curriculumassociates.com/blog/ai-and-student-data-privacy)
- [ChatGPT hallucination in academic citations — Study Finds](https://studyfinds.org/chatgpts-hallucination-problem-fabricated-references/)
- [Confusing Course Navigation Undermines Content — LMS Portals](https://www.lmsportals.com/post/confusing-course-navigation-is-undermining-your-content)

---

*Feature research for: RAG-based AI study application (Sylli)*
*Researched: 2026-03-14*
