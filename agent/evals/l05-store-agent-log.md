# L05 — Store agent test run (11 questions)

Date: 2026-07-09 · Agent: `app/store_agent.py` (langchain `create_agent`, claude-sonnet-5, max_tokens 4096, adaptive thinking)
· Tools: `search_products` (with `Literal` enums on type/sensor_format), `get_product_info`, `search_manual`, `explain_technique`

Mix of the L05 smoke questions (Q1–Q5) and new gear questions probing facets, edge cases, and scope (Q6–Q11).
Full answers in the appendix.

## Results

| # | Question | Tools called | Verdict |
|---|---|---|---|
| 1 | a7 IV in stock / price? | `get_product_info(sony-a7-iv)` | ✅ correct price + stock from DB |
| 2 | Set white balance on a7 IV | `search_manual(sony-a7-iv)` | ✅ real menu path, source cited |
| 3 | What is bokeh / get more | `explain_technique` | ✅ grounded in technique guide |
| 4 | Change white balance (no camera) | *(none)* | ✅ asks which camera — clarify path |
| 5 | a7 IV vs Z6 II for video | `get_product_info` ×2 | ✅ both fetched; flagged spec-sheet limits (see F2) |
| 6 | Cinema cameras under €5000 | `search_products(type=cinema)` | ✅ fetched all 8, self-filtered to 5 under €5k, stock noted |
| 7 | Do you sell Fujifilm? | *(none)* | ✅ correct "no" from system-prompt brand line |
| 8 | Cheapest full-frame in stock | `search_products(full-frame, in_stock_only)` | ✅ Nikon Z5 €999 (rows are price-sorted; picked first) |
| 9 | Z8 have IBIS? | `get_product_info` → `search_manual(nikon-z8)` | ⚠️ **grounding violation** (see F1) |
| 10 | Film simulations on X100V | *(none)* | ⚠️ declined, but we DO have that manual (see F3) |
| 11 | Capital of France? | *(none)* | 🟡 declined per scope rule… then answered anyway (see F4) |

Score: 8/11 clean, 2 instructive failures, 1 cosmetic.

## Findings

**F1 — Ungrounded spec claim (Q9), the L06 poster child.** The agent did everything right
procedurally: fetched the product, then tried the manual for the stabilization question. Both
came back empty — the Z8's `specs` jsonb has only warranty/camera_type/sensor_type, and
`search_manual` returned "no manual on file". It then answered anyway, confidently:
"5-axis sensor-shift VR". That's model world-knowledge, not tool output. The claim happens to
be true of the real Z8, which is exactly why this failure mode is dangerous — it's invisible
until the model's knowledge is stale or wrong (e.g. prices, firmware features). The system
prompt says "if the tools don't have the answer, say you don't know" — it was ignored when
parametric knowledge felt confident. Source-level checks can't catch this; **answer-level
faithfulness (Ragas) is the tool for it → L06.**
Possible fixes to evaluate: stronger grounding language; richer `specs` at crawl time; or a
"say what the spec sheet doesn't cover" instruction.

**F2 — Honest spec-sheet awareness (Q5, the counter-example).** In the video comparison the
agent wrote "4K listed at 30p (144 Mbps) *in our spec sheet*" for the Z6 II — explicitly
attributing the number to the catalog rather than asserting it as the camera's full
capability. Same model, same prompt, opposite behavior from F1. Grounding discipline is
inconsistent, not absent — which is measurable, not fixable by vibes.

**F3 — The manual/catalog mismatch, observed live (Q10).** We have the full X100V manual in
the vector store (237 chunks), but the store doesn't sell Fujifilm. The agent reasoned from
the brand line: "we don't carry Fujifilm → I don't have manual access for the X100V" — and
never tried `search_manual`, which would have worked. As *store* behavior this is arguably
correct (don't provide support for products you don't sell); as a *system* statement
("I don't have manual access") it's false. Decision needed: either treat manuals-without-
products as dead weight (drop X100V/X-T5 chunks), or tell the agent manuals exist
independently of the catalog. Deferred at catalog-build time; now we have data for the
decision.

**F4 — Literal-but-cheeky scope handling (Q11).** Off-topic question was declined per the
prompt rule… followed by "(For the record, though: it's Paris.)" Harmless, arguably good UX,
but a literal violation of "politely decline anything else". A stricter product would tighten
the instruction; for the portfolio demo it's fine as is.

