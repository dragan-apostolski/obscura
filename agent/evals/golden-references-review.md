# Golden-set reference verification

Every ragas-scored reference in `golden.jsonl` was rebuilt **source → reference** (never from
agent answers) and verified claim-by-claim against the corpus by three extraction agents
(2026-07-10), with spot-checks on top. This file pairs each final reference with the verbatim
source text so a human review is a read-through.

Method: extract the relevant guide/manual section → check every draft claim
(supported / not in source / contradicted) → rewrite the reference from source text only.
Page numbers cite the manual's printed page. Page numbers are kept OUT of the reference text
itself: context recall decomposes the reference into claims, and a "(p. 111)" would count as
a claim retrieval can never support.

**Corrections found (what the old, run-log-derived references got wrong):**

| Row | Issue found | Fix |
|---|---|---|
| g02 | "Blinking aperture in Tv mode" claim was Canon-manual material, in no source at hand | Removed; reference now stands on the shutter-speed guide alone |
| g06 | Custom-WB slots "k, l, m" are pypdf glyph artifacts, not real setting names | "one of the three custom white-balance slots" |
| g08 | Setting is named **"Subject to detect"**, not "subject detection" | Corrected; added auto-eye-fallback + detection caveat from p. 402 |
| g10 | Manual says white area only (no gray card); registration = control-wheel center press; message is exactly "Captured the custom WB data." | All corrected |
| g24 | Spec values came from an agent transcript, not from a source I verified | Flagged `reference_verified: false` — verify against catalog/products.json or strip the numbers |

---

## g01 — What is bokeh?
**Source:** `data/technique-bokeh.txt` — all claims SUPPORTED.

**Reference:** Bokeh is the aesthetic quality of the blur produced in the out-of-focus parts of an image (foreground or background), created by using a wide aperture lens; also defined as "the way the lens renders out-of-focus points of light." From Japanese *boke* ("blur"/"haze"). Not limited to highlights — blur occurs in all regions outside the depth of field; restricting the term to bright spots caused by circles of confusion is incorrect. Lens aberrations and aperture shape produce "good" or "bad" bokeh. Opposite: deep focus.

> In photography, bokeh ... is the aesthetic quality of the blur produced in out-of-focus parts of an image, whether foreground or background or both. It is created by using a wide aperture lens. ... Some photographers incorrectly restrict use of the term bokeh to the appearance of bright spots in the out-of-focus area caused by circles of confusion. Bokeh has also been defined as "the way the lens renders out-of-focus points of light". Differences in lens aberrations and aperture shape cause very different bokeh effects. ... ("good" and "bad" bokeh, respectively). ... However, bokeh is not limited to highlights; blur occurs in all regions of an image which are outside the depth of field. The opposite of bokeh—an image in which multiple distances are visible and all are in focus—is deep focus. The term comes from the Japanese word boke (暈け/ボケ), which means "blur" or "haze"

## g02 — When should I use a fast shutter speed?
**Source:** `data/technique-shutter-speed.txt`. Old Canon-Tv-blinking claim REMOVED (not in source). Speed-to-use pairings spot-checked directly (1/8000→birds/planes, 1/4000→athletes/vehicles confirmed in file).

**Reference (final, guide-only):** freeze fast-moving subjects (sporting events); 1/8000 s very fast subjects like birds or planes (good light, ISO 1000+, large aperture); 1/4000 s athletes or vehicles; 1/2000–1/1000 s moderately fast subjects; 1/500–1/250 s people in motion; 1/125 s and slower no longer freeze motion. Also for enlargement/close-up viewing. Handheld rule: shutter speed numerically closest to focal length (1/60 s ↔ 50 mm). Tv (Canon) / S (Nikon+) = shutter priority. Caveat: excessive speed looks unnaturally frozen.

