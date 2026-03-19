## Central Park Walk

*An AI-human collaboration to reconstruct Central Park in 3D from freely available public data.*

Central Park Walk is a real-time 3D walking simulation of all 843 acres of New York's Central Park, built entirely from public data — LiDAR surveys, OpenStreetMap, the NYC Tree Census, building footprints — and interpreted by Claude (Anthropic). No objectives, no score. Just a place.

Every tree has a real measured height. Every path follows its real-world geometry. Every building has its actual footprint. The terrain is accurate to one foot. The data has gaps, and we leave them visible.

![Cherry Hill Dawn](screenshots/cpw_000.png)
*Dawn at Cherry Hill — sycamores over the Lake, 0.61m LiDAR terrain.*

![Bethesda Terrace](screenshots/cpw_001.png)
*Bethesda Terrace at noon. 6,557 buildings from NYC footprints + LiDAR heights.*

![Central Park Lawn](screenshots/cpw_002.png)
*Birch trees on the lawn. 15 Mtree species with crossed-quad leaf cards.*

![The Lake](screenshots/cpw_003.png)
*The Lake through spring foliage. 23 water bodies from OpenStreetMap.*

## Quick Start

### Prerequisites
- [Godot 4.6.1](https://godotengine.org/download) (Linux x86_64)
- [Terrain3D v1.0.1](https://github.com/TokisanGames/Terrain3D) plugin (included in `addons/`)
- Python 3 with `numpy`, `scipy`, `gdal`, `Pillow`
- [Blender 4.5 LTS](https://www.blender.org/download/lts/4-5/) (`blender4` symlink, for model regeneration)
- [Mtree addon v5.5](https://extensions.blender.org/add-ons/modular-tree/) (Blender, for tree generation)
- NVIDIA GPU recommended (Forward+ renderer)

### Setup

```bash
git clone https://github.com/central-park-walk/central-park-walk.git
cd central-park-walk

python3 download_osm.py
python3 download_assets.py
python3 download_models.py
python3 download_sounds.py
python3 convert_to_godot.py

/path/to/Godot_v4.6.1-stable_linux.x86_64 --path .
```

### Controls

| Input | Action |
|-------|--------|
| WASD | Walk |
| Mouse + RMB | Look |
| Scroll / +/- | Speed (Stroll / Walk / Jog / Bike / Drive / Fly) |
| T | Time speed (1x / 10x / 100x / Paused) |
| [ / ] | Time ±1 hour |
| P | Weather (Clear / Rain / Thunderstorm / Snow / Fog) |
| N / Shift+N | Month |
| G | Data gap markers |
| H | HUD |
| F11 | Fullscreen |
| F12 | Screenshot |

**Gamepad**: Left stick walk, right stick look, right trigger fly, left trigger screenshot. D-pad up/down speed, left/right ±1h. LB weather, RB month.

### CLI

```bash
-- --tour              # 340 automated screenshots → /tmp/tour/
-- --pos "x,z,yaw"    # Spawn at coordinates
-- --time noon         # dawn/morning/noon/golden_hour/dusk/night
-- --weather rain      # clear/rain/snow/fog
-- --season autumn     # spring/summer/autumn/winter
```

## What's In It

### Terrain
Terrain3D geometry clipmaps with 64 regions at native 0.61m LiDAR resolution (8192×8192 heightmap). Custom shader override: 12 OSM zone types, 15+ named location materials, 4 seasons, 5 weather modes, dappled canopy shade, cloud shadows, Manhattan schist rock outcrops via DSM blend (161K cells). AGX tonemapping with glow-before-tonemap. Built-in collision and clipmap LOD.

### Trees (9,852)
NYC Tree Census + OSM + woodland scatter across 12 ecological zones. 15 Mtree species × 3 size tiers = 46 GLBs. LiDAR heights (4,005 trees), canopy height model enrichment (1,450), DBH-estimated (4,397). Crossed-quad leaf cards, FBM bark, per-pixel noise. Invasive vines: porcelain berry + oriental bittersweet (13 variants).

### Vegetation (71 BD3D meshes + 30 undergrowth species)
7 shrubs, 12 herbs, 4 ferns, 4 wetland, 2 fungi, 1 grass — zone-specific placement. 11 species upgraded to BD3D Plant Library 3D foliage with PBR textures. 13 grass types, 3 mowed lawn variants, 4 clovers, 2 dandelions, 5 fallen leaf types, 3 fallen branches, 2 moss patches, 4 weeds, 4 saplings. 6 ground cover patch types × 4 variants.

### Water (23 bodies + 10 streams)
OpenStreetMap polygons with stone coping, dawn/dusk mist (8 fog volumes).

### Buildings (6,557)
NYC Building Footprints + LiDAR heights. 5 facade materials, floor-accurate windows, cornice bands, awnings, grime weathering.

### Infrastructure
17 bridges (custom Blender models), 4.8km perimeter wall, 364 barriers, 39 landmarks, 106 statue positions, 147 sports fields, 2,000+ furniture items (33 PBR models with ambientCG textures).

### Grass
Terrain3D GPU particle system — procedural blade placement around camera with zone-aware filtering, seasonal color, canopy suppression, wind response. Biome-specific tuft meshes in progress.

### Environment
Full day/night cycle, 4 seasons, 5 weather modes, AGX tonemapping, 48-lamp lighting pool, 5-layer ambient audio.

## Data Sources

All data is freely available. No paid APIs.

| Source | Provides | License |
|--------|----------|---------|
| [NYC LiDAR (2017)](https://gis.ny.gov/elevation/lidar-coverage) | 1ft terrain DEM | Public Domain |
| [OpenStreetMap](https://www.openstreetmap.org/) | Paths, water, buildings, bridges, furniture | ODbL |
| [NYC Tree Census](https://data.cityofnewyork.us/) | Tree positions, species, diameter, heights | Public Domain |
| [BD3D Plant Library](https://blendermarket.com/products/bd3d-plant-library) | 3D foliage meshes (shrubs, ferns, grass) | Free (Gumroad) |
| [ambientCG](https://ambientcg.com/) | PBR ground + furniture textures | CC0 |
| [Sketchfab](https://sketchfab.com/) | Photogrammetry statue scans | CC-BY |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Engine | Godot 4.6.1 (Forward+, GDScript) |
| Terrain | Terrain3D v1.0.1 (geometry clipmaps, GPU particle grass, GDExtension) |
| Data pipeline | Python (GDAL, numpy/scipy, Pillow) |
| 3D modeling | Blender 4.5.8 LTS + Mtree v5.5, BD3D Plant Library |
| Rendering | 24 custom GLSL shaders, AgX tonemapping, MultiMesh instancing, 8K world atlas |

## Philosophy

1. **Data-first**: Render from data or don't render. Gaps stay visible.
2. **Honest interpretation**: What data and AI perception together produce.
3. **Community-driven**: Humans contribute data, AI reinterprets it.
4. **Accessibility**: A walking simulator. No competition, no violence.

## How to Contribute

**No coding required**: Map furniture in OSM (only ~10% mapped). Take photogrammetry scans of statues (4 of 106 scanned). Record field audio. Photograph materials. Map rock outcrops.

**Technical**: Custom tree models. Interior spaces. Performance profiling. Cross-platform support.

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## Support

Central Park Walk is built by Christopher Abbey and Claude, with no institutional backing.

[![Contribute on Open Collective](https://opencollective.com/central-park-walk/contribute/button)](https://opencollective.com/central-park-walk)

## License

Code: [MIT](LICENSE). Assets: [CC-BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).

## Credits

**Christopher Abbey** — Creator, technical lead
**Claude (Anthropic)** — Co-creator: data interpretation, code, shaders, artistic decisions

Asset sources: [credits.txt](credits.txt). Map data © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors.