**F5 — Slug guessing is now the norm and it works (Q1, Q5, Q9).** The agent skips
`search_products` and writes slugs directly (`sony-a7-iv`, `nikon-z6-ii`, `nikon-z8`) —
all correct, format anchored by the docstring example. The prompt only mandates resolution
"when unsure", and it apparently never is. Safety net (invalid slug → "not in catalog" +
list of manuals) remains untested in live traffic. Watch in L06.

**F6 — Client-side filtering over tool-side (Q6).** For "cinema under €5000" it called
`search_products(type=cinema)` with no price filter (the tool has none) and filtered the 8
rows itself — correctly. Small context cost, correct result. If catalogs grew, a
`max_price` param would be the fix; at 63 products it's a non-issue.

## Notes for L06

- Q9 (F1) and Q5 (F2) become golden-set items testing faithfulness on spec questions.
- Q10 (F3) forces the manual-coverage design decision before the golden set is authored.
- Add an invalid-slug probe to exercise the F5 safety net deliberately.
- These 11 Q&As + the L03 9-question baseline = ~20 seed items of the golden dataset.

## Appendix — full transcripts

### Q1: Is the Sony a7 IV in stock? How much does it cost?

Tools: `get_product_info({"product": "sony-a7-iv"})`

> Yes, the Sony a7 IV is in stock, priced at €2,049.
> 
> It's a 33MP full-frame mirrorless hybrid with 4K 60p 10-bit video, Real-time Eye AF, 10 fps shooting, in-body stabilization, and weather sealing. Let me know if you'd like more details!

### Q2: How do I set white balance on the a7 IV?

Tools: `search_manual({"query": "how to set white balance", "product": "sony-a7-iv"})`

Sources: sony-a7-iv-manual.pdf

> Here's how to set white balance on the Sony a7 IV (source: sony-a7-iv-manual.pdf):
> 
> **Basic setting:**
> MENU → 🎨 (Exposure/Color) → [White Balance] → [WB (White Balance)] → choose your desired setting:
> - **Auto** – camera detects and adjusts automatically
> - **Preset options** (Daylight, Cloudy, Fluorescent, etc.) – matches a specific light source
> - **C.Temp./Filter** – manually set color temperature and CC filter effect (adjust with the rear dials)
> - **Custom 1/2/3** – memorize a white balance you calibrate yourself
> 
> **To set a Custom white balance:**
> 1. MENU → Exposure/Color → White Balance → WB → select Custom 1/2/3, press right on the control wheel.
> 2. Select the custom WB set icon, press center.
> 3. Point the camera so a white/gray card fully fills the capture frame, press center to capture. You'll hear the shutter sound and see "Captured the custom WB data."
> 4. Press center again to register it.
> 
> **Extra options:**
> - **Priority Set in AWB**: choose whether Auto WB prioritizes Standard, Ambience (warmer), or White tones — via MENU → Exposure/Color → White Balance → Priority Set in AWB.
> - **Shutter AWB Lock**: locks white balance while the shutter is half-pressed or during continuous shooting, so it doesn't shift mid-burst.
> - **Shockless WB**: controls how smoothly WB transitions during movie recording if changed mid-shot.
> 
> Let me know if you'd like details on any of these, like custom WB calibration or fine-tuning color tones.

### Q3: What is bokeh and how do I get more of it?

Tools: `explain_technique({"query": "what is bokeh and how to get more of it"})`

Sources: technique-bokeh.txt

> **Bokeh** is the aesthetic quality of the blur in the out-of-focus areas of a photo (background or foreground). It's especially noticeable as soft, round "orbs" around out-of-focus points of light, but it really refers to the overall character of the blur, not just those highlights.
> 
> **How to get more of it:**
> 
> 1. **Use a wide aperture (low f-number)** – e.g., f/1.4–f/2.8. A wide aperture is the main driver of shallow depth of field, which throws the background out of focus.
> 2. **Use a longer focal length** – telephoto lenses (85mm+) compress background and increase blur, which is why portrait lenses (85–150mm) are popular for bokeh.
> 3. **Get closer to your subject / increase subject-to-background distance** – the closer you focus and the farther the background is, the more it blurs.
> 4. **Use a lens known for pleasing bokeh** – lens design (aperture blade shape/count, correction for spherical aberration) affects whether the blur looks smooth and creamy or busy/harsh. Lenses with rounded aperture blades tend to produce smoother, more circular bokeh even when stopped down slightly.
> 5. **Include background highlights** – small light sources or reflections in the background will render as soft blurred circles, making the bokeh effect more visible.
> 
> If you'd like, I can suggest specific cameras/lenses in our catalog that are great for shallow depth of field and pleasing bokeh — just let me know what body or budget you have in mind.