> Very short shutter speeds can be used to freeze fast-moving subjects, for example at sporting events. ... an image intended for significant enlargement and closeup viewing would require faster shutter speeds to avoid obvious blur. ... the slowest shutter speed that can be used easily without much blur due to camera shake is the shutter speed numerically closest to the lens focal length ... 1⁄60 s ... TV (time value on Canon cameras) mode, S mode on Nikons and most other brands. ... Excessively fast shutter speeds can cause a moving subject to appear unnaturally frozen. ... 1⁄8000 s ... Used to take sharp photographs of very fast subjects, such as birds or planes, under good lighting conditions, with an ISO speed of 1,000 or more and a large-aperture lens. 1⁄4000 s ... fast subjects, such as athletes or vehicles ... 1⁄2000 s and 1⁄1000 s: ... moderately fast subjects under normal lighting conditions. 1⁄500 s and 1⁄250 s: ... people in motion ... 1⁄125 s: This speed, and slower ones, are no longer useful for freezing motion.

## g03 — What is the rule of thirds?
**Source:** `data/technique-composition-rule-of-thirds.txt`. The GRID 9 sentence was later REMOVED from the reference (decided 2026-07-10): a general concept reference must not require retrieval from one arbitrary manual — context recall would penalize runs that didn't fetch X100V pages for a question that never asked about the X100V. GRID 9 remains verified (p. 212, excerpt below) if a dedicated cross-source question is ever added.

> The guideline proposes that an image should be imagined as divided into nine equal parts by two equally spaced horizontal lines and two equally spaced vertical lines, and that important compositional elements should be placed along these lines or their intersections. The theory is that aligning a subject with these points creates more tension, energy and interest in the composition than simply centering the subject. ... placing the horizon on the top or bottom line ... line the body up to a vertical line and the person's eyes to a horizontal line. ... The expression "rule of thirds" was first written down by John Thomas Smith in 1797.

> *(X100V manual p. 212)* FRAMING GUIDELINE — Choose a framing grid for shooting mode. ... GRID 9: For "rule of thirds" composition. GRID 24: A six-by-four grid. ...

## g04 — How does aperture affect depth of field?
**Sources:** `data/technique-depth-of-field.txt` + `data/technique-aperture.txt`. Formula **DOF ≈ 2u²Nc/f²** verified exactly. The Canon Av-mode/DOF-preview sentence was later REMOVED from the reference (same rationale as g03 — general concept questions must stay source-general); the Canon claims stay verified below (pp. 115/118) for potential future rows.

> Reducing the aperture diameter (increasing the f-number) increases the DOF because only the light travelling at shallower angles passes through the aperture so only cones of rays with shallower angles reach the image plane. In other words, the circles of confusion are reduced ... DOF ≈ 2u²Nc/f² ... for a given maximum acceptable circle of confusion diameter c, focal length f, f-number N, and distance to subject u. ... changes in proportion to the square of the distance to the subject and inversely in proportion to the square of the focal length.

> *(Canon p. 115)* A higher f/number (smaller aperture hole) will make more of the foreground and background fall within acceptable focus. ... Blurred background (With a low aperture value: f/5.6) / Sharp foreground and background (With a high aperture value: f/32). *(p. 118)* Press the depth-of-field preview button to stop down the lens to the current aperture value setting and check the area in focus.

## g05 — What is ISO?
**Source:** `data/technique-iso-film-speed.txt`. Years/standard number verified character-by-character (ISO 12232: Aug 1998, rev. Apr 2006, corrected Oct 2006, rev. Feb 2019).

> Film speed is the measure of a photographic film's sensitivity to light ... the most recent being the ISO system introduced in 1974. A closely related system, also known as ISO, is used to describe the relationship between exposure and output image lightness in digital cameras. Prior to ISO, the most common systems were ASA in the United States and DIN in Europe. ... The ISO system defines both an arithmetic and a logarithmic scale ... a doubling of film sensitivity is represented by a doubling of the numerical film speed value. In the logarithmic ISO scale ... adding 3° ... constitutes a doubling of sensitivity. For example, a film rated ISO 200/24° is twice as sensitive as one rated ISO 100/21°. ... ISO 12232:2019 (first published in August 1998, revised in April 2006, corrected in October 2006 and again revised in February 2019). ... Higher sensitivities, which require shorter exposures, typically result in reduced image quality due to coarser film grain or increased digital image noise.

