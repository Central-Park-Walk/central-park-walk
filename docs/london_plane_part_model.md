# London Plane — DEVELOPMENTAL PART MODEL

**Role:** Planner / researcher — *research and UNDERSTAND only.* Nothing built, no code edited, nothing
committed. · Opus 4.8 (1M) · 2026-07-09
**Sibling of:** [`docs/london_plane_growth_architecture.md`](london_plane_growth_architecture.md) (§0.5–§8 =
the algorithmic engine; §10 = the crown-level form model). This doc is the **part level between them.**
**Deliverable of:** "how each part of a London plane DEVELOPS into what it is."

**Authority tags on every claim:** **[PS]** plane-specific & sourced · **[BG]** broadleaf/tree-general &
sourced · **[IMG]** my own read of specimen imagery (direction only, never a number) · **[?]** assumption or
unresolved. Sources marked **(read in full)** were downloaded and read; **(abstract only)** means I saw the
abstract/secondary quotation and nothing more. Working notes: `tmp/partmodel/`.

---

## 0. What this changes, in five lines

1. **The naive part ladder is wrong in kind, not just in detail.** Botany does not decompose a tree into
   trunk/primary/secondary/twig. It uses two *orthogonal* ladders: nested **construction units** (metamer →
   growth unit → sympodial module → annual shoot → axis → …) and a small, finite set of **axis categories**
   set by **physiological age** — and the categories "**may or may not be superposed to the notion of
   branching order**" **[BG — Barthélémy & Caraglio 2007]**.
2. **★ And *Platanus* is the literature's own worked example of that mismatch.** B&C's Figure 18 is captioned
   "*Category of axis vs. branching order*," and the case where the two are **not** superposed, in a sympodial
   pattern, is "***Platanus* sp.; Caraglio and Edelin, 1990**" **[PS — primary, verified in the PDF]**. Plane
   has **no true terminal bud**; every axis is a sympodial chain of annual relay modules, so under strict
   ordering the trunk's order would increment every year. Our `hierarchy_depth` counts exactly this quantity.
3. **The number of part-types is itself an output of age**, not a constant. It is *the* early ontogenic marker
   for plane **[PS — Genoyer, Atger, Édelin & Caraglio 1999]**.
4. **Chris's primary-limb life history is right about the engine and wrong about one clause.** Thickening
   under leaf load ✔, bending under accumulating self-weight ✔, "a frozen record of its own growth" ✔ (and it
   is literally visible as occluded scars). But **shade-escape did not turn the limb horizontal** — a
   gravitropic set-point angle plus self-weight did — and **gaps between secondaries never stretched**,
   because a woody stem cannot elongate mid-axis. They were *shed*.
5. **The three layers converge on the age axis and conflict in four places**, all four of which explain a
   defect the project has already measured and mis-attributed (wiry limbs, straight twigs, the imposed clear
   bole, arcy limbs). §6.

---

## 1. Prior art first (Rule 2), in order

**Our own docs, read before anything else.** `london_plane_growth_architecture.md` §0.5 (Runions et al. 2007;
Palubicki et al. 2009), §1 (connection grammar), §2 (three-buckets-are-one-process), §3–§5 (the growth
proposal + reuse ledger), §8 (leaves-as-attractors recovery), §9 (the lollipop provenance), §10 (the crown
form model and its named gaps). §10 is the direct parent of this task: it grounded the **crown**, worked from
whole-crown imagery and horticultural prose, and explicitly recorded that it had *no part-level evidence.*
This doc is that missing level. `docs/standing_rules.md` Rule 2 applies throughout.

**Primary sources newly read for this task (none of their vocabulary existed anywhere in `docs/` before — I
checked):**

| source | status | what it gave |
|---|---|---|
| **Barthélémy, D. & Caraglio, Y. (2007). "Plant architecture: a dynamic, multilevel and comprehensive approach to plant form, structure and ontogeny." *Annals of Botany* 99(3): 375–407.** **OPEN ACCESS** — PMID [17218346](https://pubmed.ncbi.nlm.nih.gov/17218346/), [PMC2802949](https://pmc.ncbi.nlm.nih.gov/articles/PMC2802949/) · [PDF](https://amapstudio.cirad.fr/_media/soft/xplo/private/private/barthelemy_caraglio_2007_ann_bot.pdf) | ★ **text read in full** (`tmp/partmodel/bc2007.txt`) **AND figures 9, 18, 23, 26, 27, 30 rendered and read as images** (`tmp/partmodel/figs/`, 2026-07-09) | The formal decomposition; axis categories; physiological age; morphogenetic gradients; **reiteration + the pauperization gradient + the M.A.U.**; mixed axes. **The backbone of §2, §3 and §4.7.** The figures carry spatial mechanism the captions only gesture at — the 2026-07-08 pass read captions only, and that is why §4.7 was wrongly filed as blocked. |
| **Caraglio, Y. & Édelin, C. (1990). "Architecture et dynamique de croissance du platane, *Platanus hybrida* Brot."** *Bull. Soc. Bot. France, Lettres Bot.* 137(4–5): 279–291. | citation confirmed (Crossref); **body NOT read** (403) | Massart's model; "monopodial organization despite sympodial functioning"; crown metamorphosis; ties plane's pollard tolerance to its sympodial character. |
| **★ Genoyer, P., Atger, C., Edelin, C. & Caraglio, Y. (1999). "Some architectural markers of plane tree development (*Platanus × acerifolia* (Aiton) Willd.): contribution to the establishment of an ontogenic based diagnosis."** *Acta Horticulturae* **496**: 209–220. **DOI [10.17660/ActaHortic.1999.496.26](https://doi.org/10.17660/ActaHortic.1999.496.26)** · [Agritrop record](https://agritrop.cirad.fr/391940/) (French title/résumé) | **abstract read verbatim; full text unavailable** | The plane-specific part-level ontogeny. See §2.3-F3 and §7. |
| **Palubicki et al. 2009**, *Self-organizing tree models for image synthesis* (SIGGRAPH) | read in full | Borchert–Honda λ; shadow propagation; the Takenaka shed rule; **pipe-model memory**. |
| **Runions, Lane & Prusinkiewicz 2007**, *Modeling trees with a space colonization algorithm* | read in full | `D`/`di`/`dk`; branch-size hierarchy from progressively-added attractors; pipeline steps (d) decimation, (e) relocation, (f) subdivision. |
| **Meier, Saunders & Michler 2012**, "Epicormic buds in trees," *Tree Physiology* 32(5):565–584 | read in full | Epicormic trace kept at the surface by radial extension; bud-fate strategies; release by loss of apical control + light. *(Platanus not in their species tables — applied by analogy.)* |
| **Kothari et al. 2025**, "Self-pruning in tree crowns…," *Functional Ecology* 39:2238–2252 | read in full | Self-pruning light threshold `Lbase` as a functional trait; correlative inhibition as a documented violation of branch autonomy. |
| **Eloy 2011**, *Phys. Rev. Lett.* 107:258101 | read in full | Leonardo's rule from constant wind-fracture risk; Δ ∈ 1.8–2.3 empirically; sapwood may be **5%** of a mature section. |
| Coutand et al. 2007 (*Plant Physiol.*, poplar gravitropism); Moulia & Fournier 2009; Fournier et al. 2013 | read in full | Reaction-wood righting, maturation strains, autotropic decurving, "**the thicker the stem, the less it is liable to curve**". |
| **Barthélémy, Édelin & Hallé 1989**, "Architectural concepts for tropical trees" | read in full | **Architectural metamorphosis** — branches "*from plagiotropic and poorly branched at the beginning… become more and more orthotropic*". |
| **Cline & Harrington 2007**, *Can. J. For. Res.* 37:74–83 | read in full | The crisp **apical dominance ≠ apical control** distinction (Table 1). |
| FNA Platanaceae; USDA Silvics *P. occidentalis*; FEIS; VT Dendrology | read | No terminal bud; petiole-enclosed bud; zig-zag twig; bark-by-diameter; forest bole clear to 20–25 m. |
| Sprugel, Hinckley & Schaap 1991 (branch autonomy); Takenaka 1994; Alméras & Fournier 2009; Wilson 2000; Lehnebach et al. 2018; Ishii et al. 2007; Digby & Firn 1995 | **abstract / secondary quotation only** | Used only for claims that a read-in-full source also carries. Flagged inline. |

---

## 2. The part taxonomy — refined against the botany

### 2.1 What we currently call parts
Chris's starting list — **trunk/bole · primary (scaffold) limb · secondary branch/ramification · twig · sprig
(leaf-bearing tip)** — is a **caliber-rank ladder**: parts named by how thick they are and how far down the
branching hierarchy they sit. It is a perfectly good *rendering* taxonomy. It is not how the tree is built,
and the mismatch is the reason a grower keeps needing hand-placement.

### 2.2 What the architecture literature actually uses — two orthogonal ladders

**Ladder A — construction units (nested, ontogenetic).** Barthélémy & Caraglio 2007, read in full:

- **Metamer (phytomer)** — "*the entity formed by a node, associated with its leaf (or leaves) and axillary
  bud(s) plus the subtending internode, represents the basic structural unit of the plant body*". This is the
  atom. Everything else is a way of grouping metamers.
- **Growth unit (GU)** — "*the portion of an axis which develops during an uninterrupted period of
  extension*" (Hallé & Martin 1968). Delimited on the stem by "*a zone of short internodes and/or cataphylls*".
- **Sympodial unit / module** — "*the portion of an axis edified by a single terminal meristem*". **This is
  the unit *Platanus* actually stacks** (§2.3-F1).
- **Annual shoot (AS)** — "*The set of growth units produced in one year*". One GU = monocyclic; several =
  polycyclic.
- **Axis** — a rectilinear succession of modules. In a **sympodial** plant the axis is *not* one meristem's
  product; B&C therefore define an "**apparent branching order**" for it (see F1 below).
- **Branching system → architectural unit → reiterated complex → tree.**

**Ladder B — axis categories (finite, small, set by physiological age).** This is the one that matters and the
one we do not have. B&C, verbatim:

> "*the number of categories of axes is finite … and generally small (no more than five or six)*… This
> indicates that the architecture of a fully established branched system, whatever its complexity, can be
> summarized in terms of a **very simple sequence of axes**… each branch is the expression of a particular
> state of meristematic activity."

and, decisively:

> "*the categories of axes **may or may not be superposed to the notion of branching order***."

A category is defined by a *syndrome* — orientation (orthotropic / plagiotropic / **mixed**), symmetry,
phyllotaxis, GU length, branching, whether it flowers, lifespan — not by depth in a tree of pointers.

**What assigns an axis to a category: the physiological age of the meristem that made it.** B&C define three
distinct ages, and this is the crux the whole task turns on:

> "(1) the **calendar or chronological age**… (2) the **ontogenetical age** refers to the elapsed time after
> seed germination… (3) the **physiological age of a meristem** relates to the **degree of differentiation of
> the structures it produced**… it may **not be an intrinsic property of this meristem itself** but the result
> of **all morphogenetic interactions between plant parts**."

And the sentence that answers "why is a low primary different from a high primary?":

> "*the exact structure of a lateral axis depends on its **topological and ontogenetic position on the parent
> axis***."

### 2.3 Where the formal decomposition DIFFERS from ours — four findings

**F1 — For *Platanus*, branch order is degenerate, and we are counting it.**
Plane has **no true terminal bud**; the apex aborts and the uppermost axillary bud relays the axis each year
**[PS — FNA lists only "*Axillary buds: each hidden by swollen base of petiole*"; VT Dendrology, *P.
occidentalis*: "*terminal bud is absent*"; and for the London plane: "*Moderate zig-zag pattern*"]**. Caraglio
& Édelin describe plane as "*very strong monopodial organization despite sympodial functioning*," built by
"*the linear succession of annual modules*," monopodial for one or two years and **sympodial for the rest of
its life** *(abstract only)*. B&C say what that does to ordering:

> "*In a sympodial system, a rigorous use of this terminology will lead to the reference of the successive
> sympodial units as axis orders 1, 2, 3, etc.*"

i.e. a 100-year-old plane trunk is a **branching order ~100 axis** under strict ordering. B&C's repair is the
"**apparent branching order**" — treat the rectilinear succession of relay modules as one axis. **Our
`hierarchy_depth` attribute and the leaf-back "hop count" are branching-order-like counters.** They are
therefore measuring something the botany explicitly says is not the part identity. (This is *not* a bug in the
skinner contract — `strand` already does the right thing: a strand IS an apparent-branching-order axis. It is
a warning against ever gating part-type on depth.)

**F2 — ★ Axis category ≠ branching order, and *Platanus* is the literature's own example of it.**
B&C Figure 18, caption verbatim (verified in the PDF):

> "**Category of axis vs. branching order.** The relative arrangement of categories of axes (T, trunk;
> B, branch; S, short shoot) **may** (A, i.e. *Araucaria araucana*) or **may not** (B and C) be superposed to
> the notion of branching order, in either monopodial (B, i.e. *Acer* sp.) or **sympodial (C, i.e. *Platanus*
> sp.; Caraglio and Edelin, 1990)** branching pattern."

So this is not an inference we are drawing from general theory and applying to plane — **plane is the worked
counter-example**, cited to the plane monograph itself. A first-order lateral low on a veteran and a
first-order lateral high on a sapling are the *same order* and *different parts*; a reiterate's leader is a
high-order axis that behaves like a trunk. **Any rule of the form "depth == 2 → it's a secondary" is unsound
by construction, for this species, in print.**

**★ Reading panel C directly (2026-07-09) — three plane-specific facts the caption does not state:**
1. **Plane's axes are labelled `AO`, not `BO`.** Panels A and B use branching order (`T/BO1`, `B/BO2`); **panel
   C, *Platanus*, uses *apparent* branching order throughout** (`T/AO1`, `B/AO2`, `S/AO2`, `S/AO3`). B&C cannot
   use strict order for plane. This is F1, drawn.
2. **`x` (apical mortality) is marked at essentially every axis tip in panel C** — trunk apex included. The
   no-terminal-bud relay (E1) is not an incidental twig character; it is the tree's universal axis termination.
3. **★ Plane's architectural unit contains at least three axis categories: trunk (T), branch (B), and SHORT
   SHOOT (S)** — and **`B/AO2` and `S/AO2` sit at the *same* apparent order.** Two different part-types, same
   depth. Our taxonomy (§2.4) had no short-shoot category; it is now sourced, plane-specific, and primary. The
   short shoot is the physiologically-oldest axis category (short GUs, flowers, short-lived — §4.2).

**F2b — An axis can CHANGE category.** Differentiation is not one-way: "*differentiation of an axis may **not
be an irreversible process**, and according to modifications of internal or external conditions or after
architectural traumatism, **reversion of axis differentiation is very often possible**… indicating that shoot
differentiation and bud fate are controlled by a **whole plant network of correlations**.*" **[BG — B&C, read
in full]** The named macro-form of this is **architectural metamorphosis** (Édelin 1984): branches "*from
plagiotropic and poorly branched at the beginning… become more and more orthotropic*" **[BG — Barthélémy,
Édelin & Hallé 1989, read in full]**, and Caraglio & Édelin report the plane's crown as "built by reiteration
**preceded by a true architectural metamorphosis**" **[PS, abstract only]**. **A plane's primary limb is
therefore literally a different category of object at 60 years than at 6** — it re-erects. This is the formal
name for the trajectory Chris described.

