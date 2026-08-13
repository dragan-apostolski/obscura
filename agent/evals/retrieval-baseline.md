# Retrieval baseline probe — 9 questions across categories

Quick check of retrieval quality before the eval harness existed. Seed for the golden dataset.

**What's measured:** does the top result come from the *correct source* (right camera manual /
right technique guide)? This is source-level recall, **not** answer correctness — a chunk from the
right manual can still be the wrong section. Real answer quality comes with Ragas.

- `top1` = correct source is the #1 result
- `top3(#2)` = correct source is in top 3, at rank 2
- `MISS` = not found in top 10

| Category | Question | Expected source | Vector | Hybrid+Rerank |
|---|---|---|---|---|
| concept | What is bokeh? | technique-bokeh | top1 | top1 |
| concept | When should I use a fast shutter speed? | technique-shutter | top1 | top1 |
| concept | What is the rule of thirds? | rule-of-thirds | top1 | top1 |
| concept | How does aperture affect depth of field? | technique-depth | top1 | top1 |
| sanity | What is ISO? | technique-iso | top1 | top1 |
| entity-fuji | How do I set custom white balance on the X100V? | x100v | top1 | top3(#2) |
| entity-fuji | How do I use film simulation modes on the X100V? | x100v | top1 | top1 |
| entity-canon | How do I set custom white balance on the Canon EOS R5? | canon | top1 | top1 |
| entity-canon | How do I enable animal eye autofocus on the Canon R5? | canon | top3(#2) | top1 |

## Top-1 hit rate

| Category | Vector | Hybrid+Rerank |
|---|---|---|
| concept | 4/4 | 4/4 |
| sanity | 1/1 | 1/1 |
| entity | 3/4 | 3/4 |
| **total** | **8/9** | **8/9** |

## Read

- Both pipelines retrieve the right manual **8/9**. The single-query "wrong camera" scare does **not**
  generalize.
- Vector and hybrid+rerank basically **trade**: vector wins the X100V white-balance case, hybrid wins the
  Canon animal-eye case. Neither is clearly better on this sample.
- Entity questions are the weak spot (3/4), but the miss is rank #2, not buried. Marginal, not pervasive.

## Caveats

- Source-level recall, not answer quality.
- n=9 is directional, not conclusive.
- "Correct source" labels were hand-authored.

## Prime fix to test later

**Contextual embeddings** (Anthropic Contextual Retrieval) — prepend a short context blurb naming the
camera/section to each chunk before embedding. Targets the diagnosed bug: answer chunks don't contain
"X100V" in their text, only in the filename. Measure the gain against this baseline.
