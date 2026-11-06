# Changing sun direction in architectural images

Full report for MyArchitectAI. Tests run on 6 November 2026.

## Summary

No tested model changed the light cleanly and also kept the scene intact. Each one fails differently, so a model on its own is not ready for a product that promises unchanged geometry and materials.

The closest result is the Sun-Direction LoRA on exteriors: it really moves the sun. Its 4B version has a permissive license, and a color prompt fixed most of its color loss on my RTX 4070. It still changed some materials and added objects. I also tested applying only the model's light to the original photo. That keeps every object, but it leaves old hard shadows in place and adds halos.

My recommendation is a gated exterior-only pilot of the 4B version on a self-hosted serverless GPU. I would not ship interiors yet.

## What is on the market

| Option | Type | One line |
|---|---|---|
| Sun-Direction LoRA (FLUX.2 Klein) | Open LoRA | Trained for sun rotation and elevation on exteriors. Control is a rendered light ball. |
| Qwen-Edit Multi-Angle Lighting | Open LoRA | Eight directions plus above and below, set by text. Author says some angles are uncontrolled. |
| Qwen-Edit Relight and Light Migration | Open LoRA | Relight from text, or copy the lighting of a reference image. |
| FLUX.1 Kontext | Open weights and API | General text editing. Dev weights are non-commercial; Pro is the API route. |
| LTX-2.3 Relight IC-LoRA | Open LoRA, video | Sun direction and hardness for exterior video only. |
| IC-Light | Open model | Older SD 1.5 relighter with conflicting license labels. |
| Nano Banana family | Commercial API | Prompt-based editing, from $0.0336 per 1K image. |
| fal relighting | Commercial API | $0.04 per image. Underlying model not confirmed. |
| Magnific, Krea, Clipdrop | Commercial apps | Subscriptions. No evidence found of architecture-specific relighting. |

Ruled out: LBM Relighting matches a foreground object to a background rather than relighting a scene, and is CC BY-NC. UniRelight is video-only and non-commercial.

## What I tried

Three tools, each on three real photographs from Unsplash: a villa exterior, a concrete apartment block and a living room. The goal was a clearly different sun direction with the same geometry, materials and layout.

| | Sun-Direction LoRA | Qwen 3D Lighting | FLUX.1 Kontext |
|---|---|---|---|
| Sun direction | Changed on exteriors | Partly. Old shadows stay | Not moved on exteriors. Wrong side indoors |
| Geometry | Framing mostly kept | Reframed 16 to 19% on every image | Best on exteriors |
| Materials | Colors shift to gray on every image | Mostly kept. Added flower pots | Sharper texture. Interior turned orange |
| Interior objects | Sofa, table and rug redrawn | Kept, but rug ends left the frame | Kept in place, colors lost |
| Time per image | 20.5 to 26 s | 6.5 to 17 s | 31.5 to 45 s |

Times come from free Hugging Face Spaces and include upload and queue. Cost was $0.

## Measured results

Structure is local correlation with the original after correcting scale and shift, from 0 to 1. Higher means better. Light change is the spatial change in brightness, in EV. Higher means a stronger change.

| Image | Tool | Structure | Scale | Light change |
|---|---|---|---|---|
| Villa | Sun-Direction | 0.33 | 0.97 | 0.37 |
| Villa | Qwen | 0.43 | 0.81 | 0.43 |
| Villa | Kontext | 0.95 | 1.00 | 0.24 |
| Concrete block | Sun-Direction | 0.52 | 1.00 | 0.49 |
| Concrete block | Qwen | 0.60 | 0.84 | 0.41 |
| Concrete block | Kontext | 0.81 | 0.98 | 0.31 |
| Living room | Sun-Direction | 0.40 | 0.99 | 0.40 |
| Living room | Qwen | 0.60 | 0.82 | 0.50 |
| Living room | Kontext | 0.65 | 1.00 | 0.37 |

## How I decided which result is better

I did not rank by a single score. Kontext has the best structure score because it barely moved the light. So each result went through three checks:

1. Did the light really change? Read from the light-change map, then checked by eye against shadow direction.
2. Did the structure survive? Read from local correlation and a difference map.
3. Did individual objects survive? Before and after crops of the sofa, armchair, table and rug.