**F3 — ★ The number of part-types GROWS with the tree.** B&C: a tree "*expresses step by step its
architectural unit*," category by category. Genoyer et al. 1999 make this the plane's own ontogenic marker —
verbatim from the résumé:

> "*Les principaux indicateurs morphologiques de l'état de développement d'un platane au cours des premières
> phases de l'ontogenèse sont **le nombre de catégories de tiges du houppier** et **la structure des branches
> latérales**.*"
> ("The principal morphological indicators of a plane's developmental state during the early phases of
> ontogeny are **the number of stem categories in the crown** and **the structure of the lateral branches**.")

and for the rest of the tree's life the markers are those of **its primary limbs** (`branches maîtresses`):

> "*architecture (et particulièrement **ordre de réitération totale**), **orientation**, **direction de
> croissance**, ordre de ramification des réitérats totaux sommitaux et **morphologie des unités de
> croissance**.*"

That is a published, plane-specific statement that a plane's developmental state is **read off its primary
limbs**, through exactly the variables this task asks about. It is the single most on-point source found, and
we cannot read its body (§7).

### 2.4 The working taxonomy for CPW (proposed; mapping, not renaming)

Keep our names for rendering. Bind each to the botanical entity that *generates* it, and note what code already
holds it.

> ⚠ **REVISED 2026-07-09.** This section used to read: *"Plane's architectural unit, per B&C Fig. 18C, contains
> at least **T (trunk) · B (branch) · S (short shoot)**."* **B&C Fig. 18C is a teaching diagram** illustrating
> that category ≠ branching order — it is not a specification of plane's AU, and reading it as one was a
> second-hand use of a figure drawn for another purpose.

**Plane's architectural unit has FIVE axis categories, indexed by apparent order** — Caraglio & Édelin 1990,
Planche 2, *"Caractéristiques des différents ordres de ramification"*, read from the paper's own table:

| | **A1** (tronc) | **A2** | **A3** | **A4** | **A5** |
|---|---|---|---|---|---|
| orientation | **orthotropic** | plagiotropic | plagiotropic | plagiotropic | plagiotropic |
| module length | *(blank in the source)* | ~15 nodes | ~10 nodes | 7 nodes | 5 nodes |
| phyllotaxis | alternate spiral **2/5** | distichous base → spiro-distichous/spiral distally | distichous base → distichous/spiro-distichous distally | **distichous** | **distichous** |
| sexuality | — | — | — | **terminal** | **terminal** |
| self-pruning | **never** | long term | medium term | **1–6 yr** | **1–4 yr** |

*"c'est sa structure élémentaire, fonctionnelle, son 'unité architecturale'"* — **attained in the first six years.**
The old carve maps in as `T = A1`, `B = {A2, A3, A4}`, `S = A5`. **`B` splitting three ways is the point:** the
reiterate's truncation rungs are `c.r.p. A3` and `c.r.p. A4` (§4.7), which a 3-rung AU cannot even name.
⚠ **A4 also bears terminal sexuality**, so "the category that flowers" is A4 **and** A5, not S alone.

| our part | botanical entity | what MAKES it | already in code as |
|---|---|---|---|
| **sprig** (leaf-bearing tip) | **annual shoot** (1+ growth units) on a physiologically-old axis | one season's extension of a distal bud; leaves + fruit-balls | leaf-card placements (currently re-derived from bark verts — §8 of the growth doc) |
| **★ short shoot (S)** | **the physiologically-OLDEST axis category** — short GUs, flowers, short-lived | drift + high physiological age; **`B/AO2` and `S/AO2` coexist at the same order** (Fig. 18C) | **absent as a category** |
| **twig** | **axis of high physiological age** — short GUs, ramifies little, short-lived, sheds | a bud low on the vigour gradient; dies when its light/size ratio drops | `radius` below the twig floor |
| **secondary** | **axis of intermediate physiological age**, borne acrotonically on a primary | a lateral of a relay module that stayed lit | `strand` + `hierarchy_depth` |
| **primary limb** | **`branche maîtresse`** — a **reiterated complex** in the mature crown, not a mere lateral | early lateral that survived, thickened, then **re-erected and reiterated the architectural unit**, truncated by its insertion position | scaffold `origin_ids`, `strand` |
| **trunk / bole** | **axis 1 (T/AO1)** — a sympodial chain of annual modules; its *clear* length is an **output of shedding** | relay + apical control; bole cleared by self-pruning | `trunk_ids`, `spine_top` |
| **★ reiterated complex** | *the missing 6th part* — a **pauperized copy of the architectural unit**, truncation set by insertion (base → periphery); fired **automatically** at a differentiation threshold | §4.7 — **now a specified mechanism** | **absent** |
| *(pollard knuckle)* | epicormic complex + wound-wood | repeated cutting | out of CP scope (§1.6 of growth doc) |

**Verdict on the taxonomy question:** Chris's five parts survive as *render categories* and map cleanly onto
axis categories. Two corrections: (i) **"primary limb" is a reiterated complex, not a big secondary** — a
category difference, not a size difference; (ii) **a sixth part is missing** (the reiterate), and its absence
is exactly what §10.2 diagnosed at the crown level as the missing "several trees fused" massing.

---

## 3. The causal engine — six forces, and one master rule for position

Every per-part life history in §4 is these six, evaluated at a position.

- **E1 — Relay (sympodial modular extension).** No terminal bud → each year the apex aborts and the topmost
  axillary bud takes over, departing at roughly the bud's insertion angle. **Every axis is a chain of annual
  modules with an angular discontinuity at each year-boundary node.** **[PS]** This is the *only* source of
  crookedness that does not require damage. Lateral buds sit ~45° off the twig *(dendrology snippet; the ~45°
  is not a measurement I can stand behind — see §7)*.
- **E2 — Apical control and its decay.** ⚠ Two mechanisms our docs have been conflating under "apical
  dominance." Cline & Harrington 2007, Table 1, verbatim **[BG, read in full]**:
  – **Apical dominance** = "*Control exerted by an actively growing shoot apex over the **outgrowth of lateral
  buds***" — short-range, about *whether a bud grows out at all*.
  – **Apical control** = "*Growth suppression of an existing **subdominant branch** by a higher dominating
  shoot… concerned with the regulation of growth **after** budbreak and, thus, is **one step removed from
  apical dominance***" — long-range, about *how big, how fast, at what angle* an existing limb grows.
  **The excurrent→decurrent story is apical CONTROL, not dominance.** Formalised as the Borchert–Honda **λ**:
  `vm = v·λQm/(λQm+(1−λ)Ql)`, `vl = v·(1−λ)Ql/(λQm+(1−λ)Ql)`; "*λ > 0.5*" biases the main axis → excurrent,
  "*λ < 0.5*" → decurrent **[BG — Palubicki 2009, read in full]**. Decaying λ over developmental time *is* the
  young→old form progression (their Fig. 11). **Correlative inhibition** modulates it: a well-lit top raises
  the shed threshold of the branches below **[BG — Kothari 2025, read in full]**.
- **E3 — Light + branch autonomy → shedding.** A branch lives on its own carbon; the tree does not subsidise a
  shaded one *(Sprugel et al. 1991, via Kothari 2025's verbatim citation)*. Operational rule, verbatim from
  Palubicki: "*The total amount of light gathered by a branch is compared with the branch size measured in the
  number of internodes. If this ratio falls below a specified threshold, the branch is considered a liability
  for the tree and is shed.*" And: "*it is the key to the formation of tall boles.*" **[BG]**
- **E4 — Pipe model with MEMORY (the diameter ratchet).** `dⁿ = d₁ⁿ + d₂ⁿ`, n ≈ 2–3. And — the clause our
  generator does not implement — verbatim from Palubicki: "*Importantly, branch width is **not decreased** when
  leaves and branches are shed or pruned. **The model thus requires a memory of past leaves and branches.***"
  Physiologically exact: wood is never resorbed; disused pipes become heartwood (sapwood may be "*as low as 5%
  in mature trees*", Eloy 2011). **Diameter is a monotonic ratchet on the *maximum historical* load.** **[BG]**
- **E5 — Posture: gravitropic set-point angle vs self-weight.** A branch does **not** simply sag. It has a
  **GSA** it defends, actively, via **tension wood** on the upper side (angiosperms), through **maturation
  strains** laid down in each new ring **[BG — Coutand et al. 2007, read in full; Digby & Firn 1995, abstract]**.
  Two facts make the *long-run* outcome descent anyway:
  (a) Alméras & Fournier 2009 *(abstract)*: with real tree slenderness and stiffness, radial growth alone does
  not keep up — "*without gravitropic correction the mechanical design of trees would ultimately lead to a
  weeping habit.*"
  (b) Coutand et al. 2007 *(read in full)*: "*the thicker the stem, the less it is liable to curve*" — the
  **per-year righting capacity falls as the limb fattens**, while the self-weight moment keeps climbing
  (tip deflection ∝ L⁴ for distributed load).
  → **Posture is a lifelong balance that the limb slowly loses.** Chris's word "struggle" is precisely right.
  **★ E5 couples back into E2, and this is where Chris's light intuition is half-vindicated.** Wilson 2000
  *(abstract only)*: when the shoots above a lateral are removed, "*the lateral branch can grow larger and may
  **bend upwards***," via "*production of wood cells that can generate an **upward** bending moment*." So the
  competitive/dominance state of what is *above* a limb genuinely does move that limb — but **upward, on
  release, by reaction wood**, not outward-and-downward by shade-flight. The sign is opposite to the brief's.
- **E6 — Reiteration.** A released, well-lit bud can re-express the *whole architectural unit* — "*a new tree
  upon the old tree*" — rather than produce an ordinary lateral. **Adaptive** (resource/space increase) vs
  **traumatic** (damage) **[BG — B&C 2007, read in full]**. In large old trees "*delayed reiteration occurs
  without an obvious external stimulus*" *(Ishii et al. 2007, abstract)*. B&C: reiteration "*reproduces the
  morphogenetic gradients of the non-reiterated parent plant*" — a reiterate is a *scaled copy of the whole
  gradient set*, which is why a veteran's primary limb looks like a small tree. **[PS via Caraglio & Édelin:
  "the crown of the plane is built by a reiteration phenomenon preceded by a true architectural metamorphosis."]**

### The master rule for position-dependence
> "*the exact structure of a lateral axis depends on its topological and ontogenetic position on the parent
> axis.*" **[BG — B&C 2007]**

### ★ The gradients are DISTINCT — and the old grower conflated them (Fig. 30, read directly)
Figure 30 is a single diagram that separates, on one axis, the gradients we had been treating as one "low limbs
are different" effect. Reading it:

| gradient | where it acts | what it governs | our conflation |
|---|---|---|---|
| **'Base effect' = establishment phase** | the **bottom** of any axis grown from seed | the first laterals are **few and small**; vigour *rises* acropetally out of the establishment zone | we attributed the bare/weak proximal limb zone **entirely to shedding**. Wrong: it was **weakly branched from birth** as well. |
| **Acrotony** | **within** each annual shoot / growth unit | *where along that year's extension* the vigorous laterals sit (distally), with an increasing acropetal vigour gradient | we had no within-GU rule at all; laterals were emitted uniformly |
| **Drift** | **along an axis, with its ageing** | the ontogenetic decline of successive annual shoots (GU length ↓, leaf size ↓, short shoots ↑) | absent |
| **Sequential reiteration** | at a **differentiation threshold** | duplication of the *whole gradient set* by a new axis (Fig. 30 draws it as a lateral that **curves and re-erects**) | absent — this is the missing 6th part |
| *(branching order)* | whole plant | "*the higher the branching order of an axis, the higher its degree of differentiation*" — but **superimposed and weak**, and for plane it is `AO` not `BO` (§2.3-F1) | **this is the ONLY one the grower models**, via `hierarchy_depth` — and it is the weakest of the five |
| **Epitony / hypotony / amphitony** | on a **slanted** parent | which *side* gets the laterals | absent; unknown for plane (§7) |

**Three distinct causes of "the proximal end of an old limb is bare," and we had one.** *(i)* base effect —
it branched weakly there to begin with; *(ii)* **shedding** (E3) — what it did bear was later dropped; *(iii)*
**pauperization** (§4.7) — if the limb is a reiterate, *how much of the unit it expresses at all* is set by its
insertion. These are separate mechanisms with separate parameters. Collapsing them into one hand-tuned
"low = thick, bare" heuristic is precisely how the grower ended up hand-placing parts.

**And for *Platanus* the gradients are maximal, not marginal.** B&C: gradient expression "*is at a **minimum**
for a monocaulous continuously growing plant … whereas it will be at a **maximum** in a polycyclic, branched
and reiterated, **rhythmically and sympodially growing plant***." Plane is **branched, reiterated, rhythmic and
sympodial** — four of the five. **[BG]**

> ⚠ **Correction 2026-07-09.** This sentence used to read *"Plane is every one of those."* **It is not
> polycyclic.** C&E: *"Deux années après la germination … un axe orthotrope (A1) comprenant **deux** unités de
> croissance"* — two GUs after two years is **one per year** — and terminal buds abort *"**chaque année** en
> octobre-novembre."* **Plane is monocyclic.** The overclaim came from reading B&C's general sentence as a
> checklist and ticking the box; nothing in B&C says plane is polycyclic. The conclusion (gradients are maximal
> for this species) survives on the other four; the fifth was invented. *(A first-pass note on C&E made the
> mirror-image error, reading "two u.c. two years after germination" as evidence **for** polycyclism.)*

Full gradient list, all from B&C (read in full): **base effect** · **drift** · **branching order** ·
**acrotony / mesotony / basitony** · **epitony / hypotony / amphitony** · and **reiteration**, which duplicates
the whole gradient set at a new origin.

**This is the answer to the brief's crux.** The same part-type differs by position because the *meristem that
made it had a different physiological age*, and physiological age is set by position in the gradient field —
not by a rule that says "low limbs are thick."

---

## 4. Per-part LIFE HISTORIES

Format per part: **origin → development over time → position-dependent trajectory → driving optimization.**

### 4.1 The metamer and its bud (the atom)
**Origin.** The apical meristem lays down node + leaf + axillary bud + internode **[BG]**. In *Platanus* the
bud forms **inside the swollen hollow petiole base** and is exposed only at leaf fall; the sheathing stipule
leaves a **ring scar encircling the twig** **[PS — FNA, read: "*Axillary buds: each hidden by swollen base of
petiole… stipules… sheathing stem*"]**.
**Development.** Three fates: (i) extend next spring as a **proleptic (delayed) lateral** — ★ **confirmed
primary and plane-specific (2026-07-09): B&C Figure 9 uses *Platanus* itself as the exemplar of *delayed
branching***, opposite *Juglans regia* (immediate branching, long first internode = "hypopodium"). Caption
verbatim: "*Delayed branching refers to a system where lateral branching follows a resting phase of the lateral
meristem during which it is frequently included in a bud. When elongated, such delayed branching lateral shoots
frequently show a **short first internode and proximal scale leaves or bud scale scars** when abscissed
(**Platanus sp., B**).*" The photo shows a plane twig with the **scar of the abscissed prophyll α (`αs`)** at
the lateral base. **So a plane branch base carries a diagnostic short first internode + prophyll scars** — and
the "sylleptic unconfirmed" gap is now answered on the default: plane branches **proleptically**. *(It does not
positively exclude occasional syllepsis; that remains unstated.)* **[PS]**; (ii) relay the axis, if it is the
topmost survivor when the apex aborts (E1); (iii) **stay dormant and be carried outward at the bark surface**
as the stem thickens — Meier et al.
2012, read in full: "*Radial extension of the trace at the rate of overall diameter growth of the tree enables
the meristem to be maintained in its position on or in the bark*." **[IMG — this is what the small conical
bosses on smooth plane limbs are; sheet 3 of `tmp/partmodel/`, and the bole bosses in `W_197477320`.]**
**Position.** The bud's fate is set by its rank in the acrotonic gradient and its light.
**Optimization.** A bank of cheap, indefinitely-preserved options. The dormant bud is the tree's call option on
future light — the substrate for E6 and for the entire pollard response.
**Generate-ready:** yes, as a rule. Phyllotaxis is **alternate, spiral** **[PS — FNA]**, and ✅ **the 2/5
divergence IS confirmed for *Platanus*** (C&E 1990, twice: *"La phyllotaxie est alterne spiralée **d'indice
2/5**"* on the plantule, and the trunk module's *"partie distale à phyllotaxie spiralée **d'indice 2/5**"*).
**Hard-code it — for orthotropic axes only.** ★ **Phyllotaxis is the readout of the axis's orientation, not an
independent trait:** orthotropic ⇒ spiral 2/5; plagiotropic ⇒ **distichous**; an axis *changing* category passes
through **spiro-distichous** (C&E's transition zone, where A2s *"présentent une phyllotaxie spiro-distique puis
distique, parallèlement la direction de croissance est de plus en plus horizontale"*). So a grower should derive
phyllotaxis **from the posture state variable**, never set it per part — Rule 3, one more time.

### 4.2 The annual shoot / growth unit — our "sprig"
**Origin.** One season's extension of a bud. Terminated not by a resting terminal bud but by **apex abortion**.
**Development.** The GU records the vigour of the meristem that made it: "*short axes … growth units are short,
bear flowers and have a short lifetime … may be considered **physiologically old** whatever their moment of
appearance*", vs "*main axes consisting of vigorous growth units … are **physiologically young** products and
generally appear only in the young tree*" **[BG — B&C, read in full]**. Genoyer et al. name "**morphologie des
unités de croissance**" as a lifelong ontogenic marker for plane **[PS]**.
**Position.** A GU on the leader of a sapling is long, thick, many-metamered, and branches acrotonically. A GU
on a shaded inner twig of a veteran is a few short internodes, may flower, and dies. **Same organ, opposite
ends of the physiological-age scale.**
**Optimization.** Exploration (long GUs) vs exploitation (short GUs) — B&C's long/short axis dichotomy: "*long
and short axes, respectively specialized in environmental exploration and exploitation*".
**✅ RESOLVED 2026-07-09 — Caraglio & Édelin 1990, read in full (text + all five plates).** Both halves of the
old gap close, and **one of them closes against a claim this document previously made.**

**(i) Rhythm — rhythmic, MONOCYCLIC. A growth unit is a year.** *"Les branches sont ramifiées de façon
**rythmique** jusqu'à l'ordre apparent A5"*; the trunk is *"la succession linéaire de modules orthotropes,
**longs chacun d'une seule unité de croissance**"*; and *"les bourgeons terminaux de **tous les axes avortent
chaque année en octobre-novembre**."* One abortion per axis per year ⇒ one growth unit per year. Massart's
requirement is met, and C&E assign plane to **Massart's model** explicitly (Planche 5) — a claim this project
previously carried only via a secondary source.

**(ii) ⚠ Syllepsis — plane makes BOTH, and this document's "plane branches proleptically" was too strong.**
C&E's Planche 1 (English caption: *"i. : **sylleptic branch**; r : **proleptic branch**"*) draws both on one
juvenile axis. But the modes are **not co-equal — they are separated in developmental time**, and that is what
matters for a grower:

| | where | fate |
|---|---|---|
| **sylleptic** (`développement immédiat`) | the seedling's A1; the **median part of the 2nd growth unit** of the young plant | those on the **1st** GU *"se sont élagués durant le premier hiver"* — gone, only scars; those on the 2nd GU *"ne s'élaguent pas rapidement"* |
| **proleptic** (`développement différé/retardé`) | **everywhere in the established architecture** | the trunk module *"porte des rameaux à développement **retardé** à l'aisselle de toutes les feuilles de la zone spiralée"*; master-branch modules are *"ramifié[s] de façon **différée**"* |

**⇒ Syllepsis is confined to years 0–2. From the architectural unit onward, plane branches proleptically.**
B&C Fig. 9 (plane as the exemplar of *delayed* branching) was **right about the mature tree and wrong as an
absolute**, and this document repeated the absolute. Corrected. *Practical impact on CPW is small — the s/m/l
tiers are all past the juvenile phase — but the claim was overstated and is now bounded.*

### 4.3 The twig
**Origin.** A lateral of low rank in the acrotonic gradient, or a distal relay.
**Development.** Ramifies weakly; **is the part that gets shed** — E3 acts here first and constantly. Twigs are
**zig-zag by construction**, one kink per annual relay (E1) **[PS — "obviously zigzag" for *P. occidentalis*;
"moderate zig-zag" for London plane, VT]**.
**Position (the axis of variation).** *Sunlit outer twig:* long GUs, keeps ramifying, becomes a secondary.
*Shaded inner twig:* light-gathered/size falls under threshold → **abscised**. The threshold itself is a
species trait, and — the subtlety — it is **raised when the top of the tree is well lit** (correlative
inhibition) **[BG — Kothari 2025, read in full]**. So a vigorous plane prunes its interior *harder*.
**Optimization.** A twig is kept only while it pays its own respiration (branch autonomy). This is the entire
reason crowns are shells and interiors are open.

### 4.4 The secondary branch
**Origin.** A twig that stayed lit long enough to thicken.
**Development.** Accretes along the parent **only at the parent's advancing tip** — because *a woody stem
cannot elongate mid-axis*; internode length is fixed at primary growth **[BG — basic anatomy; verified]**.
So a limb's secondaries are laid down **distally, in order, one cohort per year**, and never move afterwards.
**Position — two superimposed gradients, and both matter.**
- *Within* each annual increment: **acrotony** — "*the prevalent development of lateral axes in the distal part
  of a parent axis or shoot*". **Epitony / hypotony** then decide which *side* of a slanted parent gets them —
  on a near-horizontal veteran limb this is what decides whether sub-limbs rise from the top or hang below.
  *(I could not find which applies to plane — §7.)*
- *Across* years, along the limb: **base effect → drift.** B&C: these gradients "*take into account the
  respective ontogenetic increase or decrease in several parameters along the main stem of any plant, **or even
  along lateral axes of branched plants***." Empirically (their Fig. 32, *Pinus pinaster*), successive annual
  shoots along one branch first *increase* then *decrease* in length, % branched, and % reproductive.
  → **A limb's first years branch weakly (establishment), its middle years branch most vigorously, its late
  distal years shorten and flower.** ⚠ **Correction to my own §4.5 draft:** the bare proximal zone of an old
  limb therefore has **two** causes, not one — *(i)* it was **weakly branched from the start** (base effect),
  and *(ii)* what it did bear was later **shed** (E3). The occluded scars **[IMG]** prove *(ii)* happened; they
  do not prove it was the only cause, and the literature says it was not.
**Optimization.** Fill the newly-vacated light in front of the advancing parent tip.

### 4.5 ★ The primary limb (`branche maîtresse`) — the crux
This is the part Chris characterised, and the one Genoyer et al. say carries the plane's whole developmental
signal. I verify his account clause by clause.

**Origin.** Not "a big secondary." In the young tree it is an ordinary plagiotropic lateral in a rhythmic tier
(Massart). In the mature tree it becomes a **reiterated complex**: apical control decays, the lateral is
released, and it **re-expresses the whole architectural unit** — its own leader, its own tiers, its own
gradients **[PS — Caraglio & Édelin: "crown built by a reiteration phenomenon preceded by a true architectural
metamorphosis"; BG — B&C: reiteration "reproduces the morphogenetic gradients of the non-reiterated parent"]**.
**[IMG — `W_11670158`: 4–6 heavy limbs, each reading as its own small tree. This is what §10.2 called "several
trees fused."]**

**Development over time — the mechanical story, corrected.**

| Chris's clause | verdict | the mechanism |
|---|---|---|
| "the thick horizontal veteran limb IS the thin upward young primary, aged" | ✔ **in trajectory**, ✘ **in identity** | The *position* persists; the *axis* does not. It is a **sympodial relay chain**, later a reiterate — not one persistent apex that grew old. This distinction is what produces the crook (E1) instead of a smooth arc. |
| "it thickened under its growing leaf load (pipe model over time)" | ✔ **correct** | And stronger than stated: diameter is a **ratchet** (E4). It never shrinks when the load is shed. Empirical branching exponent Δ ∈ **1.8–2.3** [Eloy 2011, read in full]; real broadleaf branches fit a **uniform-stress / self-weight** model better than a wind model in sheltered conditions [PLOS One 2014, *Fagus*]. Our `PIPE_POWER = 2.3` sits at the top of the empirical range. |
| "it went horizontal-then-below because it grew OUT to escape the shade of younger branches above it" | ✘ **NOT SUPPORTED — the one wrong clause** | Horizontality is a **gravitropic set-point angle** (lower limbs are constitutively plagiotropic), plus self-weight sag (E5). Overhead shade does **not** redirect a limb outward — it **kills** it (E3, branch autonomy). The defensible residue: a limb *extends and thickens where its own foliage stays lit*, which is why **open-grown** trees keep long low limbs at all. Light **gates which limbs survive**; it does not steer them. Rephrase: *"it extended laterally because light remained at the crown edge,"* not *"it fled the shade above."* |
| "it bent under its own accumulating weight in that struggle" | ✔ **correct, and this is the engine** | And the reason the struggle is *lost*: self-weight moment rises with L⁴ while **per-year righting capacity falls with radius** ("*the thicker the stem, the less it is liable to curve*"). Without correction the design "*would ultimately lead to a weeping habit.*" |
| "its secondaries started near the trunk and spread as the limb extended… accreting new secondaries at its growing tip while old ones stayed put" | ✔ **correct** | Primary growth is apical only. New cohorts are added distally; old ones never move. |
| "…and gaps stretched — the spacing is a FOSSIL RECORD of the growth" | ✘ **mechanism wrong** / ✔ **conclusion right, and stronger** | **Gaps never stretched.** A woody stem cannot elongate mid-axis; spacing is written once, at primary growth, and is thereafter frozen. The bare proximal zone has **two** causes: the proximal years **branched weakly to begin with** (B&C's *base effect*), and what they bore was later **shed** (E3) — the bole-clearing process, running *inside* one limb. The spacing *is* a fossil record — of annual-shoot lengths and of **which laterals survived** — and it is **literally legible**: **[IMG — `obs11623132_3.jpg` shows a heavy limb carrying a spaced series of occluded stub sockets along its bare zone, with one surviving lateral.]** |
| "the low primary and the high primary are the SAME part at two points in a life trajectory" | ✔✔ **correct, and it has a formal name** | **Architectural metamorphosis** (§2.3-F2b): the limb *reverts and re-differentiates*, plagiotropic → orthotropic, and then reiterates. Not a metaphor — a documented category change. |

**The resulting shape, derived rather than authored.** Proximal: stout, near its set angle, righting → rises.
Distal: thin, longest lever arm, carrying the accumulated tip mass → arches down. The limb is the integral of
that gradient: **ascend, then arch.** **[IMG — and a third term the literature predicts and the imagery shows:
`veteran_jarny.jpg` and `W_11670158` both show the *distal tips turning back UP*.]** Two candidate causes,
**not resolved**: (a) the outermost segments are young, thin and lightly loaded, so active righting still wins
there; (b) B&C's **"mixed axis"** — "*a proximal plagiotropic portion followed by a distal orthotropic end*" —
is a recognised botanical axis type. Flagged **[?]**.

**Position-dependent trajectory (the crux, and it is visible in a single tree).**
**[IMG — `veteran_jarny.jpg`]:** *low limb* = long, near-horizontal, **bare proximal pipe**, ramifies only
distally, tip upturned. *high limb* = short, steep, ramifies close to its origin, little bare zone.
The causes, in order of contribution:
1. **Ontogenetic position (E2/E6).** The low limb was emitted when the tree was young and apical control was
   strong (a suppressed plagiotropic tier branch); it has since had the most years to thicken, shed, and
   **reiterate**. The high limb was emitted late, under weak apical control, and is still a simple lateral.
   *Its physiological age is different because its parent's ontogenetic stage was different when it formed.*
2. **Mechanical age (E4/E5).** The low limb has integrated the most self-weight, has the fattest section, and
   therefore the least remaining righting authority → it has descended furthest.
3. **Light history (E3).** The low limb's *interior* has been shaded longest → its proximal laterals are gone,
   leaving the bare pipe. Its *periphery* stayed lit (open-grown) → it kept extending.
4. **Its own internal gradients.** Because the limb is a reiterate, it carries a *copy* of the whole gradient
   set — its own base effect, its own drift, its own acrotony — which is why it reads as a small tree.

**Driving optimization.** Maximise intercepted light per unit of structural + hydraulic investment, under
self-weight, with an irreversible diameter ratchet and a bud bank as the option set. Every geometric feature
above is a consequence: taper (material minimum for a given fracture risk, Eloy), the bare pipe (shed what
doesn't pay), the arch (posture lost slowly), the crook (relay is cheaper than maintaining one apex), the
reiterate (rebuild the whole unit where light reappears).

### 4.6 The trunk / bole
**Origin.** Axis 1 from the seed; thereafter a **chain of annual relay modules** — "*monopodial organization
despite sympodial functioning*" **[PS]**.
**Development.** Extends, thickens by ratchet, and — the load-bearing point — **its clear length is an OUTPUT
of shedding, not a parameter**: "*shedding … is the key to the formation of tall boles*" **[BG — Palubicki,
read in full]**. Empirically for the genus: "*Under forest conditions the tree has a relatively small crown and
a long, slightly tapered bole that may be clear of branches for 20 or 25 m*"; "*Open-grown sycamores have a
large irregular crown that may spread to 30 m*" **[PS — USDA Silvics, read]**. Same species, same age, two
boles — the **light axis** §2 of the growth doc flagged as unrepresented.
**Bark, as a part-level cue.** FNA, read, verbatim: "*Bark smooth at first, exfoliating in thin plates,
exposing conspicuous mosaic of chalky white to buff or greenish new bark, **becoming dark, thick, and fissured
with age**.*" FEIS: base of large trunks "*deeply furrowed and up to 3 inches thick*"; upper trunk exfoliates.
**So bark type is a function of local diameter / surface age, not of part name** **[IMG — exactly what
`W_11648420` (dark plated bole, cream limbs) and `W_197477320` (young tree, smooth nearly to the ground) show;
the plate bark *climbs* the bole with age].** A generator gets this **free** from `radius`, which the skinner
already carries.
**Position/Optimization.** The bole is what remains when everything that didn't pay for itself was dropped.

### 4.7 ★★ The reiterated complex — UPGRADED 2026-07-09: now a GENERATE-READY MECHANISM
> **Status change.** This part was previously "not yet generate-ready, blocked on the paywalled Genoyer et al.
> 1999." That was **wrong about the blocker.** The general mechanism is fully specified in Barthélémy &
> Caraglio 2007, which is **open access** (PMC2802949, PMID 17218346). The earlier pass read its *text* and its
> *captions* but never opened its **figures**. Figures 23, 26, 27 and 30 have now been rendered from the PDF and
> read directly (`tmp/partmodel/figs/`), and they carry the spatial mechanism the captions only gesture at.

**Origin — and it is NOT primarily opportunistic.** Two distinct routes, and the one that builds the crown is
the *programmed* one:
- **Opportunistic reiteration** — adaptive (resource increase) or traumatic (damage), from a released dormant
  bud. This is the one our docs had.
- **★ "Automatic" (Édelin 1984) / "sequential" (Nicolini 1997) reiteration** — "*the same process of repetition
  may be involved in the **inherent growth pattern of a species** and occur **automatically** during plant
  development **after a definite threshold of differentiation***" (Fig. 26). B&C are explicit that it is
  **endogenous, not a regression**: "*sequential reiteration must **not** be interpreted as a move backwards
  within the developmental sequence of the original organism, but rather as **part of this sequence***," and it
  "*proved to be a very common and major morphogenetic process underlying **crown construction in most forest
  trees**.*" **[BG — read in full]**

**This is the finding that makes the part designable.** The mature crown's reiterates are **scheduled by a
differentiation threshold**, not waited-for as random damage events. A grower can *fire* them from the same age
parameter that decays apical control. No stochastic trauma model is required.

**★ And C&E names the threshold's substrate, for plane: it is RELAY DOMINANCE, and a FORK IS A REITERATION.**
B&C leaves "threshold of differentiation" abstract. The plane monograph does not:

> *"L'arbre n'est monopodial qu'en apparence et ce caractère est lié à l'existence d'un **seul relais dominant à
> chaque unité de croissance**."* … *"il y a une **diminution progressive de la dominance** des relais
> subterminaux. Ce phénomène se traduit par la présence de **fourche sur les branches** (complexes réitérés
> partiels), puis à l'**extrémité du tronc** (complexes réitérés totaux)."*

Dominance rises (*"l'acrotonie augmente"*), then falls; when it collapses the module's one dominant relay is
replaced by **2–3 co-equal relays**, and each co-equal relay **is** a reiterated complex. The trunk does not
sprout its master branches sideways — *"le tronc en tant que structure unique **s'est arrêté**"* — it **forks and
ends**. Each fork element then *"présente d'abord une forte acrotonie et une grande dominance … il y a ensuite
diminution … ce qui aboutit à une **nouvelle vague de réitération**,"* with dominance *"[diminuant] pour devenir
**nul**"* at the crown periphery. **The wave series is a recursion on one state variable, and it terminates by
itself.** This replaces "a scalar φ crossing Φ" as the firing rule (design §2).

**Development — the governing law is the PAUPERIZATION GRADIENT (Fig. 23).** Verbatim:

> "*They all duplicate the original sequence of differentiation of the original individual **but the duplication
> is smaller and more 'pauperized' according to their insertion from the base of the trunk to the 'periphery' of
> the crown**. At the top of the tree and in the most peripheral part of the crown, pauperization of the
> duplication is the highest and reiterated complexes all have a reduced and minimal specific structure … named
> '**Minimal Architectural Unit**' (M.A.U.) by Barthélémy (1988).*"

**Reading the diagram (not just the caption):** Fig 23A (*Araucaria*) labels a **complete reiteration (C.R.)
low on the trunk** and a **partial reiteration (P.R.) higher up**. Figs 23B/C draw reiterates in black along the
parent trunk: near the base each is a **full miniature of the whole tree** (own trunk, several tiers); they
shrink and simplify upward; at the apex/periphery the arrow marks **M.A.U.** — in *Symphonia*, "*a small trunk
bearing only **one** flowering tier of plagiotropic branches.*"

So the gradient is a **monotonic, positionally-indexed truncation of the architectural unit** — and for plane,
**C&E names the rungs itself**, so the table below is transcribed rather than interpolated:

| insertion position | reiterate expresses | C&E's own label | reads as |
|---|---|---|---|
| base of trunk / low on a master branch | the **complete** unit, A1→A5 | **`c.r.t.`** (*complexe réitéré total*) | a whole small tree |
| out along an A2 | A3, A4, A5 | **`c.r.p. A3`** (Planche 4, Fig. 5) | a branched sprout with flowering tips |
| further out | A4, A5 | **`c.r.p. A4`** (Planche 4, Fig. 5) | a small flowering spray |
| top / crown periphery | A5 alone | the **Minimal Architectural Unit** | a flowering short shoot |

*"[Les petits rejets] sont des systèmes ramifiés possédant **la même structure que des axes A3 et A4
séquentiels**."* — **a partial reiterate is literally an axis of order `s`, grown where an axis of order `s` does
not belong.** The truncation index is a **starting rung**, not a size scalar.

> ⚠⚠ **The positional law does NOT govern every reiterate, and C&E is why.** The **first** total reiterates form
> *"à l'**extrémité du tronc**"* — at the trunk's apex, the most *peripheral* point there is — which the
> positional law alone would predict to be an M.A.U. There is no contradiction, because there are **two birth
> modes**: a **terminal fork** reproduces *the forking axis's own rung* (A1 forks ⇒ total reiterates ⇒ the master
> branches), while a **latent bud on old wood** is truncated by *its insertion position*. B&C's Fig. 23 gradient
> indexes the second. **Applying it to the first would put M.A.U.s on top of the trunk and build no crown at all.**
> Specified in `grower_reiterate_design.md` §3.3 and escalated as fork **F7**.

**★ This is the direct, published answer to the brief's crux.** "How does the same part-type differ by position
— low vs high, inner vs outer?" A low primary and a high primary are **the same object (a reiterate) truncated
at different depths of the architectural unit**, indexed by insertion position. It is not a size scalar; it is
*how much of the species' developmental sequence the copy gets to express.*

**The origin geometry is drawn, too.** In Fig. 30 the reiterate is drawn as an axis that **leaves the parent
stem, curves, and re-erects into a new vertical axis** bearing its own gradients. Fig. 26D draws the same thing
with arrows: the **lower branches turn up** and become the reiterates that build the mature crown. That curve is
**architectural metamorphosis (secondary orthotropy, §2.3-F2b) and reiteration as one motion** — and it is
geometrically the ascend-then-re-erect profile the veteran imagery shows **[IMG — `veteran_jarny.jpg`]**.

**The developmental sequence (Fig. 26, *Fraxinus excelsior*).** Four stages, read off the diagram:
**A** seedling, leader + few laterals · **B** the **architectural unit fully expressed** once (conical, tiered) ·
**C** the unit **duplicated automatically** · **D** mature crown = "*a complex mature crown made of a
**succession of reiterated complexes***," rounded, with the lower branches re-erected. **This mechanizes §10's
ovoid → rounded → spread series**: the crown broadens and rounds because it is accumulating reiterates of
increasing order, each pauperized by its insertion.

**The within-sequence trend set (Fig. 27) — directions, from the diagrams.** As physiological age advances
(*Artocarpus*, main-axis leaves; *Fagus sylvatica*, panel B, left→right by developmental stage):
- **growth-unit length ↓** (the black "latest G.U." shortens),
- **branching complexity / branching grade ↑**,
- **short shoots appear and multiply**,
- **leaf size ↓ and leaf form simplifies** (large, deeply-lobed juvenile leaves → small, entire mature leaves),
- **stem and leaf anatomy shift**, and **crown outline goes conical → domed**.

**★ A free rendering consequence we were not exploiting.** Leaf size/form is a function of the **physiological
age of the bearing axis**, not of the species. FNA independently records this for plane: leaves "to **30 × 40
cm** on **sucker shoots**" versus 6–20 cm typical **[PS]**. Our leaf cards are one size for the whole tree.
Cards on vigorous/young/reiterate-leader axes should be **larger and more deeply lobed**; cards on old short
shoots **smaller and simpler**. The skinner already carries the per-node attributes needed to drive this.

**Position / optimization.** Rejuvenation — reduce respiration/photosynthesis ratio, shorten the hydraulic path
to new foliage, reset the meristem *(Ishii et al. 2007, abstract only)*. And B&C's own scope note, which is a
gift for plane: morphogenetic-gradient expression "*is at a **minimum** for a monocaulous continuously growing
plant … whereas it will be at a **maximum** in a **polycyclic, branched and reiterated, rhythmically and
sympodially growing plant***." **Platanus is sympodial, branched, rhythmic and reiterated — the maximum-gradient
case.** For this species the gradients are not a refinement; they are the form.

**⚠ Corroboration from the traumatised case — and a warning about our imagery.** Genoyer et al. 1999 is *about
traumatised trees* (pruned / crown-reduced) and reports that after injury a plane's crown sub-units "*se
développent de façon apparemment indépendante les unes des autres*." Two consequences: (i) reiterates behave
**autonomously**, which is branch autonomy (E3) at the limb-system scale, in plane, in print; (ii) **their
architecture diverges from the reference ontogenic sequence** — so see §5's hardened rule on pruning imagery.

### 4.8 The epicormic complex and the pollard knuckle (mechanism only; out of CP scope)
Not to be modelled for Central Park (growth doc §1.6, unchanged). But it is the **same mechanism seen bare**,
and it is why the cut-limb imagery is admissible evidence for *natural* form:
- Caraglio & Édelin attribute plane's "*extraordinary response to cultural practices*" **to its sympodial
  character** *(abstract only)*. Pollarding removes an apex; a lateral/epicormic bud relays. **That is E1, on a
  schedule.** The knuckle is accreted wound-wood plus a released epicormic cluster **[IMG — `cut_sprouting.jpg`]**.
- Therefore a pollarded limb shows the *natural* relay geometry with the amplitude turned up, and a hard-pruned
  limb shows the *natural* caliber hierarchy stripped of foliage **[IMG — `cut_pruned_hard.jpg`: primaries leave
  the bole over a range of heights; secondaries at intervals along each; a **strong caliber step at every
  fork**; **limbs near-straight between nodes with the direction change AT the node**]**.
- ⚠ **Do not import the pollard's amplitude.** A CP plane is not cut. Use these frames for *topology and
  caliber*, never for sinuosity magnitude.

---

## 5. Grounding — what is evidence, and what each kind can and cannot say

**Literature** (table in §1). The causal mechanisms E1–E6 are all **sourced, most from papers read in full**.
Note where they are *not* plane-specific: E2–E6 are **[BG]**, verified for broadleaves generally; only E1, the
bark rule, the Massart assignment, the reiteration-built crown, and the pollard link are **[PS]**.

**Cut-limb / pruning imagery — the brief's hypothesis, tested.** The brief predicted cut plane limbs would be
abundant and would show limb geometry as *objects*. Confirmed: hard-pruned and pollarded planes are common on
Wikimedia Commons, and `cut_pruned_hard.jpg` does exactly what was hoped — it isolates the caliber hierarchy,
the along-limb secondary spacing, the wide insertion angles, and the **angular-at-nodes** crook character.

**⚠ HARDENED RULE for pruning imagery (2026-07-09).** Genoyer et al. 1999 is *a study of traumatised planes*,
and its finding is that a traumatised tree's development "*suit, peu après le traumatisme, des modalités
originales par rapport à la séquence ontogénique de référence*" — **it departs from the reference ontogenic
sequence**, and soon after injury the crown's sub-units develop apparently independently of one another. So:

| what a pruned/pollarded plane photo IS evidence for | what it is NOT evidence for |
|---|---|
| **limb GEOMETRY** — taper, caliber step at forks, insertion angle, along-limb secondary spacing, angular-at-node crooks, bark-by-diameter | **developmental SEQUENCE** — reiterate order, which axis category is where, how the crown assembled, GU-length trends, pauperization gradient |
| the *mechanism* of relay (apex removed → lateral takes over), seen bare | the *amplitude* of natural sinuosity, or the natural number/placement of reiterates |

A pollard is a tree whose ontogenic sequence has been overwritten. Use these frames for **shape**, never for
**history**. (This tightens the earlier, vaguer "don't import the pollard's amplitude" note in §4.8.)

**★ The reframe that unlocked our own collection.** §10 triaged the 311-observation iNat pull for **whole-crown
outlines** and discarded ~90% as "ID close-ups (bark / leaf / fruit / from-below)." For a **part-level** model
that triage **inverts**: those close-ups *are* the part data. Reading them (contact sheets, then full-res) gave
the five regularities below. **The crown-outline gap of §10.5 is untouched and stays open** — this reframe buys
nothing at the crown level.

Full frame-by-frame reads: `tmp/partmodel/imagery_notes.md`. Summary of what the imagery **supports (direction
only, never a number)**:
1. **Bark type tracks local diameter**, not part name.
2. **Crooks are angular and sited at nodes**; limbs are near-straight between them.
3. **Proximal limb length is bare; ramification is distal**; the bare zone is longer on lower/older limbs.
4. **Old limbs carry a spaced series of occluded lateral scars** in the bare zone — the fossil record, visible.
5. **Low limb ≠ high limb in the same crown at the same instant** (long/horizontal/bare/distally-ramified/tip-up
   vs short/steep/ramified-at-origin).

**What the imagery cannot give, and I have not invented:** fork angle, taper exponent, secondary spacing,
bare-zone fraction, per-relay kink angle — *as numbers*. Every frame is single-angle and uncalibrated. Fitting
a number to a thin anchor is what produced the lollipop (§9 of the growth doc).

---

## 6. The three-layer convergence check

**Layer 1 = the algorithmic engine** (growth doc §0.5–§8: space colonization, pipe model, apical dominance).
**Layer 2 = this part model.** **Layer 3 = the crown form model** (growth doc §10).

### Where all three AGREE (strong grounding — treat as settled)
- **The age axis.** Engine: decaying λ / apical control animates excurrent → decurrent (Palubicki Fig. 11).
  Part: E2 decay releases laterals, which reiterate (E6). Crown: §10's ovoid → rounded → spread, "*crown
  metamorphosis*". **Three independent literatures, one mechanism.** The "three buckets = one growth process"
  reframe is now grounded at all three levels.
- **The crown must be filled as a volume.** Engine: Runions Fig. 7 (shell-only → hollow lantern). Part: leaves
  are borne on annual shoots throughout the reiterates' interiors. Crown: §10's "aggregation of reiterated
  units," not a smooth shell. Agree.
- **Taper is derived, never imposed.** Engine: pipe model. Part: E4. Crown: §10's caliber gradient. Agree —
  **with one correction, below (C2).**
- **The clear bole is made by shedding.** Engine: Palubicki §4.4. Part: E3. Crown: §10's `cb_frac` falling with
  age. Agree — **with one correction (C4).**
- **Light is a second axis, orthogonal to age.** All three say so; none of the three has it implemented.

### Where they CONFLICT — seven real findings; five of them explain a defect we already measured

**C1 — ★ The engine grows monopodially and continuously; *Platanus* grows sympodially and modularly.**
Space colonization advances a node by a fixed step `D` toward the attractor average. There is no year
boundary, no apex abortion, no relay. **The engine has no event at which a crook can be born.** Consequences,
matched to defects already in the record:
- the "*fine outer-twig layer still dense + straight → reads busy*" residual (topology-redesign Stage 2);
- the smooth garden-hose leader (growth doc §0.2 — attributed there to the *unforked* leader, which is true and
  separate; **straightness of the ramified twigs has a different cause, and this is it**);
- every attempted cosmetic fix (curvature noise, θ_min spacing, "elbow" metrics) is treating the symptom.
**The correct primitive is the annual module, not the step `D`.** A relay kink at each module boundary produces
zig-zag twigs, sinuous limbs, and the plane's whole crooked identity, *for free and from the botany*.
⚠ Honest caveat: the **magnitude** of the per-relay angle is a named gap (§7). The *existence* of the mechanism
is **[PS]** and certain; the number is not.

**C2 — ★ The engine's radius is a function of the FINAL graph; reality is a ratchet over HISTORY.**
`_finish` computes `radius[i] = (Σ r_child^p)^(1/p)` from the children that exist at the end. The engine sheds
nothing, so it never has to remember anything. **A bare thick proximal limb is therefore unreachable**: a limb
with no proximal children tapers *down* toward twig radius. This is, mechanically, the iter-1 Critic finding
that "**limbs read thin/wire**" — and it is why AC-14 (primary-limb caliber) had to be added as an *acceptance
criterion* and then satisfied by a **hand-weighted partition** (`target tips ∝ w^(p/2)`, "da Vinci area-above").
That partition is a **fake of the ratchet.** The real mechanism is: *grow many laterals → shed most of them →
keep the diameter they earned.* Diameter should be `max` over history, not `f(current children)`.
**This is the single most consequential conflict, because it converts a tuned heuristic into a derived one.**

**C3 — ★ `N_PRIMARIES = 4` scaffolds off one spine is not reiteration, and cannot become it.**
The engine places 4 scaffold origins at `linspace` heights × golden-angle azimuths. A reiterate is a *fresh
expression of the architectural unit* — its own leader, its own tiers, its own gradients — whose degree of
dedifferentiation depends on *where and when* it arose (B&C, quoted in §4.7). **§10's mature crown ("an
aggregation of several heavy crooked twisting ascending limbs… 'several trees fused'") cannot be produced by
the current scaffold model at any parameter setting**, because the scaffolds are laterals, not sub-trees. Layer 2
and Layer 3 agree with each other and both conflict with Layer 1. This is a **structural** gap, not tuning.

> **★ Update 2026-07-09 — C3 now has its fix specified (§4.7).** The reiterate mechanism converts C3 from "a
> named structural hole" into "a designable replacement": a scaffold origin becomes a **reiterate origin** that
> (a) fires at a differentiation threshold rather than being placed at a `linspace` height, (b) **curves away
> and re-erects** instead of shooting straight to the shell, (c) **re-runs the whole grower on itself**,
> truncated by the pauperization gradient at its insertion. `N_PRIMARIES` stops being a constant and becomes an
> *output* of the firing schedule — the same "output, not parameter" correction as `cb_frac` (C4) and the
> already-retired depth cap. **What the reiterate mechanism constrains in the other conflicts:**
> - **C2 (pipe-model ratchet):** a reiterate is a *sub-tree*, so its base legitimately carries the summed load
>   of everything it ever bore. The ratchet and the reiterate are the same claim seen from two ends — a bare
>   thick proximal limb is a reiterate's **own bole**, cleared by its **own** shedding (E3).
> - **C1 (annual modules):** the reiterate inherits the relay, so its axes crook exactly as the parent's do. The
>   module boundary is where a reiterate can *also* fire. One primitive serves both.
> - **C5 (set-point angle):** the "curve away and re-erect" origin geometry **is** a posture problem — a
>   plagiotropic lateral acquiring an orthotropic set-point. C5 is not optional decoration; it is the mechanism
>   by which a reiterate is born.
> These four were listed as independent defects. They are one missing abstraction.

**C4 — The engine imposes `cb_frac` as an envelope input; the botany makes clear bole an OUTPUT.**
The bole is what survives shedding. Imposing it is the same class of error the project already diagnosed and
retired once — *"depth is an OUTPUT not a parameter"* (crown-mould memory, 2026-07-06). **`cb_frac` is the next
instance of that lesson**, and the woodland/open-grown split (growth doc §2) is exactly the experiment that
would prove it: same grower, different light field, different bole. *(Flagged, not costed. The engine has no
light model at all — Runions' `Q` is binary, which Palubicki explicitly warns "*would cause branches to be shed
immediately after they stop growing*.")*

**C5 — Posture is entirely absent.** `tropism` is a parameter and it is `0`. There is no set-point angle, no
self-weight deflection, no righting. The "arcy frontal views" and "uniform 60° emergence" residuals from the
trunk-scaffold prototype are this hole. E5 gives the derivation: shape = set-point arc + self-weight deflection
along a tapered axis, with the tip still righting.

**C6 — A conflict with the brief itself, not with the code.** The brief's premise that the primary limb "*went
horizontal-then-below because it grew OUT to escape the shade of younger branches that came in above it*" is
**not supported** by the biomechanics literature (§4.5). Recorded here because the brief explicitly invited the
correction. Everything else in the brief's sketch survives, and the "fossil record" intuition is *more* right
than it claimed. (Partial vindication: release from apical control *does* move a limb — **upward**, by reaction
wood (Wilson 2000). The competitive state above a limb matters; the sign is opposite.)

**C7 — ★ A conflict BETWEEN the two literatures, which our engine has silently resolved in one direction.**
The **modelling** school makes light the *driver*: buds sense a shadow field, resource follows light, branches
that fail a light/size ratio are shed (Palubicki, Takenaka). The **architecture** school makes light a
*modulator* of an endogenous programme. B&C, verbatim, on environmental factors:

> "*they **almost never** (except probably in extreme conditions) **modify the inherent morphogenetic and
> ontogenetic constructional rules** of plant organization.*"

Both are read-in-full primary sources and they are not saying the same thing. Neither is obviously wrong: the
architecture school studies *which axis categories exist and in what order they appear* (endogenous, stable);
the modelling school studies *how many branches survive where* (environmental). **They are answering different
questions, and a grower needs both** — an endogenous ontogenic sequence that *generates part types in order*,
with a light/mechanics layer that *prunes and poses* the parts that sequence emits. Our engine has only the
second. It predicts that a purely light-driven grower will produce a plausible *population* of branches with the
wrong *identities* — exactly the "equal-stick pom-pom" and "wire armature" symptomology in the record.

> ### ✅ C7 RESOLVED 2026-07-09 — and the resolution was in the exception clause all along.
>
> C7 was filed as *"a real, unresolved tension and I am not resolving it here."* **The architecture school's own
> plane monograph resolves it,** and the synthesis did not need inventing. Re-read B&C with the emphasis where
> they put it: environment *"**almost never** (**except probably in extreme conditions**) modify the inherent
> morphogenetic and ontogenetic constructional rules."* Now C&E, on plane:
>
> - *"Cela va même parfois jusqu'à la formation de **fourches orthotropes (milieu très ensoleillé)** conférant à
>   la plante un aspect arbustif, voire buissonnant (**en conditions très drastiques**)."*
> - *"le moindre traumatisme, **un haut niveau d'énergie lumineuse** ou un stress hydrique peuvent **redonner …
>   une équivalence aux différents modules émanant d'une même u.c.**, favorisant tout processus réitératif."*
>
> **The two clauses meet exactly: "except probably in extreme conditions" ≡ "en conditions très drastiques."**
> The environment gets a **parametric handle on relay dominance `D`** inside an otherwise endogenous programme.
> It does not rewrite the AU — the rungs A1…A5 and their production rules are untouched — it changes **how often
> an axis forks**, and therefore how many limbs there are and when.
>
> **So light acts at three separated places, and steering is not one of them:** (i) it modulates `D` (topology);
> (ii) it gates survival (shedding); (iii) it fills space at twig scale. This is the both-schools grower C7 said
> was needed. Consequence, and it is a real prediction: **the woodland/open-grown split needs two mechanisms** —
> shedding sets the *bole length*, `D`-modulation sets the *fork count and timing* — and neither produces the
> other's effect. Recorded as an **amendment to ratified fork F1** in `grower_reiterate_design.md` §7.5.

---

## 7. THE HONESTY GATE — is each part generate-ready?

"Generate-ready" = *a grower could emit this part from a mechanism, rather than place it.* Naming a gap is the
success condition; a fabricated mechanism is the failure condition.

> **Table revised 2026-07-09 after C&E 1990 was read in full.** Four rows change verdict.

| part | mechanism understood? | generate-ready? | the named gap | how it closes |
|---|---|---|---|---|
| **metamer / bud** | **YES** (E1; petiole-enclosed bud, stipule ring, dormant-bud trace) | **YES** | ✅ **2/5 phyllotaxis CONFIRMED** (C&E, ×2) — and it is a *readout of orthotropy*, not a free trait (§4.1). Bud insertion angle (~45°) is still a snippet | one winter twig for the angle |
| **annual shoot ("sprig")** | ✅ **YES** | ✅ **YES** *(upgraded)* | ✅ **rhythm CLOSED: rhythmic, MONOCYCLIC — a GU is a year** (C&E ×3, §4.2). ✅ **branching mode CLOSED, and CORRECTED: BOTH modes — sylleptic in years 0–2 only, proleptic from the AU onward.** Residual: no measured GU length for **A1** (C&E's table leaves that cell blank); A2–A5 are **measured at 15/10/7/5 nodes** | measurement, or Genoyer 1999 |
| **★ short shoot (A5, was "S")** | ✅ **YES** | ✅ **YES as a mechanism** | ✅ its production rule is now tabulated: **5 nodes, distichous, terminal sexuality, sheds after 1–4 yr, *"peu nombreux"*.** ⚠ A4 *also* flowers, so "the flowering category" is A4+A5 | — |
| **twig** | **YES** (E1 + E3) | **YES as a mechanism** | per-relay kink angle unmeasured. **NARROWED:** the relay leaves *"dans le **prolongement** du module"* (small angle) while laterals take *"un angle d'insertion **ouvert**"* — relay ≪ lateral, `[PS]`, no number | measurement |
| **secondary branch** | **PARTIAL** | **NOT YET** | insertion angle, along-limb spacing unmeasured; **epitony vs hypotony NARROWED, not closed** — C&E settles only the reiterate case (a new complex arises at the **summit of the arch**, i.e. the upper side, `[PS]`); ordinary laterals on a slanted parent remain unknown | literature; failing that, a scaled photo of one horizontal limb |
| **★ primary limb** | **YES — mechanism complete** (E1+E2+E3+E4+E5+E6) | **MECHANISM yes; PARAMETERS no** | taper exponent for plane; bare-zone fraction; fork angle; per-relay kink angle; **tip-upturn cause unresolved** (young-segment righting vs B&C "mixed axis") | the four numbers are **one measurement session on real limbs** (or a scaled winter photo set). ⚠ This is the honest bar: *do not fit them to the existing single-angle frames.* |
| **trunk / bole** | **YES** (relay + ratchet; clear length = shed output) | **YES as a mechanism** | **no numeric diameter threshold for the smooth→fissured bark transition** in plane | literature search failed; a scaled photo of a bole series would settle it (cheap) |
| **★★ reiterated complex** | ✅ **YES — and the firing SUBSTRATE is now named: relay dominance `D`. A fork IS a reiteration** (§4.7). **TWO birth modes** (terminal fork / latent bud) with **two different truncation laws** | **★ DESIGN-READY** | ⚠ **the PLANE-SPECIFIC QUANTITATIVE STAGING** — `Φ_fork`, the per-wave dominance reset `D₀`, the pauperization rate γ. The *shape* of every law is now known **and sourced**; the *numbers* are not. ⚠ Also **NEW FORK F7**: which birth mode(s) the grower implements | **Genoyer et al. 1999** ([10.17660/ActaHortic.1999.496.26](https://doi.org/10.17660/ActaHortic.1999.496.26)). **Priority UNCHANGED** — C&E gave the mechanism, Genoyer still holds every number |
| **architectural metamorphosis** (the limb's category change) | ✅ **YES — mechanism sourced, plane-specific** | **MECHANISM yes; THRESHOLD no** | C&E gives the *observable*: *"branches mixtes, **verticales à leur base, horizontales à leur extrémité**"*, and the transition-zone A2s whose successive GUs go spiral→spiro-distichous→distichous **while turning horizontal**. So **phyllotaxis and posture co-vary within one axis** and metamorphosis is a continuous drift in the posture state, not a switch. The `D` **threshold** is still a number we lack | Genoyer 1999; Wilson 2000 (paywalled) for the reaction-wood mechanism |
| epicormic / knuckle | YES (mechanism) | n/a — **out of CP scope** | — | — |

### ★ Verdict on the reiterate: DESIGN-READY, with Genoyer as a REFINEMENT gap (not a blocker)

The reiterate was filed on 2026-07-08 as *"not generate-ready, blocked on the paywalled Genoyer et al."* **That
was a mis-diagnosis of the blocker,** and the correction matters more than the conclusion: the general
mechanism was sitting in an **open-access** paper we had already downloaded, in figures nobody opened. *Read
the whole primary source, figures included* — a specific, cheap instance of Rule 2.

**What is now sufficient to DESIGN the reiterate part-type** (all primary, all open access):
1. **Firing rule** — sequential/automatic reiteration occurs "*automatically … after a definite threshold of
   differentiation*," and is "*part of [the developmental] sequence*," not a regression. → schedule it off the
   same age/dominance-decay parameter that drives §10's crown series. **No trauma model needed.**
2. **Placement + truncation rule** — the **pauperization gradient**: complete reiterates low on the trunk,
   partial higher, **M.A.U. at the top/periphery**. → one positional scalar indexes *how much of the
   architectural unit the copy expresses*.
3. **Origin geometry** — the lateral **curves away and re-erects** into a new orthotropic axis (Figs. 26D, 30).
4. **Internal trend set** — GU length ↓, branching grade ↑, short shoots ↑, leaf size ↓ with physiological age
   (Fig. 27), and the copy inherits a *scaled* version of the parent's gradients.
5. **Plane's own axis categories** — T, B, S; labelled by **apparent** order; apex mortality at every tip (Fig. 18C).

**What is genuinely still missing, and is honestly a refinement:** the **plane-specific staging numbers** — how
many reiterate orders *P. × acerifolia* expresses at each developmental stage, at what heights, at what
insertion angles, and the counts per stage. Those are in Genoyer et al. 1999. **They tune a mechanism we can
now write down; they are not required to write it down.**

**Do not overclaim.** "Design-ready" here means: *the part-type can be specified and its parameters given
names and a source-grounded structure.* It does **not** mean the numbers are known — §"What I refuse to
supply" still stands, and now includes reiterate order-counts and insertion heights for plane. It also does
**not** mean the grower is ready: C3 (scaffolds-are-not-reiterates) is a structural change to the generator,
not a parameter edit.

### The shape of the gap set — a finding in its own right
**The part level is better served by the data we already hold than the crown level was.** §10's central gap
(mature crown aspect) is genuinely **off-computer**: it needs LiDAR/QSM or crown photogrammetry of CP specimens
plus clone ID, and it stays open. By contrast, **almost every gap above is a literature-access gap**, closable
at a desk or a university library:
- ✅ **Caraglio & Édelin 1990 — OBTAINED AND READ IN FULL, 2026-07-09** (text + all five plates as images;
  `reference/Architecture_et_dynamique_de_croissance.pdf`). It closed **more than it was asked for**: the AU
  (five rungs, not three), the rhythm (monocyclic), the acrotony rule, phyllotaxis, *and the firing mechanism
  itself* (relay dominance). It also **corrected two claims this document had made** — "plane branches
  proleptically" (true only from year ~2) and "plane is polycyclic" (false). ⚠ *And note what nearly went wrong:
  the plate pages were listed from the caption text as 5/8/10/12, but **Planche 2 — the AU table — is on page 7**.
  A caption-derived page list would have skipped the single most important figure in the paper.*
- **★ Genoyer et al. 1999** (the plane's ontogenic sequence, reiteration order, growth-unit morphology) —
  **DOI [10.17660/ActaHortic.1999.496.26](https://doi.org/10.17660/ActaHortic.1999.496.26)**, print/paywalled.
  **Downgraded 2026-07-09 from BLOCKER to REFINEMENT** — it supplies plane's staging *numbers*, not the
  mechanism (which is open access; see the reiterate verdict above).
- ⚠ **Lesson recorded:** the reiterate gap was mis-filed as library-blocked when the mechanism was in an
  open-access paper **already on disk**, in **figures that were never opened**. Captions ≠ figures. When a
  primary source is the backbone of a claim, **read its diagrams**, not only its text.
- Secondary: Huang, Hung & Kuo-Huang 2010 *Trees* 24:1151 (partitions growth-strain righting vs self-weight
  bending — would quantify E5 directly); Wilson 2000 (equilibrium angle); Mäkinen (branch demography, would
  quantify the bare-zone/self-pruning front).

**★ One volume closes two gaps.** *Acta Horticulturae* **496** is the proceedings of the 1997 International
Symposium on Urban Tree Health (Paris). Genoyer et al. is article **496.26**; the immediately preceding article,
**496.25**, is **Fournier-Djimbi, M. & Chanson, B., "Biomechanics of trees and wood for hazardous tree
assessment," 197–208** ([10.17660/ActaHortic.1999.496.25](https://doi.org/10.17660/ActaHortic.1999.496.25)) —
by the same Meriem Fournier whose posture-control work underpins **E5**. **Acquiring this single volume
therefore addresses both the plane-ontogeny gap and the righting-vs-self-weight quantification gap.** It is the
highest-value single library request this project has.

**One genuinely off-computer item**, and it is small: the **four limb numbers** (taper exponent, bare-zone
fraction, fork angle, per-relay kink angle). These need *scaled* observation of real limbs — a tape and a few
photographs with a scale bar, on any mature plane. That is a **cheap piggyback on the NYC data trip**, not a new
expedition, and unlike the crown-aspect gap it does not require an open-grown specimen or clone ID.

### What I refuse to supply
No fork angle. No taper exponent. No bare-zone fraction. No kink angle. No bark-transition diameter. **No
reiterate order-count per stage, no reiterate insertion heights, no pauperization rate for plane.** **And, new
2026-07-09: no module length for A1** — C&E's table leaves that cell blank, and interpolating it from A2's 15
nodes would be a fabrication dressed as a reading.

The imagery is single-angle and uncalibrated; the literature does not contain these for *Platanus*. **The
mechanisms are strong enough to generate the parts; the parameters must be measured, and until they are, they are
`[?]` and must be labelled so in any spec.** Every one is exactly the kind of number that, fitted to a thin
anchor, produced the lollipop.

> ⚠ **And a number I refuse to supply *even though C&E measured five of them*.** The paper gives per-category
> self-pruning tempos — A1 never, A2 long, A3 medium, A4 1–6 yr, A5 1–4 yr. The tempting move is to hard-code
> them as five lifespans. **That would violate Rule 3.** An axis lifespan is not given to a tree; it is **what
> happens** to an axis that stops paying for itself. The five tempos are a **five-point validation curve for the
> single `τ_shed` threshold**, and their monotone ordering is *forced* by the mechanism (module length falls
> 15→10→7→5 while each rung sits deeper in the shade). One knob, five ordered predictions, falsifiable.
> See `grower_reiterate_design.md` §7.3.

---

## 8. Report-back summary

**(a) The refined part taxonomy.** Botany does not use a caliber-rank ladder. It uses **nested construction
units** (metamer → growth unit → sympodial module → annual shoot → axis → architectural unit → reiterated
complex) crossed with a **small finite set of axis categories** assigned by the **physiological age of the
meristem** — and B&C 2007 state flatly that "*the categories of axes may or may not be superposed to the notion
of branching order*." Four consequences: **(F1)** *Platanus* has **no terminal bud** and relays sympodially
every year, so strict branch order is degenerate — and `hierarchy_depth`/hop-count are branch-order-like
counters, so part identity must never be gated on depth; **(F2)** ★ category ≠ order, and **B&C's Figure 18
uses *Platanus* itself as the worked counter-example**, citing the plane monograph — this is primary and
plane-specific, not an inference; **(F2b)** an axis can **change category** ("*reversion of axis differentiation
is very often possible*"), and the macro-form is **architectural metamorphosis** — a plane's primary limb
literally *is* a different kind of object at 60 years than at 6; **(F3)** the **number of part-types grows with
the tree**, and is the plane's own published early ontogenic marker. Chris's five parts survive as render
categories, with two corrections: a **primary limb is a *reiterated complex*, not a large secondary**, and a
**sixth part — the reiterate — is missing from our taxonomy and our code.**

**(b) Per-part developmental account.** Six forces drive everything: **relay** (no terminal bud → annual module
chain, one kink per year), **apical-control decay** (Borchert–Honda λ), **branch autonomy → light-driven
shedding** ("*the key to the formation of tall boles*"), **pipe model with memory** (diameter is a ratchet on
maximum historical load, never reduced when branches are shed), **posture** (gravitropic set-point angle
defended by tension wood, losing slowly to self-weight because righting capacity falls as the limb fattens),
and **reiteration**. Position-dependence has a single governing rule: "*the exact structure of a lateral axis
depends on its topological and ontogenetic position on the parent axis*," expressed through named morphogenetic
gradients (base effect, drift, acrotony, epitony/hypotony, order) — and reiteration *duplicates the whole
gradient set* at a new origin, which is why a veteran's primary limb reads as a small tree.
**Chris's primary-limb life history:** thickening under leaf load ✔; bending under accumulating self-weight ✔
(and "struggle" is the exactly right word — the limb *loses* it, because moment rises while righting capacity
falls); **"the same part at two points in a life trajectory" ✔✔ — it has a formal name, architectural
metamorphosis**, though ✘ *in identity* (it is a relay chain, then a reiterate, not one aged apex — and that is
what makes it crooked); **shade-escape ✘ — not supported**: GSA + self-weight set the horizontal, and overhead
shade *kills* a limb rather than steering it (partial vindication: release from apical control *does* move a
limb, **upward**, by reaction wood — opposite sign); **"gaps stretched" ✘ — a woody stem cannot elongate
mid-axis**, so the bare proximal zone was *weakly branched to begin with* (base effect) and then *shed*, never
stretched — but **"the spacing is a fossil record" ✔, and more literally than claimed: the occluded stub
sockets are visible on the bark.**

**(c) Where the three layers converge and conflict.** They **converge** on the age axis (λ-decay = apical
control decay = crown metamorphosis — three literatures, one mechanism), on volumetric fill, on derived taper,
on shedding-makes-boles, and on light as an unimplemented second axis. They **conflict** in four places, and
each conflict explains a defect already measured and mis-attributed:
- **C1** the engine grows *continuously and monopodially* (step `D`); plane grows *modularly and sympodially*.
  There is no event at which a crook can be born → the straight busy twigs. **The primitive should be the
  annual module, not `D`.**
- **C2** the engine derives radius from the *final* graph; reality ratchets it over *history*. A shed-nothing
  grower **cannot** make a thick bare proximal limb → the "limbs read thin/wire" finding, and the reason AC-14
  had to be bolted on and satisfied by a hand-weighted `w^(p/2)` partition that **fakes the ratchet**.
- **C3** four scaffolds off one spine are laterals, not reiterates → §10's "several trees fused" mature crown is
  **structurally unreachable** at any parameter setting.
- **C4** `cb_frac` is imposed as an envelope input, but clear bole is an *output of shedding* — the next
  instance of the project's own hard-won *"depth is an output, not a parameter"* lesson.
- **C5** posture (set-point angle, self-weight, righting) is absent entirely; `tropism = 0`.
- **C7** the two literatures themselves disagree — the modelling school makes light the *driver*, the
  architecture school says environment "*almost never modify the inherent morphogenetic and ontogenetic
  constructional rules*." Our engine has silently adopted the first. A grower needs both: an endogenous
  sequence that emits part *types* in order, plus a light/mechanics layer that prunes and poses them.
  Unresolved, and flagged rather than papered over.

**(d) Honest verdict per part** *(revised again 2026-07-09, after C&E 1990 was read in full)*.
**Generate-ready as mechanisms:** metamer/bud, twig, trunk/bole, **the primary limb**, **the reiterated complex**
(DESIGN-READY), and — newly upgraded — **the annual shoot** and **the short shoot (A5)**, whose production rules
C&E tabulates. The reiterate fires when **relay dominance collapses**, which produces a **fork**, and each fork
element is a reiterate; it is truncated by **which AU rung it starts at**, by one of **two laws** depending on
**birth mode**. Genoyer et al. 1999 stays a **refinement** — it holds plane's *staging numbers*, not the
mechanism. **Not yet:** the secondary (epitony vs hypotony for ordinary laterals still unknown), and the
metamorphosis *threshold*.

**Plane's architectural unit is FIVE rungs (A1…A5), not three.** The T/B/S carve came from B&C Fig. 18C, a
teaching diagram about category-vs-order, used second-hand as a specification. **`B` splits into A2/A3/A4**, and
that split is load-bearing: the reiterate's own truncation rungs are `c.r.p. A3` and `c.r.p. A4`.

**Three of this document's own claims were wrong and are corrected in place:** (i) *"plane branches
proleptically"* — true only from the architectural unit onward; **syllepsis occurs in years 0–2**; (ii) *"plane
is … polycyclic"* — **it is monocyclic**, one growth unit per year, and no source ever said otherwise;
(iii) C7 was filed as unresolvable — **it is resolved**, in B&C's own exception clause.

**No parameters are supplied** — taper exponent, fork angle, bare-zone fraction, per-relay kink angle,
bark-transition diameter, reiterate order-counts, insertion heights, **A1's module length**, and the five
self-pruning tempos *as parameters* (they are a validation curve, not inputs — Rule 3). None invented.

**(e) The four grower conflicts are one missing abstraction.** C1 (annual modules), C2 (pipe-model ratchet), C3
(scaffolds≠reiterates) and C5 (set-point angle) were logged as independent defects. With the reiterate specified
they collapse: a reiterate is a sub-tree that inherits the relay (C1), earns its own bole diameter by its own
shedding (C2), replaces the `linspace` scaffold (C3), and is *born* by a plagiotropic lateral acquiring an
orthotropic set-point (C5). `N_PRIMARIES` becomes an **output** of the firing schedule — the same "output, not
parameter" correction as `cb_frac` and the retired depth cap.

**(f) Process finding, recorded as a rule.** The reiterate was filed as blocked on a paywalled paper. It was
not: the mechanism was in an **open-access** paper **already downloaded**, in **figures that were never
opened**. The previous pass read the text and the captions and stopped. **Captions are not figures.** Rule 2
("prior art first") needs the corollary: *read the diagrams.*

---

## 9. → The design lives in a sibling doc (2026-07-09)

Understanding is complete; the design is written up separately in
**[`docs/grower_reiterate_design.md`](grower_reiterate_design.md)** (spec only — no grower code, nothing
committed). What it concluded, and what it found that this doc did not:

- **The reiterate object** is recursive: its `Axis` **is** the existing `strand`, its `Module` is a new time
  quantum, and it is **born by re-categorizing a `B` axis to `T`** — the re-erection *is* the birth (C5).
- **Firing is automatic/sequential** off a physiological-age threshold; **pauperization truncates the copy by
  topological path distance** from the root. `N_PRIMARIES`, `cb_frac` and **`DBH`** all convert from inputs to
  **outputs** (and `DBH` thence to a *validation target* against the 1564-tree census we already hold).
- **AC-14's `w^(p/2)` partition is deleted** — the design identifies it as a **clock substitute**. AC-14 as an
  *acceptance criterion* is kept, now earned rather than imposed.
- **★ Two new findings the part model did not reach.**
  1. **The abstraction under the abstraction is TIME.** C1/C2/C3/C5 each assert something about *history* — a
     ratchet is a max over the past, a threshold is a crossing, shedding presupposes growth. **The grower has no
     clock** (verified: `build_trunkscaffold` runs once; `_finish` computes radius from the *final* children and
     rescales to an imposed DBH). The reiterate is first-class only if the year is.
  2. **★ GAP-AU — a prerequisite, not a refinement.** A reiterate is *by definition* a truncated copy of the
     **architectural unit**. We have never specified plane's AU. B&C Fig. 18C gives the category *list*
     (T, B, S); nothing we can read gives the per-category *production rules*. **You cannot truncate what does
     not exist.** This outranks the Genoyer staging numbers.
- **Space colonization belongs to the twig categories only.** Orthotropy/plagiotropy is a category syndrome, so
  the direction law is per-category: posture for `T`/`B`, space-filling for `S`. The "pom-pom of equal sticks"
  and the "garden-hose arc" were one error — *using a twig rule to build a limb*.
- **Six forks are flagged for Chris (F1–F6)**, chief among them the light model: Palubicki warns explicitly that
  the shed rule "*is more suitable for models that rely on shadow propagation rather than space colonization*,"
  because a binary `Q` would shed branches the moment they stop growing. **Our `Q` is binary.**
**The gap set has a shape worth reporting:** unlike §10's crown-aspect gap, which is genuinely off-computer
(LiDAR/QSM + clone ID), **almost every part-level gap is a literature-access gap** — chiefly **Genoyer, Atger,
Edelin & Caraglio 1999, *Acta Hort.* 496:209–220, DOI
[10.17660/ActaHortic.1999.496.26](https://doi.org/10.17660/ActaHortic.1999.496.26)**, which names the plane's
primary limbs as the carriers of its whole developmental signal and is the highest-value unread source this
project has — and whose **own volume also carries the Fournier biomechanics paper** that would close the E5 gap
(§7). The one real off-computer item is four numbers off a tape and a scale bar on any mature limb — a cheap
piggyback on the NYC trip, not an expedition.

**Doc-hygiene correction made here, not silently:** growth doc §10.2 cites this work as "[PS — Édelin,
*Architecture et dynamique de croissance du platane*]". The paper is **Caraglio, Y. & Édelin, C. (1990)**,
*Bull. Soc. Bot. France, Lettres Bot.* 137(4–5): 279–291 — **Caraglio is first author**.
✅ **Its body has now been read in full (2026-07-09), text and all five plates.** Both plane-specific claims in
growth-doc §10.2 are **promoted from secondary to primary**: *"L'arbre d'avenir … est **conforme au modèle de
Massart**"* (Planche 5, Fig. 1) and *"La cime du Platane est édifiée par un phénomène de **réitération** précédé
d'une véritable **métamorphose architecturale**"* (abstract). Retag them `[PS]`.

**★ Rule-2 corollary, earned twice now.** The last pass learned *"captions are not figures — read the diagrams."*
This pass nearly repeated the error in a new form: a note listed C&E's plate pages as **5/8/10/12**, derived from
where the caption text falls. **Planche 2 — the architectural-unit table, the single figure this whole
prerequisite was about — is on page 7**, and rendering only the listed pages would have missed it entirely.
**Do not derive a figure's location from its caption. Enumerate the pages.**

*No code written, no build run, no protected file edited, no tree generated, nothing committed. Deliverable is
this document. Working notes and downloaded frames: `tmp/partmodel/` (gitignored).*
