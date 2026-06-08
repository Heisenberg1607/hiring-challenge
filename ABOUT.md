# ABOUT.md

## Why this role

When I initially started working with Voice agents, that was the time I tried making a simple cascading voice pipeline  (STT -> LLM -> TTS). 
As I pushed deeper, my interest grew tremendously. I explored webSockets, Pipecat and LiveKit , WebRTC, created self-improving voice agents,read research papers about Voice AI orchestration. 
When i came across AgentCollect's Full Stack Engineering role, it immediately hit me that this is the work that excites me, working with full-stack systems and desigining low latency pipelines along with agentic workflows that handle context, tool callings efficiently. 

I love the use-case of using voice AI for B2B debt collection, and how it can automate the work and save time with personalized experience for both sides. Secondly, the stakes are real when working in finance, and handling 
such challenges and problems is something I am excited for. 


## How you work with AI tools

I use AI (Claude, Cursor) as a thinking partner and an accelerator, but I keep the design decisions and only ship what I can defend.

On this challenge I used it most before writing any code — to pressure-test the plan. It caught a real error in my first instinct: I had entity-matching as just another additive signal, when it needs to be a hard gate that runs first. A strong, well-sourced contact for the *wrong* company should score zero, not high. That reframing changed the whole architecture.

Where I trust the model: articulation, calibration sanity-checks, and boilerplate. Where I override it: judgment calls, scoring weights, and anything I can't personally explain. When my first confidence weights flagged too many good rows for review, I recalibrated by hand against worked examples rather than accepting the output. The rule I follow is simple — if I can't explain why a line is there, it doesn't ship.

## Your last project (structured)

Recently, I built a voice AI mental health companion. Users can get a personalized therapy session where they can talk to human-like AI to vent thoughts and emotions. 
-Super low latency <500ms using Pipecat and WebRTC. 
-Grafana monitoring for the AI agent to keep track of latency, cost, ai-decisions every turn. 
-Self-improvement loop for the agent using evaluation metrics in Cekura.
-Efficient context summarization every 6 turns. 
-Self-harm detection redirecting to emergency helplines. (Call escalation).

- **One ambiguity you faced and how you resolved it:**
A bad therapy response just feels off, and no test catches that.
When I started evaluating my AI therapist, I had no benchmark. Does the agent respond with enough warmth? Is it listening or just pattern matching? Is it being concise or cutting the user off emotionally? There's no dataset for "good therapy conversation" I could compare against.
I had to define quality myself. I landed on five evaluation dimensions with Cekura, Empathy, Active Listening, Safety Detection, Conciseness, and Task Completion, and scored every session turn against them. But even then, the rubric was my own judgment. A 6/10 on empathy is not objective. It's a hypothesis.
What changed my thinking: I stopped asking "is the response correct?" and started asking "would a user feel heard after this turn?" That shift — from correctness to emotional resonance — was the real ambiguity. And it changed how I designed every prompt after that.

- **One tradeoff you made and why:**
Context vs Cost. 
-> Initially, I was sending the entire chat history to the LLM as context, which gave super good accuracy but the cost was increased heavily after every conversation turn. So, I shifted to context summarization after every 6 turns which dropped the latency as well as cost. But I started losing some nuance. So I added emotional tags along with summary.

- **One mistake you made and what you changed:**
-> I created the entire pipeline from scratch using WebSockets and ElevenLabs streaming. When I pushed it to production, it gave audio jitters and gaps giving a bad voice experience. (latency 800ms).
Later on I shifted to Pipecat + WebRTC (along with Deepgram, OpenAI and ElevenLabs) which gave a smooth voice-to-voice experience as well as Noise cancellation using Krisp. 
(I learnt a lot about creating voice AI when I created the entire pipeline from scratch). 

- **One review comment that made you change your mind:**
A peer flagged that my VAD (voice activity detection) was cutting off users mid-sentence during pauses in emotional speech, which is common in therapy contexts. I'd tuned it for speed, not empathy. Adjusted the end-of-utterance silence threshold significantly. Changed how I think about VAD parameters as a UX decision, not just a latency one.

## Anything you'd improve about THIS challenge or your CLAUDE.md

No ground-truth row to calibrate against:
A confidence score is itentionally open-ended but there's no way a candidate can validate their model if it's caliberated reasonably or not.
An annoted reference row would help the candidate, check their logic.
---

### How to run

```bash
python contact_finder.py
```

Reads `challenge/data/companies.csv` and `challenge/mocks/enrichment_responses.json`, writes `output.csv`, and prints a summary table. Standard library only — no dependencies.

**Result on the mock set:** 30 companies → 4 auto-accept, 26 needs-human-review, in three tiers: 4 fully-confident contacts (name + role + email, confidence 71–87); ~6 where a person was identified but no reachable handle exists (flagged, with a head-start for the reviewer); ~11 genuine cannot-verify rows with no source data. The high review rate is intended — per the clarifications, a high `needs_human_review` rate on genuinely hard rows is a good result, not a failure.

**Process evidence:** see the commit timeline. `PLAN.md` was committed first (before reading `CLARIFICATIONS.md`), then the slice. Adaptations after reading the clarifications — threshold 75→70, the AP-first persona priority order, and the suppression/opt-out check — live in the build commits and are summarized above, not retrofitted into the plan.v