I added the third check after I spotted a changed sofa color, table and rug that the overall score had missed. The numbers narrow the choice, but the final judgment is visual.

## What went wrong

- **Sun-Direction:** colors fade in the LoRA pass, not the overcast pass as I first assumed. The overcast pass added a tree and wire to the concrete block. Indoors it redrew the sofa and table and shrank the rug. The model was not trained on interiors, so this was expected.
- **Qwen:** reframes every image, even at the Space's own dimensions. It added flower pots on the concrete block. Indoors it put a sun patch on the window wall, which is physically impossible.
- **Kontext:** did not move the shadows on exteriors. Indoors it replaced the outside view and put the sun on the wrong side.
- **Metrics:** the first score fell to near zero on any reframed image, so I added alignment. The score also cannot separate a correct new shadow from an added object. The color check ignores brightness, so a dark armchair turning light gray scores low.

## Local test: the commercially usable 4B version

The Space uses FLUX.2 Klein 9B, which is non-commercial and too large for my 12 GB card. So I ran the Apache-2.0 4B base and its matching LoRA on my own RTX 4070, with and without a color prompt.

| Image | Run | Structure | Light change | Time | What I saw |
|---|---|---|---|---|---|
| Villa | No prompt | 0.29 | 0.30 | 116 s | Pale, as in the 9B run |
| Villa | Color prompt | 0.31 | 0.27 | 81 s | Sun and blue sky look right. Steel sculpture looks like stone, facade turned warmer |
| Concrete block | No prompt | 0.52 | 0.50 | 108 s | Sun moved, concrete faded, clouds added |
| Concrete block | Color prompt | 0.48 | 0.61 | 103 s | Blue sky back, concrete still paler. Tree and clouds added |
| Living room | No prompt | 0.48 | 0.29 | 114 s | View changed, objects redrawn |
| Living room | Color prompt | 0.49 | 0.31 | 89 s | Good sunlight, but rug color changed, armchair lost its green, view changed and an extra ceiling light appeared |

The villa and living room color runs reused a stored overcast pass, so they were faster. All runs used one seed, peak GPU memory was 10.4 GB, and the model was partly offloaded to system RAM, so these times are not production speed.

The color prompt is a cheap and useful fix, but it does not restore the original materials exactly.

## Extra test: transferring only the light

All three models fail by redrawing pixels. So I kept the original photo and took only a filtered brightness ratio from each model's output. The pixels and color come from the original, and the method needs no GPU. Output keeps the original resolution.

| Setting | Structure | Light change | Living room objects (structure) | What I saw |
|---|---|---|---|---|
| Smooth, Sun-Direction | 0.97 to 0.98 | 0.14 to 0.20 | 0.90 to 0.98 | Objects intact. Light barely changes |
| Smooth, Qwen and Kontext | 0.98 to 1.00 | 0.04 to 0.16 | 0.96 to 1.00 | Objects intact. Light barely changes |
| Sharp, Sun-Direction | 0.94 to 0.95 | 0.15 to 0.20 | 0.80 to 0.96 | New light reaches the rug and floor. Halos appear |

- **What worked:** the sofa, table and rug stayed the same, including colors.
- **What failed:** on the concrete block, the old diagonal shadow stayed. A ratio that is smooth or edge-following cannot erase a hard shadow cleanly.
- **New artifacts:** sharper settings add bright halos around objects. Indoors, a ghost ring from the model's wrong table shadow carried over.

So this is a useful guard against redrawn objects, not a finished answer. It may work better for soft changes such as time-of-day color than for moving hard shadows.

## Production recommendation

**Pilot the 4B Sun-Direction LoRA for exteriors only, on a serverless GPU that I run myself, with automatic checks before a user sees a result.** I would not ship interiors from these results.

Pipeline:

1. Run the 4B Sun-Direction LoRA on the exterior image with a color-keeping prompt.
2. Correct any remaining color drift toward the original.
3. Run the structure and alignment checks. Reject and retry a failed result.
4. Upscale for 4K output, then test that step separately.

