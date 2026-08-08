# Product Specification: AI Mock Interview Platform

**Platform Objective:** A voice-native web platform for mockup interviews utilizing LLM agents, offering real-time Speech-to-Text (STT) and Text-to-Speech (TTS).

## 1. Core Features
* **Dynamic Context:** The platform ingests a job description and optionally a candidate resume to ground the interview role, topics, location, and seniority.
* **Interview Modes:** Supports two distinct types of interviews: an initial recruiter call and a technical hiring manager call.
* **Lifelike Roleplay:** The agent must impersonate the chosen persona (recruiter or technical staff) dynamically based on the company culture extracted from the job description.
* **Session Recording:** The entire interview must be recorded as both downloadable audio and a readable text transcription.
* **Post-Call Analytics:** The system generates a detailed feedback summary highlighting strengths and areas for improvement, accompanied by a final rating out of 100.

## 2. Technology Stack & Abstract Interfaces
* **Frontend:** Browser-based client utilizing WebRTC over WebSockets for jitter-free audio transport.
* **Backend/Auth:** Firebase Authentication for user management and Firestore as the primary NoSQL datastore, strictly wrapped in a `BaseDataStore` abstract interface.
* **TTS Engine:** Kokoro TTS or Piper running in CPU-only Docker containers, wrapped in a `BaseTTS` interface.
* **STT Engine:** Groq (Whisper) via serverless API, wrapped in a `BaseSTT` interface.
* **LLM Routing (via OpenRouter):** DeepSeek V4 handles the live, real-time interview generation. GPT-5.6 Luna Pro handles the asynchronous post-interview grading and feedback based on the final transcript.

## 3. Development Phases
1. **Phase 1 (Abstract Foundation):** Implement Firebase datastore wrappers, the base interface classes for audio providers, and the core routing logic.
2. **Phase 2 (Audio Transport):** Build the WebRTC client and server architecture for chunked audio streaming.
3. **Phase 3 (Agent Brain):** Implement the Dynamic Topic Queue (Resume RAG injector) and the "Filler Word" hack to mask processing time.
4. **Phase 4 (Post-Call Analytics):** Build the transcript compilation and the GPT-5.6 Luna Pro grading pipeline.
