# Product Requirements Document (PRD)

**Product Name:** Sylli
**Target Audience:** University students across all disciplines looking to organize, synthesize, and review complex course materials.

---

## 1. Product Overview

Sylli AI is a student-centric, Retrieval-Augmented Generation (RAG) study application. Unlike generic "chat-with-PDF" tools, this application uses a "Syllabus-First" ingestion engine to automatically categorize uploaded lecture slides, reading assignments, and notes into a chronological timeline (Units/Weeks). It provides a three-pillar interface: a chronological library navigator, a highly contextual AI tutor capable of understanding dense texts and varied media, and an adaptive quiz generator.

---

## 2. Core Functionalities (The "Three Pillars")

### A. Smart Ingestion & Auto-Sorting (Backend)
* **Syllabus Anchoring:** The user uploads a course syllabus. The AI extracts the reading schedule and lecture topics, creating a background JSON map of themes mapped to specific weeks.
* **Automated Tagging:** When new documents (journal articles, slide decks, book chapters) are uploaded, the system parses the text, compares it to the syllabus map, and automatically assigns a "Week" and "Topic" metadata tag (e.g., tagging a PDF as "Week 3: The French Revolution" or "Unit 2: Cognitive Psychology").

### B. Pillar 1: The Navigator (Library View)
* **Chronological UI:** A sidebar displaying the semester broken down by Week/Unit.
* **AI Summaries:** A 2-3 sentence AI-generated TL;DR for every uploaded document to make skimming massive reading loads seamless.

### C. Pillar 2: The Tutor (Contextual Chat)
* **Grounded QA:** A chat interface where users can ask complex questions. The AI strictly searches the embedded vector database of the uploaded course materials to prevent hallucinating outside information.
* **Multimodal Understanding:** The bot must be able to "read" standard text as well as visual aids like historical maps, sociology charts, or scanned images of older text and accurately explain them in context.
* **Source Citations:** Every AI response must include a clickable citation that scrolls the Navigator to the exact page or slide referenced.

### D. Pillar 3: The Examiner (Quiz Generation)
* **Scoped Quizzes:** Users can select specific units (e.g., "Prep for Midterm: Weeks 1-6") to generate practice assessments.
* **Dynamic Formatting:** The AI generates varied question types tailored to the subject, including multiple-choice, term matching, short-answer prompts, and essay thesis outlines.

---

## 3. User Interface & Experience (UI/UX)

* **Layout:** A persistent, three-pane dashboard.
  * **Left Pane (20%):** The Unit/Week Navigator and file uploader.
  * **Center Pane (50%):** The Document Viewer (rendering the actual PDF/Slide with highlighted citations).
  * **Right Pane (30%):** A toggleable sidebar switching between the "Tutor Chat" and the "Examiner Quiz" modes.
* **Design System:** Clean, dark-mode compatible interface (suitable for late-night study sessions) built with a modern framework.

---

## 4. Technical Architecture (Python + AWS)

To build a scalable and cost-effective application, the architecture relies heavily on standard cloud practitioner patterns, utilizing a fully serverless AWS stack tied together with Python (`boto3`, `FastAPI`).

| Component | Technology / AWS Service | Purpose |
| :--- | :--- | :--- |
| **Frontend UI** | React or Next.js (JavaScript/TS) | Creates the interactive three-pane dashboard. Hosted on **AWS Amplify**. |
| **Backend API** | Python (FastAPI) via **AWS Lambda** | Handles routing, auth, and business logic without managing servers. Exposed via **Amazon API Gateway**. |
| **Raw Storage** | **Amazon S3** | The landing zone for all uploaded course materials. Organized into `syllabus/` (for syllabus files) and `documents/` (for slides, readings, etc.) subfolders. |
| **Database** | **Amazon DynamoDB** | Stores the metadata mapping (User IDs -> Courses -> Document Tags -> Chat History). |
| **Embedding & Search** | **Amazon Bedrock Knowledge Bases** | Automatically chunks S3 documents, converts them to vectors (Titan Embeddings), and stores them in **Amazon OpenSearch Serverless**. |
| **AI / Brain** | **Amazon Bedrock (Claude 3.5 Sonnet)** | Handles the heavy lifting: syllabus mapping, multimodal image processing (handling poorly scanned readings or visual charts), and answering chat queries. |
| **Event Triggers** | **Amazon EventBridge** | Triggers the Python Lambda processing functions the moment a file hits the S3 bucket. |

---

## 5. Potential Risks & Considerations

* **Context Window Limits with Massive Readings:** Humanities and social science courses often require hundreds of pages of reading per week. Passing full books to an LLM for quiz generation could result in dropped context.
  * *Mitigation:* Rely strictly on OpenSearch vector retrieval to pull only the top 10-15 most relevant text chunks before generating quiz questions or answering prompts.
* **OCR Inaccuracy on Scanned Documents:** College courses frequently use older, poorly scanned PDFs of book chapters or journal articles which standard text extraction tools struggle to read.
  * *Mitigation:* Utilize Claude 3.5 Sonnet's vision capabilities through Bedrock to process messy pages as images, bypassing the limitations of standard OCR.
