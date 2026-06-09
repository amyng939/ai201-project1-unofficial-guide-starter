# The Unofficial Guide — Project 1

> **How to use this template:**
> Complete each section *after* you've built and tested the corresponding part of your system.
> Do not write placeholder text — if a section isn't done yet, leave it blank and come back.
> Every section below is required for submission. One-liners will not receive full credit.

---

## Domain

<!-- What topic or category of knowledge does your system cover?
     Why is this knowledge valuable, and why is it hard to find through official channels?
     Example: "Student reviews of CS professors at [university] — useful because official
     course descriptions don't reflect teaching style, exam difficulty, or workload." -->

Student reviews of colleges. It is valuable because there are so many different colleges to choose from and so much information out there to compare along with biased information from official channels and it can be overwhelming.

---

## Document Sources

<!-- List every source you collected documents from.
     Be specific: include URLs, subreddit names, forum thread titles, or file names.
     Aim for variety — sources that together cover different subtopics or perspectives. -->

| # | Source | Type | URL or file path |
|---|--------|------|-----------------|
| 1 |RMP|Overall Hunter College Student review page |https://www.ratemyprofessors.com/school/226 |
| 2 |RMP |Overall Queens College Student review page |https://www.ratemyprofessors.com/school/231 |
| 3 |RMP |Overall Baruch College Student review page |https://www.ratemyprofessors.com/school/222 |
| 4 |RMP |Overall Columbia University Student review page |https://www.ratemyprofessors.com/school/278 |
| 5 |RMP |Overall Binghamton Student review page |https://www.ratemyprofessors.com/school/958 |
| 6 |RMP |Overall Stony Brook Student review page |https://www.ratemyprofessors.com/school/971 |
| 7 |RMP |Overall Brooklyn College Student review page |https://www.ratemyprofessors.com/school/223 |
| 8 |RMP |Overall NYU Student review page |https://www.ratemyprofessors.com/school/675 |
| 9 |RMP |Overall Cornell Student review page |https://www.ratemyprofessors.com/school/298 |
| 10 |RMP |Overall CCNY Student review page |https://www.ratemyprofessors.com/school/224 |

---

## Chunking Strategy

<!-- Describe your chunking approach with enough specificity that someone else could reproduce it.
     Include:
     - Chunk size (characters or tokens) and why that size fits your documents
     - Overlap size and why (or why not) you used overlap
     - Any preprocessing you did before chunking (e.g., stripping HTML, removing headers)
     - What your final chunk count was across all documents -->

**Chunk size:** 256–512 tokens

**Overlap:** 50–100 tokens

**Why these choices fit your documents:** Using student reviews from my sources, the chunks should be smaller to be effective to get the sentiment of the full reviews and not anything extra.

**Final chunk count:** 369

---

## Embedding Model

<!-- Name the embedding model you used and explain your choice.
     Then answer: if you were deploying this system for real users and cost wasn't a constraint,
     what tradeoffs would you weigh in choosing a different model?
     Consider: context length limits, multilingual support, accuracy on domain-specific text,
     latency, and local vs. API-hosted. -->

**Model used:** all-MiniLM-L6-v2 via sentence-transformers because no API key and no rate limits

**Production tradeoff reflection:** Cost not being a constraint means I can use a more powerful embedding model for better accuracy and larger context lengths. Multilingual support isn't as important because these sources are typically in English. Latency is definitely a larger importance as well for better user experience.

---

## Grounded Generation

<!-- Explain how your system enforces grounding — how does it prevent the LLM from answering
     beyond the retrieved documents?
     Describe both your system prompt (what instruction you gave the model) and any structural
     choices (e.g., how you formatted the context, whether you filtered low-relevance chunks).
     Do not just say "I told it to use the documents" — show the actual instruction or explain
     the mechanism. -->

**System prompt grounding instruction:** The model is given a system prompt with four hard rules:

> You are a factual assistant that answers questions about colleges using ONLY the student reviews and rating summaries provided in the context. Follow these rules strictly:
> 1. Use only information found in the context below. Do NOT use any outside or prior knowledge about these colleges.
> 2. If the context does not contain enough information to answer, reply with exactly: "I don't have enough information on that."
> 3. Refer to schools by name (the context labels each excerpt with its source school).
> 4. Do not invent ratings, numbers, or quotes that are not in the context.

Two structural choices reinforce this beyond the prompt:

- **Context formatting:** retrieved chunks are passed as a numbered list where each excerpt is prefixed with its source school, the review's rating, and date (e.g. `[1] (REVIEW — Hunter College, rated 2.7, Jun 2nd, 2026)`). Labeling every excerpt with its source makes it possible for the model to attribute claims and makes off-context answers stand out.
- **Low-relevance filtering (pre-LLM decline):** before the LLM is ever called, the top retrieved chunk's cosine distance is checked against a `MAX_DISTANCE = 0.75` threshold. If nothing is even loosely relevant, the system returns the decline message *without* calling the model at all — so an off-topic question (e.g. "the football team's win-loss record") can't trigger a hallucinated answer. Generation also runs at `temperature=0.1` to keep output close to the evidence.

