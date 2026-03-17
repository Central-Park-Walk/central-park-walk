# Vegetation Rendering Best Practices in Godot 4 (as of early 2026)

Research compiled from Godot documentation, community forums, shader repositories, GodotFest talks, and developer showcases.

---

## 1. Transparency Modes for Foliage

### The Five Options (ranked by performance, best to worst)

| Mode | Render Pipeline | Sorting | Visual Quality | Use Case |
|------|----------------|---------|---------------|----------|
| **Alpha Scissor** | Opaque pass | Not needed | Hard edges | Fences, simple leaves |
| **Alpha Hash** | Opaque pass (Vulkan/Mobile only) | Not needed | Dithered edges (needs TAA) | Hair, soft foliage |
| **Alpha to Coverage** | Opaque pass (needs MSAA) | Not needed | MSAA-smoothed edges | Leaves with MSAA enabled |
| **Depth Pre-Pass** | Opaque + transparent | Partial | Smooth edges | Foliage needing correct sort |
| **Full Alpha Blend** | Transparent pass | Required | Smooth but sort issues | Avoid for vegetation |

### Practical Recommendations

- **Alpha Scissor is king for foliage.** It renders in the opaque pass, avoids transparency sorting entirely, and is the cheapest option. Set `ALPHA_SCISSOR_THRESHOLD` to ~0.4-0.5.
- **Alpha Hash** produces softer dithered edges but requires TAA to look clean. **NOT available in OpenGL/Compatibility renderer** -- only Vulkan Forward+ and Mobile. A custom shader workaround exists (copy the hash function from Godot's forward renderer source).
- **Alpha to Coverage** (`alpha_to_coverage` render mode) uses MSAA to antialias alpha-scissored edges. Moderate performance cost, but effective. Requires MSAA to be enabled in project settings. Two sub-modes: Alpha Edge Blend and Alpha Edge Clip (combines with alpha-to-one).
- **Depth Pre-Pass** (`depth_prepass_alpha`) is Godot's official recommendation for "transparent grass or tree foliage" when sorting matters. Renders opaque pixels first via opaque pipeline, then remaining pixels with alpha blend. More expensive than scissor alone.
- **Full alpha blend is an FPS killer.** Forum reports: a simple tree with alpha-blended leaves dropped FPS from 200 to 40. Avoid for vegetation.

### Distance-Adaptive Scissor Trick (from TreeIt shader)
```glsl
float threshold_dist_modifier = 1.0 - min(view_distance / max_distance, 1.0);
ALPHA_SCISSOR_THRESHOLD = alpha_scissor_threshold * threshold_dist_modifier;
```
This lowers the scissor threshold at distance, making distant leaves appear fuller (compensating for mipmap alpha erosion).

### ALPHA_HASH_SCALE in Custom Shaders
For the hexaquo grass LOD system, `ALPHA_HASH_SCALE = 1.0;` enables dithered alpha in the opaque pass -- avoids expensive alpha blending while allowing per-blade fade-out at distance.

---

## 2. Two-Sided Leaves and Backlight/Translucency

### render_mode cull_disabled
Every foliage shader uses `cull_disabled` to render both sides of leaf quads. Combined with:

```glsl
// Fix normals for back faces
if (!FRONT_FACING) NORMAL = -NORMAL;
// Or equivalently:
NORMAL = FRONT_FACING ? NORMAL : -NORMAL;
```

### Three Approaches to Leaf Translucency (cheapest to most expensive)

#### A. BACKLIGHT (cheapest -- built-in)
```glsl
BACKLIGHT = vec3(0.2);  // or texture-driven
```
Works like direct light but received even when normals face away from the light. Built into Godot's spatial shader. No extra passes. **Best cost/quality ratio for foliage.**

The TreeIt shader uses a dedicated backlight texture:
```glsl
BACKLIGHT = texture(texture_backlight, UV).rgb * backlight_color.rgb;
```

#### B. Custom SSS in light() function (moderate cost)
From the GodotShaders.com foliage SSS shader:
```glsl
float get_sss(vec3 n, vec3 v, vec3 l, float s) {
    l = normalize(l);
    float kSSS = pow(clamp(dot((-l + n * s), v), 0.0, 1.0), power);
    return kSSS;
}

void light() {
    float kSSS = get_sss(normal, VIEW, LIGHT, sigma);
    vec3 SSS_color = albedo_influence * ALBEDO + light_color_influence * LIGHT_COLOR;
    DIFFUSE_LIGHT += SSS_color * (max(mix(1., ATTENUATION, attenuation_influence), 0.001) *
                     (0.3 + max(kD * scale, kSSS * scale)));
}
```
Based on Alex Zucconi's fast SSS method. Runs per-light per-fragment. Good quality but adds to fragment cost. Recommended uniforms: `sigma = 0.02`, `attenuation_influence = 0.98`.

#### C. SSS_STRENGTH + SSS_TRANSMITTANCE (most expensive -- built-in)
Godot's built-in subsurface scattering:
```glsl
SSS_STRENGTH = 0.5;
SSS_TRANSMITTANCE_COLOR = vec4(0.3, 0.6, 0.1, 1.0);
SSS_TRANSMITTANCE_DEPTH = 0.1;
```
Full screen-space subsurface scattering. Expensive -- involves extra passes. Usually overkill for foliage. Better for skin.

### Recommendation for Central Park
Use **BACKLIGHT** for all tree leaf shaders. It's built-in, costs almost nothing, and gives the "light through leaves" look when the sun is behind a tree. Reserve custom SSS for hero close-up vegetation only.

---

## 3. Billboard Leaf Quads -- Making Them Look Realistic

### Mesh Structure Rules (from FaRu85/Godot-Foliage and hexaquo)
1. Mesh must be **quad elements only** (two triangles per quad)
2. Each quad's UV should fill the **entire UV space** (0,0 to 1,1)
3. **UV2 X-coordinate** is used to randomly rotate each quad face for natural variation
4. Texture's **red channel** (or green channel) used as alpha mask in leaf shape
5. Colors set in shader, not baked into texture -- allows seasonal variation

### Avoiding the "Flat Rectangle" Look
- **Random rotation per quad** via UV2: each leaf card faces a different direction
- **Vertex offset billboard** (partial billboard): instead of full camera-facing, blend between original orientation and camera-facing:
```glsl
vec2 viewspace_offset = (UV - vec2(0.5)) * vertex_offset_scale;
vec4 modelspace_offset = inverse(MODELVIEW_MATRIX) * vec4(viewspace_offset, 0.0, 0.0);
VERTEX += modelspace_offset.xyz * billboard_strength;  // 0.0 = no billboard, 1.0 = full
```
- **Fresnel rim lighting** adds depth perception at leaf edges:
```glsl
float fresnel = pow(1.0 - dot(NORMAL, VIEW), fresnel_power);
vec3 final_color = mix(foliage_colour, fresnel_colour, fresnel * fresnel_strength);
```
- **Normal transfer from cylinder** (hexaquo method): In Blender, use Data Transfer modifier to copy normals from a cylinder onto leaf quads. This "implies roundness" and creates proper specular highlights on flat geometry.

### Mesh Creation Recommendations
- **Tree canopy**: 50-200 leaf quads arranged in a roughly spherical cluster. Each quad ~0.3-0.5m. Not billboard -- fixed orientation with random rotation from UV2.
- **Grass blade**: 3-9 triangles per blade (1 quad = 2 tris for simple, 4 quads = 8 tris for detailed). UV maps vertically 0-1 for shader-driven bend.
- **Simple LOD**: Remove vertices until blade is a single triangle. Switch mesh based on camera distance.

---

## 4. Wind Animation Techniques

### Method A: Noise-Based Vertex Displacement (Victor Karp)
Uses **FastNoiseLite** textures panned over time, fed into vertex positions. Vertex color channels control motion:
- **Red channel**: vertical gradient (trunk=0, crown=1) -- prevents trunk from moving
- **Green channel**: branch base-to-tip gradient -- allows tips to flutter more
- World position used as seed so each tree sways differently
- `MODEL_MATRIX` transform applied to wind direction for rotated instances

### Method B: Trigonometric Wind (TreeIt shader)
Uses global uniforms for wind coordination across all trees:
```glsl
global uniform vec4 tree_wind_size;   // (frequency, height_scale, ?, flutter_freq)
global uniform vec3 tree_wind_power;  // (trunk_sway, branch_sway, flutter_power)
```
Three layers:
1. **Global sway**: `cos/sin` of world position -- large trunk movement
2. **Branch variation**: per-vertex offset using `COLOR.y` and `COLOR.z`
3. **Leaf flutter**: high-frequency `sin` using world normals and `COLOR.x`

### Method C: Simple Sine Wind (hexaquo grass)
```glsl
uniform sampler2D wind_noise;
uniform float wind_strength = 0.3;
// Sample noise in world space, offset by time
vec2 wind_uv = world_vertex.xz / 10.0 - TIME * wind_direction * wind_strength;
float wind = texture(wind_noise, wind_uv).r;
VERTEX.xz += wind * bottom_to_top * wind_strength;
```

### Wind Color Shift (Synty shader)
Wind gusts darken/color-shift leaves to simulate changing light angles:
```glsl
wind_darken = (wind_gust + sway_gust) * 0.5;
// In fragment():
leaf_color = mix(leaf_color, wind_color_shift, wind_darken * wind_color_strength);
```

---

## 5. MultiMesh Best Practices for Vegetation

### Core Architecture
- **One draw call per MultiMeshInstance3D**, regardless of instance count
- All instances share **one mesh and one material**
- Instances are spatially indexed as a single AABB -- **no per-instance frustum culling**
- Supports per-instance: Transform3D + Color + custom_data (vec4)

### Chunking Strategy (essential for vegetation)
Since MultiMesh can't cull individual instances, divide vegetation into spatial chunks:
- **Terrain3D uses 32x32m cells**, each with its own MultiMeshInstance3D
- **Hexaquo grass uses 5x5m or 10x10m chunks**, 10K-20K blades per chunk
- Chunks enable frustum culling, occlusion culling, and distance-based hiding
- Load closest chunks first, 1 chunk per frame to avoid VRAM spikes

### Buffer API for Maximum Performance
```gdscript
# Allocate
var mm = MultiMesh.new()
mm.transform_format = MultiMesh.TRANSFORM_3D
mm.use_colors = true
mm.use_custom_data = true
mm.instance_count = max_instances
mm.mesh = blade_mesh

# Bulk write (fastest -- avoids per-instance overhead)
var buffer = PackedFloat32Array()
buffer.resize(instance_count * 16)  # 12 (transform) + 4 (custom)
# ... fill buffer ...
mm.buffer = buffer  # Single upload

# Control visibility
mm.visible_instance_count = actual_count  # Hide unused instances
```

### Key Limitations
- **visible_instance_count bug**: In some Godot versions, changing it after the first frame has no visual effect (instances drawn remain the same). Workaround: recreate the MultiMesh or use chunk show/hide instead.
- **No per-instance LOD**: All instances in a MultiMesh render at the same LOD level. Separate distant instances into their own MultiMeshInstance3D.
- **generate_aabb() is VERY SLOW** -- never call it frequently. Set AABB manually if possible.
- **Shadow cost**: Avoid casting shadows from grass/small vegetation. Shadows require lights to also render the grass geometry.
- **Material must be opaque or alpha-tested** for automatic instancing. Alpha-blended materials are never auto-instanced.

### Performance Numbers
- Hexaquo grass: 600 blades/m² in 5x5m chunks = ~15,000 blades per chunk, at 9 triangles/blade = 135K tris per chunk. Renders in ~2ms total for world-spanning coverage.
- Realistic forest (80.lv showcase): "steady 60 FPS (170 FPS uncapped) on RTX 3080" with all LODs and billboards spawned simultaneously.

---

## 6. LOD Strategies for Vegetation

### A. Godot's Built-in Mesh LOD
- **Automatic**: Godot generates LOD meshes on import using meshoptimizer library
- **Works with MultiMesh**: All instances switch LOD simultaneously based on distance to nearest instance group edge
- **Screen coverage based**: LOD switches based on mesh's screen coverage percentage
- **Import settings**: Can be disabled per-mesh. LOD bias adjustable per-node.
- **Caveat**: For MultiMesh, all instances get the same LOD. Chunk your MultiMeshes so distant chunks get lower LOD.

### B. Visibility Ranges (HLOD)
Properties on GeometryInstance3D (and MultiMeshInstance3D):
- `visibility_range_begin`: Distance where node starts appearing
- `visibility_range_end`: Distance where node stops appearing
- `visibility_range_begin_margin`: Fade-in distance
- `visibility_range_end_margin`: Fade-out distance
- `visibility_range_fade_mode`: `DISABLED`, `SELF`, or `DEPENDENCIES`

Use case: Show individual MeshInstance3D trees close up, switch to MultiMeshInstance3D cluster at distance, switch to billboard impostor further out.

**Visibility Parent**: Set on child nodes to automatically hide children when parent becomes visible (and vice versa). Enables LOD chains.

### C. Hexaquo Grass LOD System (most detailed reference)
Three tiers with smooth transitions:

| Distance | What renders | Triangles |
|----------|-------------|-----------|
| 0-10m | Full blade geometry (9 tri/blade) | 135K/chunk |
| 5-20m | Impostor planes (world-space textured) | ~100/chunk |
| 20m+ | Terrain shader impostor (0 extra tris) | 0 |

Key techniques:
- **Smoothstep crossfade** between tiers (no pop-in)
- **Per-instance alpha** via `instance uniform float alpha` (avoids material duplication)
- **AO flattening** during fade: `AO_LIGHT_AFFECT = mix(0.2, 1.0, alpha)`
- **Impostor color blending**: `ALBEDO = mix(ALBEDO, ground_color, 1.0 - alpha)`
- **Visibility toggling**: `$Grass.visible = mid_to_end < 1.0` prevents invisible geometry from consuming GPU
- **World-space texture sampling** on impostors for seamless transitions
- **Wind replication** on impostors using identical noise calculations

### D. Octahedral Impostors (for trees at extreme distance)
Plugin: [Godot-Octahedral-Impostors](https://github.com/wojtekpil/Godot-Octahedral-Impostors)
- Bakes tree from multiple angles into texture atlas (albedo, normal, depth, ORM)
- Single quad with shader that samples correct atlas region based on view angle
- **Hemisphere mode** recommended for trees (better side-view resolution)
- Baker generates: result_albedo.png, result_depth.png, result_normal.png, result_orm.png
- Grid size: typically 16 (256 views). Atlas resolution: 2048 recommended.
- Supports parallax from depth map for subtle 3D effect on flat plane
- **Godot 4 status**: v2.0 branch exists but compatibility needs verification

---

## 7. Texture Atlas Approaches

### For Leaf Quads
The FaRu85/Godot-Foliage approach: each quad uses full UV space (0,0 to 1,1) with a single leaf texture. This is simpler than atlas packing and works well with MultiMesh since all instances share one material/texture.

### For Multiple Species
Pack multiple leaf types into one atlas. Use INSTANCE_CUSTOM data to encode which region of the atlas each instance should sample:
```glsl
// In fragment shader:
vec2 atlas_offset = INSTANCE_CUSTOM.xy;  // e.g., (0.0, 0.0), (0.5, 0.0), etc.
vec2 atlas_uv = atlas_offset + UV * 0.5;  // if 2x2 atlas
```

### Godot's AtlasTexture
- `AtlasTexture` resource: defines a region within a larger texture
- Reduces draw calls when multiple sprites share one atlas
- For 3D vegetation, shader-based atlas sampling is more flexible than AtlasTexture resource

### Texture Packing Tools
- **TexturePacker plugin** (Godot 4 compatible): imports sprite sheets as AtlasTexture
- **Relintai/texture_packer**: C++ module for runtime texture packing

---

## 8. Community Plugins and Tools

### Vegetation Placement
| Plugin | Approach | Features | Status |
|--------|----------|----------|--------|
| **Spatial Gardener** | Paint on 3D surfaces | Thousands of instances, GDScript | Godot 4.x |
| **ProtonScatter** | Automatic positioning | Projects onto colliders, density maps | Godot 4.x |
| **Scatter Tool** | Level population | Collision support, foliage focus | Godot 4.x |
| **Foliage3D** | Procedural for Terrain3D | Integrates with Terrain3D plugin | Godot 4.x |

### Grass Rendering
| Plugin | Approach | Features | Status |
|--------|----------|----------|--------|
| **SimpleGrassTextured** | Mesh-based | Interactive mode (player collision on layer 17), LOD, heightmap baking | Godot 4.x |
| **grass_plugin_4_godot** | GPU-based | Handles huge amounts, 100x100 unit areas | Godot 4.x |
| **Terrain3D Instancer** | MultiMesh cells | 32x32m grid, up to 10 LODs, shadow impostor, distance culling | Godot 4.4+ |

### Tree Generation
| Plugin | Approach | Features | Status |
|--------|----------|----------|--------|
| **Tree3D** | Procedural | Varying complexity, editor tool | Godot 4.0-4.3 |
| **Zylann Tree Generator** | Procedural | Editor plugin, multiple species | Godot 4.x |

### Impostor/LOD
| Plugin | Approach | Features | Status |
|--------|----------|----------|--------|
| **Octahedral Impostors** (wojtekpil) | Multi-angle atlas | Bakes albedo/normal/depth, hemisphere mode | Godot 3.x (v2 branch for 4.x?) |
| **godot-imposter** (zhangjt93) | Octahedral for 4.x | Based on wojtekpil, updated for Godot 4 | Godot 4.x |

---

## 9. Reference Shaders (Complete, Production-Ready)

### A. TreeIt Tree Shader (MIT license)
**Best for**: Realistic trees with wind, backlight, distance-adaptive alpha
- `render_mode blend_mix, depth_draw_opaque, cull_disabled, diffuse_burley, specular_schlick_ggx`
- Uses global uniforms for coordinated wind across all trees
- BACKLIGHT texture for translucency
- Distance-adaptive `ALPHA_SCISSOR_THRESHOLD` (fuller at distance)
- Three-layer wind: global sway + branch variation + leaf flutter
- Vertex color channels: R=wind weight, G=height variation, B=leaf/trunk flag

### B. Synty Biomes Tree Shader (CC0 license)
**Best for**: Production trees with trunk+leaf separation, frost, wind color shift
- `render_mode depth_prepass_alpha, cull_disabled, diffuse_burley, specular_schlick_ggx`
- Vertex color B channel >0.5 = leaf, <0.5 = trunk (single shader for whole tree)
- Leaf tint base/highlight driven by vertex color G channel
- Frost overlay system (seasonal)
- Wind with gust noise, sway, jitter, deform, and bend layers
- Wind darkening/color shift on leaves
- `vectoralign()` function for natural trunk bending in wind

### C. Foliage SSS Shader (from GodotShaders.com)
**Best for**: Close-up foliage with visible light transmission
- `render_mode cull_disabled`
- Custom `get_sss()` in light() function
- Optional thickness map for varying translucency
- Vertex sway animation
- Alpha cutoff via discard

### D. Hexaquo Grass Blade Shader
**Best for**: Dense ground-level grass with natural variation
- `render_mode cull_disabled`
- `BACKLIGHT = vec3(0.2)` for translucency
- Patch noise for clumping (size + color variation)
- Normal mix toward vec3(0,1,0) at blade tips (diffuse specular)
- AO from UV.y (darker at base)
- `ALPHA_HASH_SCALE = 1.0` for distance fade

---

## 10. AAA-Quality Godot Vegetation: What the Best Projects Do

### The 80.lv Realistic Forest (RTX 3080, 60-170 FPS)
- **Terrain3D plugin** for terrain
- **Houdini** generates placement points based on curvature/slope, saved as binary
- Godot script instantiates random objects from categories using **RenderingServer** directly
- **All LODs and billboards spawned simultaneously**, visibility controlled via `visibility_range`
- Grass via **GPU particles** (developer notes this is "difficult to manage")
- Considering grid-based chunk system for better control

### GodotFest Large-Scale Vegetation Talk (Karl Bittner / hexaquo)
- **EZTree** + **Blender** for asset creation (free tools)
- Photograph-based billboard plants for variety
- Full impostor LOD system for open-world scale
- Emphasis on shading tricks that approximate foliage properties cheaply
- Production-ready system demonstrated at scale

### Key Takeaways from AAA Godot Projects
1. **Use RenderingServer directly** for thousands of instances (avoids node overhead)
2. **Chunk everything** into spatial cells (32x32m is a good default)
3. **Spawn all LODs simultaneously**, use visibility_range for switching
4. **Billboard impostors** for trees beyond ~100m
5. **GPU particles or custom MultiMesh** for grass (both have tradeoffs)
6. **Disable shadows on grass** -- use AO in shader instead
7. **Alpha scissor in opaque pass** -- never full alpha blend for vegetation
8. **Shared materials** across all instances of same type
9. **Binary data files** for placement data (not JSON/text)
10. **Houdini or equivalent** for smart placement (curvature, slope, density maps)

---

## 11. Relevance to Central Park Walk

### What the project already does well
- Hexaquo grass system with proper MultiMesh chunking (10m chunks, 20K blade cap)
- Alpha hash LOD crossfade on grass
- Buffer API for bulk instance upload
- 17 tree models with species variation
- Queue-based chunk loading (1/frame)
- Per-blade BACKLIGHT in grass shader

### Potential improvements based on this research
1. **Tree leaf translucency**: Add `BACKLIGHT` to tree leaf shaders (currently not mentioned in MEMORY.md shader list). Cheapest way to get light-through-leaves effect.
2. **Distance-adaptive alpha scissor** on tree leaves (TreeIt technique) to prevent distant canopy thinning from mipmap alpha erosion.
3. **Alpha to Coverage** if MSAA is enabled -- smoother leaf edges at minimal cost.
4. **Wind color shift** on tree leaves (Synty technique) -- gust-driven color variation adds realism.
5. **Octahedral impostors** for trees beyond ~100-150m -- single quad per tree instead of full geometry.
6. **Tree MultiMesh chunking** -- if trees are in one big MultiMesh, split into spatial chunks for frustum culling.
7. **Frost/snow overlay** on tree canopy for winter season (Synty shader has this built in).
8. **Normal transfer from cylinder** for leaf quads in Blender -- better specular highlights.

---

## Sources

### Official Documentation
- [Making Trees -- Godot Docs](https://docs.godotengine.org/en/stable/tutorials/shaders/making_trees.html)
- [Spatial Shaders Reference](https://docs.godotengine.org/en/stable/tutorials/shaders/shader_reference/spatial_shader.html)
- [Standard Material 3D](https://docs.godotengine.org/en/stable/tutorials/3d/standard_material_3d.html)
- [MultiMesh Optimization](https://docs.godotengine.org/en/stable/tutorials/performance/using_multimesh.html)
- [Mesh LOD](https://docs.godotengine.org/en/stable/tutorials/3d/mesh_lod.html)
- [Visibility Ranges (HLOD)](https://docs.godotengine.org/en/stable/tutorials/3d/visibility_ranges.html)
- [BaseMaterial3D Reference](https://docs.godotengine.org/en/stable/classes/class_basematerial3d.html)

### Hexaquo Grass Rendering Series (Karl Bittner)
- [Part 1: Theory](https://hexaquo.at/pages/grass-rendering-series-part-1-theory/)
- [Part 2: Full-Geometry Grass](https://hexaquo.at/pages/grass-rendering-series-part-2-full-geometry-grass-in-godot/)
- [Part 4: LOD Tricks](https://hexaquo.at/pages/grass-rendering-series-part-4-level-of-detail-tricks-for-infinite-plains-of-grass-in-godot/)

### GodotFest
- [Plants, Polygons and Pixels: Large-Scale Vegetation Rendering](https://godotfest.com/talks/plants-polygons-and-pixels-large-scale-vegetation-rendering-in-godot/)

### Community Shaders
- [TreeIt Tree Shader](https://godotshaders.com/shader/treeit-tree-shader/)
- [Synty Biomes Tree Shader](https://godotshaders.com/shader/synty-biomes-tree-compatible-shader/)
- [Stylized Fluffy Tree Leaves](https://godotshaders.com/shader/stylized-fluffy-tree-leaves/)
- [Foliage SSS Shader](https://godotshaders.com/shader/simple-foliage-subsurface-scattering-shader/)
- [Performant SSS Approximation](https://godotshaders.com/shader/performant-sss-sub-surface-scattering-approximation/)
- [Foliage Animation / Wind](https://godotshaders.com/shader/foliage-animation/)

### GitHub Repos
- [FaRu85/Godot-Foliage](https://github.com/FaRu85/Godot-Foliage)
- [TheMIU/Stylized-Fluffy-Tree-Shader](https://github.com/TheMIU/Stylized-Fluffy-Tree-Shader)
- [IcterusGames/SimpleGrassTextured](https://github.com/IcterusGames/SimpleGrassTextured)
- [HungryProton/scatter (ProtonScatter)](https://github.com/HungryProton/scatter)
- [dreadpon/godot_spatial_gardener](https://github.com/dreadpon/godot_spatial_gardener)
- [wojtekpil/Godot-Octahedral-Impostors](https://github.com/wojtekpil/Godot-Octahedral-Impostors)
- [zhangjt93/godot-imposter](https://github.com/zhangjt93/godot-imposter)
- [Zylann/godot_tree_generator_plugin](https://github.com/Zylann/godot_tree_generator_plugin)
- [marcosbitetti/grass_plugin_4_godot](https://github.com/marcosbitetti/grass_plugin_4_godot)
- [caphindsight/Foliage3D](https://github.com/caphindsight/Foliage3D)

### Tutorials and Articles
- [Victor Karp: Shader-Based Foliage Wind in Godot 4](https://victorkarp.com/godot-foliage-wind/)
- [GDQuest: Optimizing a 3D Scene](https://www.gdquest.com/tutorial/godot/3d/optimization-3d/)
- [80.lv: Realistic Forest in Godot](https://80.lv/articles/godot-developer-showcased-impressive-forest-scene-demo)
- [Terrain3D Instancer Documentation](https://terrain3d.readthedocs.io/en/stable/docs/instancer.html)

### Godot Issues / Proposals
- [Alpha Hash not in OpenGL (#103094)](https://github.com/godotengine/godot/issues/103094)
- [Transparent object performance (#60364)](https://github.com/godotengine/godot/issues/60364)
- [Alpha to Coverage proposal (#1273)](https://github.com/godotengine/godot-proposals/issues/1273)
- [GPU indirect rendering discussion (#8647)](https://github.com/godotengine/godot-proposals/discussions/8647)
- [Per-instance frustum culling proposal (#10669)](https://github.com/godotengine/godot-proposals/issues/10669)