| Route | Cost per image | Speed | Verdict |
|---|---|---|---|
| Self-hosted serverless RTX 4090 | About $0.01, or $0.02 with one retry | About 20 to 26 s | Recommended pilot |
| Always-on RTX 4090 | About $650 per month | Same, without cold start | Only above about 16,000 images a month, compared with a $0.04 API |
| Kontext Pro API | $0.04 | Not measured | Did not move the sun in the dev version |
| Qwen Edit API | $0.02 to $0.05 | Not measured | Reframes images |

Self-hosted cost uses RunPod's $1.34 per hour and my 9B Space timings as an estimate of GPU time. Neither 4B on that GPU nor cold starts were measured, so both figures need checking on the real hardware.

Three risks need clearing first:

- **Speed:** 20 to 26 s is slower than the 13.4 s average MyArchitectAI publishes for its API. I measured 81 to 116 s on my RTX 4070 with offloading, which is not a production setup.
- **Quality:** the 4B version still changes some materials and adds objects, so the checks in step 3 matter. They are not yet tuned, and the color check misses brightness changes.
- **Color fix:** the prompt helped, but the correction in step 2 is untested.

Before building anything, I would test the 4B version on at least 30 exteriors and measure how often a result passes the checks.

## Sample limits

This is one direction on each of three images, one seed per run. Render inputs were not tested. Results show failure patterns, not reliable rates. Timings come from a shared free queue, not a dedicated GPU.

Photo credits: framesforyourheart, Clay Banks and Valentin Gerardi on Unsplash.

---

# Appendix: problems log

**Tools and access**

| Problem | Effect | What I did |
|---|---|---|
| Two Qwen Relight Spaces were paused or crashing | Could not use the first choice | Switched to Qwen 3D Lighting Control |
| The Multi-Angle Space had a runtime error | Same | Same |
| A second Sun-Direction Space had a runtime error | Only one working mirror | Used the linoyts Space |
| Anonymous ZeroGPU limit stopped runs after three attempts | Six planned runs failed | Logged in with a Hugging Face account |
| Saved Hugging Face token was invalid | Login looked done, but runs still failed | Diagnosed it and logged in again through the browser |
| Sun-Direction reserves 150 s per run | Two color-correction runs failed with 147 s left | Moved the tests to my own RTX 4070 |
| FLUX.2 Klein 9B is too large for a 12 GB card | Could not repeat the Space run locally | Used the 4B version, which is also the license-safe one |
| Local 4B runs need offloading to system RAM | 81 to 116 s per image | Recorded as a local test, not production speed |
| Sun-Direction needs a ball image made in the browser | Could not call the API directly | Recreated the ball scene in Python |
| Openverse rate-limited the image search | Part of the search failed | Used Unsplash instead |
| OpenAI pricing page refused access, BFL prices came back blank | No first-party prices for those two | Left out of cost figures |
| Google pricing page was partly summarized | Figures are less certain | Marked for checking |

**Decisions that changed**

| First position | What changed |
|---|---|
| LBM was a candidate | Dropped. It relights a foreground object, and its license is non-commercial |
| Free API credits were expected | None shown on Google, fal or Replicate |
| A render was one of the three test images | Replaced with a real photo, so renders remain untested |
| The villa was chosen for hard shadows | Its shadows are softer than expected, and it is heavily processed |
| Sun-Direction looked like the clear winner | Changed after the interior object check |
| Gray colors seemed to come from the overcast pass | Saved the overcast image. Color survived that pass, so the LoRA pass is the cause |
| The 9B model seemed to be the one to recommend | Replaced by 4B because 9B is non-commercial |
| Qwen reframing might have come from my size settings | Tested with the Space's own sizes. The result was the same |
| Light transfer might solve everything | Objects were kept, but the sun did not really move on exteriors |
| Smooth light transfer was the first setting | Light barely changed, so I tried a sharper one. It added halos |

**Measurement problems**

| Problem | Fix or status |
|---|---|
| Structure score fell near zero on reframed images | Added scale and shift alignment |
| Kontext scored best while barely changing the light | Score light change separately |
| Score could not separate a correct shadow from an added object | Read the difference map by eye |
| Overall score missed the sofa, table and rug changes | Added per-object crops and measurements |
| Color check ignores brightness, so dark to light gray scores low | Not fixed. Crops are checked by eye |
| Position check gave a table shift of only 1 px while its shape had changed | Use the object structure score and crops |

All attempts, including failures, are kept in `sonuclar/`.