## g06 — X100V custom white balance
**Source:** X100V manual p. 111 (PDF p. 131). "k/l/m" glyph artifacts removed from reference.

> Custom White Balance — Choose [one of the three custom slots] to adjust white balance for unusual lighting conditions using a white object as a reference (colored objects can also be used to lend photos a color cast). A white balance target will be displayed; position and size the target so that it is filled by the reference object and press the shutter button all the way down to measure white balance (to select the most recent custom value and exit without measuring white balance, press DISP/BACK, or press MENU/OK to select the most recent value and display the fine-tuning dialog). • If "COMPLETED !" is displayed, press MENU/OK to set white balance to the measured value. • If "UNDER" is displayed, raise exposure compensation and try again. • If "OVER" is displayed, lower exposure compensation and try again.

## g07 — Canon EOS R5 custom white balance
**Source:** Canon guide pp. 188–190. All claims verified, including both cautions and the gray-card note.

> *(p. 188)* 1. Shoot a white object. Aim the camera at a plain white object, so that white fills the screen. Set the lens's focus mode switch to ⟨MF⟩ and shoot to obtain standard exposure for the white object. You can use any of the white balance settings. 2. Select [Custom White Balance]. *(p. 189)* 3. Import the white balance data. ... select the image captured in step 1 ... Select [OK] to import the data. 4. Select [White balance]. 5. Select the custom white balance. ... Caution: If the exposure obtained in step 1 differs greatly from the standard exposure, a correct white balance may not be obtained. The following images cannot be selected: Images captured with the Picture Style set to [Monochrome], multiple-exposure images, cropped images, and images shot with another camera. *(p. 190)* Note — Instead of shooting a white object, you can also shoot a gray card or standard 18% gray reflector.

## g08 — Canon EOS R5 animal eye AF
**Source:** Canon guide pp. 400–402. Setting name corrected: **"Subject to detect"**.

> *(p. 400)* Subject to Detect ... Animals — Detects animals (dogs, cats, or birds) and people and prioritizes detection results for animals as the main subjects to track. For animals, the camera attempts to detect faces or bodies, and AF points are shown over any faces detected. When an animal's face or entire body cannot be detected, the camera may track part of their body. *(p. 401)* Eye Detection — With the AF method set to [Face+Tracking], you can shoot with the eyes of people or animals in focus. 1. Select [Eye detection]. 2. Select [Enable]. *(p. 402)* 3. Aim the camera at the subject. An AF point is displayed around their eye. ... You can also tap the screen to choose an eye. If your selected eye is not detected, an eye to focus on is selected automatically. 4. Take the picture. Caution: Subject eyes may not be detected correctly, depending on the subject and shooting conditions.

## g09 — X100V film simulation modes
**Source:** X100V manual pp. 106 / 142 / 157 (verified in the main session, not by run logs — the one row that was source-first from the start).

> *(p. 106)* FILM SIMULATION — Simulate the effects of different kinds of film, including black-and-white (with or without color filters). ... PROVIA/STANDARD: Ideal for a wide range of subjects. Velvia/VIVID: Vibrant reproduction, ideal for landscape and nature. ASTIA/SOFT: Softer color and contrast for a more subdued look. CLASSIC CHROME: Soft color and enhanced shadow contrast for a calm look. PRO Neg. Hi ... PRO Neg. Std ... CLASSIC Neg. ... ETERNA/CINEMA: Soft color and rich shadow tone suitable for film look movie. *(p. 142)* FILM SIMULATION BKT — Choose the three film simulation types used for film simulation bracketing ... ACROS / MONOCHROME (available with Ye/R/G filters) / SEPIA. *(p. 157)* MOVIE SETTING — F FILM SIMULATION: Choose a film simulation effect for movie recording.

