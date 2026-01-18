# Safe Journalist API — Product Brief

## Project Overview
Simple API for investigative journalists to upload audio and text check-ins. The system stores uploads, transcribes audio, and produces a short 3–5 bullet summary with actionable insights for an emergency contact list. Designed for high-stress reporting scenarios.

## Target Audience
Investigative journalists operating in hostile or high-risk environments (e.g., covering dictators, cartels), and their emergency contacts.

## Primary Benefits / Features
- Audio + text ingestion via API with durable storage.
- Automatic audio transcription.
- AI-generated 3–5 bullet summaries focused on actionable, contact-ready insights.
- Fast, lightweight API intended for low-friction check-ins under stress.

## High-Level Tech / Architecture
- FastAPI for the HTTP API layer.
- Python + uv for runtime and dependency management.
- pytest for automated testing.