**How source attribution is surfaced in the response:** Attribution is generated **programmatically from the retrieved chunks' metadata**, not left to the LLM to remember. After generation, `format_sources()` collapses the retrieved chunks into one entry per distinct school, with the number of excerpts that school contributed and its source URL (e.g. `Hunter College (3 excerpts) — https://www.ratemyprofessors.com/school/226`). These sources are returned as a separate `sources` list alongside the answer and rendered in their own "Retrieved from" panel in the Gradio UI. If the answer is the decline message, the source list is deliberately left empty so we never cite sources for a non-answer.

---

## Evaluation Report

<!-- Run your 5 test questions from planning.md through your system and record the results.
     Be honest — a partially accurate or inaccurate result that you explain well is more
     valuable than a suspiciously perfect result. -->

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 |What opinions do students have about food and dining options? |pricy, limited food options, etc |lack of kosher food options on Stony campus, food trucks at Queens, variety at Brooklyn, not good or ok from Stony Brook and Bing| Relevant|Accurate |
| 2 |What do students say about the crowdedness of the colleges? |Most of the colleges are expected to be crowded especially in the city |According to the reviews, Columbia University's facilities, including libraries and gym, are always overcrowded. There is no mention of overcrowding at the other colleges. |Relevant |Partially Accurate |
| 3 |What do students review the most positive from the colleges? |Opportunities, clubs, activities |Cornell has good programs and faculty and reputation, baruch diversity and programs as well, stony brook academics but more neutral review |Relevant |Accurate |
| 4 |What do students review the most negative from the colleges? |Classes, registration |CCNY has strong regrets from students choosing the school, Columbia intense competition, safety concerns |Relevant |Accurate |
| 5 |What do students say about the professors of the colleges? |Absent, hit or miss, great|a lot of some great some not, CCNY and stony brook don't care about you |Relevant |Accurate |

**Retrieval quality:** Relevant / Partially relevant / Off-target  
**Response accuracy:** Accurate / Partially accurate / Inaccurate

---

## Failure Case Analysis

<!-- Identify at least one question where retrieval or generation did not work as expected.
     Write a specific explanation of *why* it failed, tied to a part of the pipeline.

     "The answer was wrong" is not an explanation.

     "The relevant information was split across a chunk boundary, so retrieval returned
     only half the context — the model didn't have enough to answer correctly" is an explanation.

     "The embedding model treated the professor's nickname as out-of-vocabulary and returned
     results from an unrelated review" is an explanation. -->

**Question that failed:** What do students say about the crowdedness of the colleges?

**What the system returned:** According to the reviews, Columbia University's facilities, including libraries and gym, are always overcrowded. There is no mention of overcrowding at the other colleges.

**Root cause (tied to a specific pipeline stage):** For some reason when I had a typo in the question (crowdiness instead of crowdedness), it produced a more thorough answer. It jsut leads to not enough reviews about crowding.

**What you would change to fix it:** Use more reviews and chunks along with running the query to get the best chunks from each college source than overall top 5.

---

## Spec Reflection

<!-- Reflect on how planning.md shaped your implementation.
     Answer both questions with at least 2–3 sentences each. -->

**One way the spec helped you during implementation:** It helped me organize what what going on and get all the information down to know what I was doing with implementation. It made me put down questions I wanted to ask and think about what my sources tell.

**One way your implementation diverged from the spec, and why:** I changed some questions during implementation because I realized it wasn't the best questions for student reviews and more so catered towards hard ratings. I also got rid of the overall ratings of each college that is given at the top of each source to better focus on student reviews.

---

## AI Usage

<!-- Describe at least 2 specific instances where you used an AI tool during this project.
     For each: what did you give the AI as input, what did it produce, and what did you
     change, override, or direct differently?

     "I used Claude to help me code" is not sufficient.
     "I gave Claude my Chunking Strategy section from planning.md and asked it to implement
     chunk_text(). It returned a function using a fixed character split. I overrode the
     chunk size from 500 to 200 because my documents are short reviews, not long guides." -->

**Instance 1**

- *What I gave the AI:* I first gave chatgpt my planning.md for milestone 3 with sources and chunk information.
- *What it produced:* It was a little confusing what it produced with messy outputs of the text.
- *What I changed or overrode:* I broke it down more and tried Claude to check the scraping was good before moving onto the chunk. It made it a lot cleaner and readable.

**Instance 2**

- *What I gave the AI:* I gave Claude my planning.md and requirements for retrieving. 
- *What it produced:* The retrieval.py file
- *What I changed or overrode:* I ran the code and noticed some of the test queries wasn't as good so I changed the questions and added all my questions to ensure the results were good.
