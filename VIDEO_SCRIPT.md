# Demo Video Script — CX Intelligence Agent

**Total time: ~4 minutes**
*(Italics = what's on screen at that moment)*

---

## INTRO (20 sec)

*Show repo or title screen*

"Hi. I built Use Case 18 — Customer Experience Intelligence.

The problem: businesses collect thousands of customer reviews but can't act on them fast enough. Reading reviews manually doesn't scale. And generic sentiment tools just give you a score — they don't tell you what to fix or where in the customer journey things are breaking down.

This system changes that."

---

## WHAT IT DOES (30 sec)

*Show architecture diagram or README*

"Six AI agents work together in a pipeline.

First, a Discovery Agent reads the reviews and figures out what kind of business it's looking at — no hardcoded domains, it infers everything from the text.

Then Sentiment Analysis classifies every review. A Journey Mapper assigns each review to a stage in the customer journey. A Pain Detector uses semantic embeddings and clustering to group complaints into themes.

A Recommender generates five prioritised actions. And finally, an Evaluator — powered by gpt-5.1 — critiques those recommendations and sends them back for revision if they're not specific enough.

The whole thing runs in about 35 seconds."

---

## DEMO — HEALTH CHECK (15 sec)

*Run `./demo.sh` or show terminal*

"Let's see it live. The system runs as a FastAPI service.

Health check confirms the API is up, Compass is configured, and we're ready to go."

---

## DEMO — RESTAURANT (45 sec)

*Watch Step 2 output appear*

"First test — 20 restaurant reviews with mixed sentiment.

The Discovery Agent inferred the business type as restaurant and identified six journey stages: Discovery and Reservation, Arrival, Ordering, Dining, Billing, Post-Visit.

Sentiment: 8 positive, 10 negative, 2 mixed. Zero neutral — the model finds the signal in every review.

Four pain clusters emerged. The top one — Reservation System Failures — high severity, three reviews mentioning lost bookings.

The Evaluator triggered a revision on the first attempt, asking for more specific KPIs. The Recommender responded with a revised set. That's the critique loop working as designed."

---

## DEMO — AIRLINE (30 sec)

*Watch Step 3 output appear*

"Now the same pipeline — no config changes — on 30 airline reviews.

Business type: airline. Completely different journey stages inferred: Booking, Check-in, Boarding, In-flight, Baggage, Support.

Five pain clusters. The system adapted entirely from the text.

This is what vertical-agnostic means in practice. You can point it at any industry and it figures out the domain itself."

---

## DEMO — EDGE CASES (20 sec)

*Watch Steps 4 and 5*

"Two edge cases worth showing.

All-negative reviews — maximum pain clusters, the evaluator is demanding.

All-positive reviews — no negative sentiment to cluster, so the system correctly outputs no pain points and no critical recommendations. It doesn't invent problems that aren't there."

---

## STREAMLIT UI (30 sec)

*Switch to browser at localhost:8501*

"There's also a Streamlit UI for interactive demos.

You can upload any JSON file or paste reviews directly.

The Sentiment tab shows every review individually with the evidence the model used to classify it.

The Journey tab shows a distribution chart across the inferred stages.

Pain Clusters are sorted by severity. Recommendations show the full evaluator critique alongside the final actions."

---

## TECH STACK (20 sec)

*Show README or code briefly*

"Under the hood: LangGraph for orchestration, FastAPI for the API, Core42 Compass for all LLM and embedding calls — gpt-4.1 for agents, gpt-5.1 for evaluation, text-embedding-3-large for clustering.

There's an embedding cache so repeated runs don't hit the API unnecessarily.

29 automated tests, a working Dockerfile, and nine example inputs across seven verticals."

---

## CLOSE (10 sec)

"That's Use Case 18 — a complete, working, production-ready CX intelligence system built for the G42 Agentathon. Thank you."

---

## TIPS FOR RECORDING

- Speak at a natural pace — don't rush the technical parts
- Let the terminal output finish before moving on
- For the UI section, click through each tab slowly
- Total target: 3.5 to 4 minutes
