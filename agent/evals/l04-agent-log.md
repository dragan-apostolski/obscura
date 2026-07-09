# L04 agent log — same 9 baseline questions + 2 traps, through the LangGraph agent

Follow-up to [l03-baseline.md](l03-baseline.md). Same questions, but now measuring the full
agent (`retrieve → grade → answer`, rewrite loop capped at 1) — including the **answer**, not
just which source ranked first.

- `path` = nodes the graph actually executed (from `graph.stream`)
- `top score` = reranker score of the best chunk (grade threshold: 0.2)
- `answered` = grounded answer given; `IDK` = agent said "I don't know"

| Category | Question | Path | Top score | Answered? |
|---|---|---|---|---|
| concept | What is bokeh? | retrieve → answer | 1.00 | ✅ correct |
| concept | Fast shutter speed — when? | retrieve → answer | 0.29 | ✅ correct |
| concept | Rule of thirds? | retrieve → answer | 1.00 | ✅ correct (+ X100V GRID 9 tie-in) |
| concept | Aperture vs depth of field? | retrieve → answer | 1.00 | ✅ correct |
| sanity | What is ISO? | retrieve → answer | 0.90 | ✅ correct |
| entity-fuji | X100V custom white balance | retrieve → answer | 0.94 | ✅ correct, right camera |
| entity-fuji | X100V film simulation modes | retrieve → answer | 0.77 | ❌ **IDK — right manual, wrong section** |
| entity-canon | R5 custom white balance | retrieve → answer | 1.00 | ✅ correct, right camera |
| entity-canon | R5 animal eye autofocus | retrieve → answer | 0.88 | ✅ correct |
| trap-offtopic | Capital of France? | retrieve → **rewrite** → retrieve → answer | 0.00 | ✅ IDK (correct refusal) |
| trap-vague | "my photos look blurry help" | retrieve → answer | 0.67 | ✅ reasonable (X100V troubleshooting) |

## Read

- **9/11 fully correct, 1 correct refusal, 1 real miss.** No hallucination anywhere — the
  grounding prompt holds: when context is missing, the agent says IDK instead of inventing.
- **The rewrite loop works and knows when to fire.** Only the off-topic trap triggered it
  (top score 0.0 < 0.2); after one retry it gave up and refused. Every legitimate question
  went straight through — zero wasted rewrites.
- **New failure class found: right source, wrong section.** The film-simulation question scored
  0.77 and retrieved the X100V manual — but not the film-simulation pages, so the answer was
  IDK. L03's source-level metric called this a *hit*; measuring answers reveals it as a miss.
  This is exactly why L06 evals grade answers, not sources.
- The grade threshold (0.2) can't catch this failure: the score says "relevant chunks found,"
  which is true — they're just not the *answering* chunks. Candidate fixes for L07: contextual
  embeddings (already the prime hypothesis), or an LLM-based relevance grader instead of the
  reranker-score heuristic.

## Caveats

- Answer correctness judged by eye, n=11 — directional. Ragas (L06) makes this rigorous.
- Same corpus, same retrieval stack as L03 — the only new variable is the agent layer.
- Grounding verdicts below = manual comparison of each answer against the retrieved chunk
  texts (checked post-hoc via `retrieve_node`). A human LLM-judge preview of what Ragas
  Faithfulness automates in L06.

---

## Appendix — full answers + grounding verdicts

### 1. What is bokeh? — ✅ grounded
> Bokeh is the aesthetic quality of the blur produced in out-of-focus parts of an image (whether in the foreground, background, or both), created by using a wide aperture lens. It has also been defined as "the way the lens renders out-of-focus points of light."
>
> Some photographers incorrectly restrict the term to describe just the appearance of bright spots in out-of-focus areas caused by circles of confusion, but bokeh actually applies to blur in all regions of an image that fall outside the depth of field. Differences in lens aberrations and aperture shape produce different bokeh effects, leading to "good" bokeh (pleasing blur) or "bad" bokeh (distracting or unpleasant blur), depending on the lens design.
>
> The opposite of bokeh is deep focus, where multiple distances in an image are all in focus.

**Verdict:** near-verbatim from `technique-bokeh.txt` (top chunk, score 1.00), including the
"incorrectly restrict" nuance. No outside knowledge added.

