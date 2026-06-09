# Project 1 Planning: The Unofficial Guide

> Write this document before you write any pipeline code.
> Your spec and architecture diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Update the Retrieval Approach and Chunking Strategy sections if you change your approach during implementation.
> Update this file before starting any stretch features.

---

## Domain

<!-- What domain did you choose? Why is this knowledge valuable and hard to find through official channels? -->
Student reviews of colleges. It is valuable because there are so many different colleges to choose from and so much information out there to compare along with biased information from official channels and it can be overwhelming.

---

## Documents

<!-- List your specific sources: URLs, subreddit names, forum threads, or file descriptions.
     Aim for at least 10 sources that together cover different subtopics or perspectives within your domain. -->

| # | Source | Description | URL or location |
|---|--------|-------------|-----------------|
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

<!-- How will you split documents into chunks?
     State your chunk size (in tokens or characters), overlap size, and explain why those
     numbers fit the structure of your documents.
     A review-heavy corpus warrants different chunking than a long FAQ. -->

**Chunk size:** 256–512 tokens

**Overlap:** 50–100 tokens

**Reasoning:** Using student reviews from my sources, the chunks should be smaller than would a long FAQ and would be effective to get the sentiment of the reviews.
---

## Retrieval Approach

<!-- Which embedding model are you using (e.g., all-MiniLM-L6-v2 via sentence-transformers)?
     How many chunks will you retrieve per query (top-k)?
     If you were deploying this for real users and cost wasn't a constraint, what tradeoffs
     would you weigh in choosing a different embedding model — context length, multilingual
     support, accuracy on domain-specific text, latency? -->

**Embedding model:** all-MiniLM-L6-v2 via sentence-transformers

**Top-k:** 5

**Production tradeoff reflection:** Cost not being a constraint means I can use a more powerful embedding model for better accuracy and larger context lengths. Multilingual support isn't as important because these sources are typically in English. Latency is definitely a larger importance as well for better user experience.

---

## Evaluation Plan

<!-- List your 5 test questions with their expected correct answers.
     Questions should be specific enough that you can judge whether the system's response
     is right or wrong. "What are good dining halls?" is too vague.
     "What do students say about wait times at [dining hall name] during lunch?" is testable. -->

| # | Question | Expected answer |
|---|----------|-----------------|
| 1 |What opinions do students have about food and dining options? |pricy, limited food options, etc |
| 2 |What do students say about the crowdiness of the colleges? |Things about elevators not working, lots of students, etc |
| 3 |What do students review the most postive from the colleges? |Location and safety are consistently the some of the highest rated features throughout all but from reviews |
| 4 |What do students review the most negative from the colleges? |Social and food are consistently the worst rated features throughout all but from reviews |
| 5 |What do students say about the professors of the colleges? |absent, passionate, etc |

---

## Anticipated Challenges

<!-- What could go wrong? Name at least two specific risks with reasoning.
     Consider: noisy or inconsistent documents, missing source attribution, off-topic
     retrieval, chunks that split key information across boundaries. -->

1. Missing retrieval of the ratings in the reviews and the overall rating because it's in a different format than the review text.

2. Chunks that split reviews up creating weird inconsistent summaries

---

## Architecture

<!-- Draw a diagram of your pipeline showing the five stages:
     Document Ingestion → Chunking → Embedding + Vector Store → Retrieval → Generation
     Label each stage with the tool or library you're using.
     You can use ASCII art, a Mermaid diagram, or embed a sketch as an image.
     You'll use this diagram as context when prompting AI tools to implement each stage. -->

[Document Ingestion: Rate my professor]
   ↓
[Chunking: 256–512 tokens size, 50–100 tokens overlap]
   ↓
[Embeddings: all-MiniLM-L6-v2 via sentence-transformers]
   ↓
[Vector Store: ChromaDB]
   ↓
[Retrieval: top-k = 5]
   ↓
[Generation: Groq (llama-3.3-70b-versatile)]

---

## AI Tool Plan

<!-- For each part of the pipeline below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, which requirements)
     - What you expect it to produce
     - How you'll verify the output matches your spec

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Chunking Strategy section and ask it to implement chunk_text()
     with my specified chunk size and overlap" is a plan. -->

**Milestone 3 — Ingestion and chunking:** Claude/ChatGPT - implement chunk_text() with 256–512 tokens size, 50–100 tokens overlap from chunking strategy section

**Milestone 4 — Embedding and retrieval:** Claude/ChatGPT - input retrieval section to implement a retrieval function with top 5 most similar chunks

**Milestone 5 — Generation and interface:** Claude/ChatGPT - input the retrieved chunks and questions with the LLM used to implement a response
