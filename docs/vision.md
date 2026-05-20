# Vision

## What this is
**Central Park Walk** is a walk simulator set in New York City's Central Park. The user walks, looks, and sometimes bikes through a real, faithfully interpreted virtual park. There is no combat, no story, no quest, no objective. Movement and looking are the experience.

## Who it's for
People who want a **software mini-vacation** — a casual, low-stress, beautiful experience. Not gamers seeking challenge. Not researchers seeking measurement-grade accuracy. People seeking calm.

## The experience
- Quiet, contemplative pace.
- The natural environment carries the experience: trees, terrain, water, sky, weather, light.
- Diurnal cycle, seasons, and weather give the world variability without demanding the user's attention.
- Movement (walk and bike) is the only required interaction. Looking is the primary verb.

## Success criteria
**The natural environment of Central Park is accurately interpreted and presented in simulation.**

"Accurately interpreted" means:
- Faithful to source data — OSM, LiDAR, NYC tree census, NYBG / Central Park Conservancy botanical references.
- Recognizable to someone who knows the park. The Ramble feels like the Ramble. The Great Lawn feels like the Great Lawn.
- Visually plausible at the scale of a single tree, a path bend, a stand of woodland, a meadow at golden hour.

We are NOT trying to be:
- Photorealistic in the technical sense. We aim for naturalistic, soft, painterly — data grounded, artistically interpreted.
- A scientific reconstruction. We are an artistic interpretation that respects the data.

## Performance target
**1080p / 60fps on RTX 3060 Ti.** This is the binding constraint for every architectural decision, the budget for every subsystem, and the test for whether a change ships.

Reference point: GTA 5 hits ~100fps on the same 3060 Ti with raytracing off and shadows/reflections at reasonable settings. GTA 5 is a far larger and busier world than a walk-only Central Park. 60fps for our project is achievable without exotic techniques — if we're missing it, the architecture is wrong, not the hardware.

Visual quality lower bound: **GTA 5 with sensible settings would be acceptable.** We hope for better, especially in the natural layer where we have a much narrower subject and can spend our budget densely.

## Distribution
- Free on Steam.
- Donations accepted.
- Open call for community contributions for the man-made layer.
- **MIT licensed.**

## Scope priority
1. **Natural environment first.** Trees, undergrowth, ground cover, vines, terrain, water, sky, weather, light, seasons. This is the substance of the project and the gate to a v1.0 release.
2. **Perimeter skyline buildings restored** — for visual context (the park is framed by Manhattan). Visible but not interactive.
3. **Man-made park elements** — tunnels, bridges, fountains, statues, terraces, the bandshell, detailed park buildings (Tavern on the Green, etc.). Deferred to community contribution after the natural layer ships.
4. **Audio.** Deferred to a later pass.

## Ambient animal life
A small number of animals — birds, squirrels, ducks on water, the occasional turtle — as **ephemeral ambient life**, treated the same way as weather and lighting: procedural, low-input, no relationship with the user, no AI worth the name. They exist to make the place feel alive, not to be a feature. Implementation is deferred until the natural environment is otherwise in shape.

## Anti-scope (what this project will not be)
- No pedestrians, NPCs, dialogue, or quests.
- No combat.
- **No procedural generation of nature itself.** Only ephemera — weather, lighting, audio, ambient animal life — are procedural. Data gaps in the natural layer stay visible rather than being filled with invented content.
- No multiplayer.
- No VR (for now).

## Operating principles that flow from this vision
- **Keep the design simple.** A walk simulator is a small idea. Resist the urge to bolt on complexity. Every subsystem should be the simplest thing that meets the bar, not the most ambitious.
- **Data-first.** Render from data or don't render.
- **Nature-first.** Every decision serves the natural environment first, the framing-context second, everything else not yet.
- **Faithful before flashy.** A correct understated rendering beats an impressive embellishment.
- **The 3060 Ti budget is non-negotiable.** Any subsystem that exceeds its perf budget is broken until it doesn't.