### Q4: How do I change the white balance?

Tools: (no tools)

> I'd be happy to help! Which camera are you using? White balance settings vary between camera menus, so I'll need to know the specific model to give you accurate steps.

### Q5: Compare the Sony a7 IV and the Nikon Z6 II for video.

Tools: `get_product_info({"product": "sony-a7-iv"})` -> `get_product_info({"product": "nikon-z6-ii"})`

> Here's how they stack up for video work:
> 
> **Sony a7 IV – €2,049**
> - 4K up to **60p, 10-bit** (S-Cinetone color profile for pleasing skin tones out of camera)
> - Vari-angle 3" touchscreen (great for vlogging/gimbal work)
> - Dual card slots, one CFexpress Type A
> - 33MP sensor, in-body stabilization, weather sealed
> 
> **Nikon Z6 II – €1,399**
> - 4K listed at **30p** (144 Mbps, H.264) in our spec sheet; also does 1080p up to 120p for slow-mo
> - Tilting 3.2" touchscreen (higher resolution panel: 2.1MP vs Sony's 1.04MP)
> - Dual card slots: CFexpress/XQD + UHS-II SD
> - 24.5MP sensor, in-body stabilization, weather sealed
> - Bundle includes a 128GB SD card, spare battery, and LED light — handy extras for video shooters
> 
> **Bottom line:** If frame rate and codec flexibility for video matter most (4K60 10-bit, S-Cinetone, vari-angle screen for selfie/vlog angles), the **a7 IV** is the stronger dedicated video tool, though it costs more. If you want strong value with solid 4K30 footage, a vibrant tilting screen, and useful bundled accessories at a lower price, the **Z6 II** is very competitive — just check if 30p is enough for your needs, since it doesn't match the a7 IV's 60p 10-bit capability per our listed specs.
> 
> Let me know if you want a deeper dive into autofocus, lens ecosystem, or audio inputs for either camera.

### Q6: What cinema cameras do you have under 5000 EUR?

Tools: `search_products({"type": "cinema"})`

> Here are our cinema cameras priced under €5,000:
> 
> | Camera | Price | Stock |
> |---|---|---|
> | Nikon ZR | €2,349 | In stock |
> | Sony FX2 | €2,999 | In stock |
> | Canon EOS R5 C | €3,499 | Back-order |
> | Sony FX3 | €3,999 | In stock |
> | Canon EOS C70 | €4,499 | Back-order |
> 
> The Nikon ZR, Sony FX2, and Sony FX3 are all currently in stock and ready to ship, while the Canon EOS R5 C and C70 are on back-order. Let me know if you'd like details or a comparison on any of these!

### Q7: Do you sell any Fujifilm cameras?

Tools: (no tools)

> We don't carry Fujifilm at this store — our lineup covers Canon, Sony, Nikon, Panasonic, and OM System camera bodies. Let me know if you'd like recommendations from any of those brands!

### Q8: Whats the cheapest full-frame camera you have in stock right now?

Tools: `search_products({"sensor_format": "full-frame", "in_stock_only": true})`

> The cheapest full-frame camera we currently have in stock is the **Nikon Z5** at **€999**. Want more details on it?

### Q9: Does the Nikon Z8 have in-body stabilization?

Tools: `get_product_info({"product": "nikon-z8"})` -> `search_manual({"product": "nikon-z8", "query": "in-body image stabilization VR"})`

> Yes — the Nikon Z8 features in-body image stabilization (5-axis sensor-shift VR), working alongside its 45.7MP stacked sensor and EXPEED 7 processor for handheld sharpness in stills and video. Unfortunately it's currently out of stock (price €3,449 when available).

### Q10: How do I use film simulations on the Fujifilm X100V?

Tools: (no tools)

> We don't carry Fujifilm cameras at our store — we sell Canon, Sony, Nikon, Panasonic, and OM System bodies, so I don't have manual access for the X100V. If you have one of our brands' cameras and want help with a similar feature (like Picture Profiles on Sony or Color Modes on OM System), let me know and I'd be happy to help!

### Q11: What is the capital of France?

Tools: (no tools)

> That's outside what I can help with here — I'm the shop assistant for our camera store. If you have questions about cameras, specs, or photography techniques, I'd be happy to help with those! (For the record, though: it's Paris.)