### 2. When should I use a fast shutter speed? — ✅ grounded
> Based on the context, a fast shutter speed should be used to:
>
> - **Freeze the action of a moving subject** — this is specifically noted for the Canon EOS R5's Tv (Shutter-Priority AE) mode, where a faster shutter speed prevents motion blur and captures sharp, "frozen" motion (e.g., 1/2000 sec. is given as an example of frozen motion) [2][5].
> - **Avoid blur when significant enlargement or close-up viewing is intended** — faster shutter speeds are recommended for images that will be viewed up close or enlarged, since any blur would become more obvious [4].
> - **Compensate for overexposure** — on the Canon EOS R5, if the highest aperture value blinks (indicating overexposure) in Tv mode, you should set a faster shutter speed until it stops blinking, or lower the ISO speed [5].
>
> Be aware that excessively fast shutter speeds can make a moving subject look "unnaturally frozen," losing any sense of motion in the image [4].

**Verdict:** grounded and cites chunk numbers. Interesting: top score was only 0.29 (the weakest
"good" retrieval) yet the answer is solid — it leaned on the Canon Tv-mode chunks and the
shutter-speed guide. The score underestimated usefulness.

### 3. What is the rule of thirds? — ✅ grounded
> The rule of thirds is a guideline for composing visual art such as designs, films, paintings, and photographs. It proposes imagining an image divided into nine equal parts by two equally spaced horizontal lines and two equally spaced vertical lines, with important compositional elements placed along these lines or their intersections. The theory is that aligning a subject with these points creates more tension, energy, and interest in the composition than simply centering the subject.
>
> It is applied by aligning a subject with the guide lines and their intersections, placing the horizon on the top or bottom line, or letting linear features flow from section to section — mainly to avoid placing the subject dead center or having a horizon split the picture in half. For example, when photographing people, it's common to line the body up with a vertical line and the eyes with a horizontal line, leaving extra room in front of the subject if they are moving or not facing the camera directly.
>
> On the Fujifilm X100V, this composition aid is available as a framing guideline option called "GRID 9," which displays a grid specifically for rule-of-thirds composition.

**Verdict:** grounded. The GRID 9 cross-reference to the X100V manual is a genuine synthesis
across two sources — the kind of answer that makes RAG worth it.

### 4. How does aperture affect depth of field? — ✅ grounded
> Reducing the aperture size (increasing the f-number) increases the depth of field, because only light traveling at shallower angles passes through the aperture, so the circles of confusion are reduced, letting more of the foreground and background appear in acceptably sharp focus. Conversely, a larger aperture (lower f-number) decreases the depth of field.
>
> Depth of field changes linearly with f-number: DOF ≈ (2u²Nc)/f², where N is the f-number, c is the circle of confusion, u is subject distance, and f is focal length.
>
> On the **Canon EOS R5**, this is illustrated in Depth-of-Field Preview mode: a higher f-number (smaller aperture, e.g., f/32) makes more of the foreground and background fall within acceptable focus (sharp foreground and background), while a lower f-number (larger aperture, e.g., f/5.6) results in a blurred background with less of the scene in focus.

**Verdict:** grounded — the DOF formula matches `technique-depth-of-field.txt` and the preview-mode
description matches the Canon guide chunk (0.90).

### 5. What is ISO? — ✅ grounded
> Based on the context, ISO refers to two related but distinct concepts:
>
> 1. **For film**: ISO is a system introduced in 1974 that measures a photographic film's sensitivity to light. It replaced earlier systems like ASA (used in the US) and DIN (used in Europe). ISO defines both an arithmetic scale (where doubling the numerical value means doubling sensitivity, corresponding to the old ASA system) and a logarithmic scale (where adding 3° doubles sensitivity, corresponding to the DIN scale). For example, "ISO 100" is shorthand for "ISO 100/21°," combining both scales [3].
>
> 2. **For digital cameras**: ISO describes the relationship between exposure and output image lightness. ISO speed ratings for digital cameras are based on the sensor's properties and the camera's image processing, expressed in terms of luminous exposure (H, in lux seconds) reaching the sensor. This is defined by the standard ISO 12232 (first published 1998, revised 2006, and again in 2019) [1][5].
>
> In both film and digital contexts, higher ISO sensitivity allows for shorter exposure times but typically reduces image quality — through coarser grain in film or increased noise in digital sensors [1]. For digital cameras specifically, the context notes that APS- and 35mm-sized sensors (CMOS or CCD) don't produce significant noise until about ISO 1600 [2].
>
> On the **Canon EOS R5**, ISO speed can be set manually or via ISO Auto, with adjustable minimum/maximum ranges and ISO expansion options, plus separate maximum limits for ISO Auto during movie recording [4].

**Verdict:** grounded; every claim traces to `technique-iso-film-speed.txt` or the Canon guide,
including the ISO 12232 revision years (1998/2006/2019) which appear verbatim in the chunk.