## g10 — Sony a7 IV white balance
**Source:** Sony a7 IV manual pp. 209–214. Corrections: white area only (no gray card in manual); exact message "Captured the custom WB data."; registration via control-wheel center press.

> *(p. 209)* MENU → (Exposure/Color) → [White Balance] → [White Balance] → desired setting. ... Auto / Auto: Ambience / Auto: White / Daylight / Shade / Cloudy / Incandescent / Fluor.: Warm White / Fluor.: Cool White / Fluor.: Day White / Fluor.: Daylight / Flash / Underwater Auto ... C.Temp./Filter: ... Achieves the effect of CC (Color Compensation) filters for photography. Custom 1/Custom 2/Custom 3 ... *(p. 211)* Select from among [Custom 1] to [Custom 3], and then press the right side of the control wheel. Select (custom white balance set), and then press the center of the control wheel. Hold the product so that the white area fully covers the white-balance capture frame, and then press the center of the control wheel. After the shutter sound is heard and the message [Captured the custom WB data.] is displayed, the calibrated values ... are displayed. Press the center of the control wheel. The calibrated values will be registered. *(pp. 212–214)* Priority Set in AWB: Standard / Ambience / White. Shutter AWB Lock: Shutter Half Press / Cont. Shooting / Off. Shockless WB: sets the speed at which the white balance switches during movie recording.

## g11 — Time-lapse movie on the Nikon Z6 II (cross-section)
**Source:** Z6 II manual, printed pp. 340–350 (PDF 384–394). Authored source-first (no prior agent answer existed). Glyph fix: the manual's OK-button icon extracts as the letter "J"; the reference says "the OK button" instead (same artifact class as Fuji k/l/m).

> The camera automatically takes photos at selected intervals to create a time-lapse movie. ... photo shooting menu. [Interval] Choose the interval between shots, in minutes and seconds. [Shooting time] Choose how long the camera will continue to take pictures, in hours and minutes. [Exposure smoothing] Selecting [On] smooths abrupt changes in exposure. [Silent photography] Select [On] to silence the shutter ... [Choose image area] ... from [FX] and [DX]. [Frame size/frame rate] ... [Interval priority] ... [Focus before each shot] ... [Destination] Choose the slot used to record time-lapse movies when two memory cards are inserted. *(p. 342)* To ensure that shooting is not interrupted, use a fully-charged battery, an optional charging AC adapter, or an optional AC adapter and power connector. ... Highlight [Time-lapse movie] in the photo shooting menu. *(p. 343)* Choose an interval longer than the slowest anticipated shutter speed. The maximum shooting time is 7 hours and 59 minutes. *(p. 347)* Highlight [Start] and press [OK]. Shooting starts after about 3 s. The display turns off during shooting. To end shooting before all the photos are taken, press [OK] or select [Time-lapse movie] ... highlight [Off] ... A movie will be created from the frames shot to the point where shooting ended. *(p. 348)* The maximum length for time-lapse movies is 20 minutes. *(p. 349)* Sound is not recorded with time-lapse movies. For consistent coloration, choose a white balance setting other than [Auto] or [Natural light auto].

## g12 — Format a memory card on the Panasonic Lumix S5 II (entity)
**Source:** S5 II manual, p. 573 (+ p. 56). Authored source-first; all cautions included.

> [Setup] menu ([Card/File]) — [Card Format] — [Card Slot 1] / [Card Slot 2]. Formats the card (initialization). Format the cards with the camera before use. • When a card is formatted, all of the data stored in the card is erased and cannot be restored. Save a backup of necessary data before formatting the card. • Do not turn off the camera or perform another operation during formatting. • If the card has been formatted with a PC or other device, format it again with the camera. • You can format the card while keeping the camera settings information stored on the card. ([Save/Restore Camera Setting])

---

**Still open:** g11/g12 (TODO rows — your questions to author), g24 (verify spec values against `catalog/products.json` or strip them), g26 (blocked on the F3 manual-coverage decision), g25 (F4: strict refusal or keep the charm).