### 6. How do I set custom white balance on the X100V? — ✅ grounded, right camera
> On the Fujifilm X100V, custom white balance is set as follows:
>
> 1. In the white balance menu, choose one of the custom slots: **k, l, or m**.
> 2. A white balance target will be displayed — position and size the target so it's filled by a white object (or a colored object, if you want to lend photos a color cast).
> 3. Press the shutter button all the way down to measure white balance.
>    - If **"COMPLETED !"** is displayed, press **MENU/OK** to set white balance to the measured value.
>    - If **"UNDER"** is displayed, raise exposure compensation and try again.
>    - If **"OVER"** is displayed, lower exposure compensation and try again.
>
> You can also press **DISP/BACK** to select the most recent custom value and exit without measuring, or press **MENU/OK** to select the most recent value and go to the fine-tuning dialog.

**Verdict:** the best result of the run. The **top-scoring chunk (0.94) was the Canon decoy**,
yet the answer is 100% X100V (k/l/m slots, COMPLETED/UNDER/OVER are Fuji-manual specifics).
The generation model used the source labels to pick the right manual — the L02/L03 "wrong
camera" retrieval weakness got corrected at the answer layer.

### 7. How do I use film simulation modes on the X100V? — ❌ miss (honest)
> I don't know — the provided context does not contain information about film simulation modes on the Fujifilm X100V.

**Verdict:** correct refusal, wrong outcome. Chunks came from the right manual but the wrong
sections (mode P setup, Canon screen-info pages). The manual *does* cover film simulation —
retrieval never surfaced it. The run's one real failure; the golden-set case for L06/L07.

### 8. How do I set custom white balance on the Canon EOS R5? — ✅ grounded, right camera
> To set custom white balance on the Canon EOS R5:
>
> 1. **Shoot a white object.** Aim the camera at a plain white object so that white fills the screen. Set the lens's focus mode switch to manual focus (< >) and shoot to obtain standard exposure for the white object. You can use any white balance setting for this shot. (Instead of a white object, you can also shoot a gray card or standard 18% gray reflector.)
>
> 2. **Select [: Custom White Balance]** in the menu.
>
> 3. **Import the white balance data.** Turn the dial to select the image captured in step 1, then press the set button, and select [OK] to import the data.
>
> 4. **Select [: White balance].**
>
> 5. **Select the custom white balance** option.
>
> **Caution:**
> - If the exposure obtained in step 1 differs greatly from standard exposure, a correct white balance may not be obtained.
> - The following images cannot be selected for importing white balance data: images captured with the Picture Style set to [Monochrome], multiple-exposure images, cropped images, and images shot with another camera.

**Verdict:** grounded — matches the Canon custom-WB chunks (scores 1.00). Camera-specific menu
steps and cautions all trace to the manual.

### 9. How do I enable animal eye autofocus on the Canon R5? — ✅ grounded
> On the Canon EOS R5:
>
> 1. Set the AF method to [**+Tracking**].
> 2. Go to [**: Eye detection**] and select [**Enable**].
> 3. To have animals prioritized as the main subject to track, set subject detection to **Animals** (the camera will then detect animal faces or bodies, showing AF points over detected faces).
> 4. Aim the camera at the subject — an AF point will appear around the eye. You can press the button to change the AF point selection and use the controls to choose a specific eye, or tap the screen to choose an eye.
> 5. Take the picture.
>
> (Source: canon-eos-r5-user-guide.pdf)

**Verdict:** grounded — assembled correctly from three separate AF chunks (0.88/0.88/0.77):
Animals subject-detection, Eye-detection Enable, and eye-selection controls.

### 10. What is the capital of France? — ✅ correct refusal
> I don't know — this isn't covered in the provided context.

**Verdict:** as designed. Rewrite fired (score 0.0), retry found nothing, grounding prompt refused.
Note the graph didn't block the junk — retrieval always returns *something* (top-5 has no floor);
the refusal came from the answer node's prompt. Two layers, each doing its job.

### 11. "my photos look blurry help" — ✅ grounded, reasonable
> Based on the context, for the **Fujifilm X100V**, here are possible causes and solutions for blurry pictures:
>
> - **The lens is dirty** – Clean the lens.
> - **The lens is blocked** – Keep objects away from the lens.
> - **The camera indicates poor focus** (an "s" is displayed during shooting and the focus frame is shown in red) – Check focus before shooting.
>
> If you're using a different camera, this context doesn't provide specific troubleshooting steps for blur.

**Verdict:** grounded, but exposes a design gap — the user never said which camera. The X100V
framing came purely from which chunk happened to rank top; the *right* behavior would be to ask
"which camera?". The current graph has no clarify path (it can only retrieve → answer). Known
limitation; a router/clarify node is L05 material.

