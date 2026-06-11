extends RefCounted
## Static data for tour mode, showcase shots, README captures, and named park areas.
## Extracted from main.gd to keep constant data separate from runtime logic.


const VIEWPOINTS: Array = [
	{"name": "bethesda_fountain", "x": -480.0, "z": 1020.0, "yaw": 180.0},
	{"name": "literary_walk", "x": -600.0, "z": 1420.0, "yaw": 30.0},
	{"name": "great_lawn", "x": -200.0, "z": 0.0, "yaw": 0.0},
	{"name": "conservatory_water", "x": -152.0, "z": 958.0, "yaw": 270.0},
	{"name": "alice_wonderland", "x": -96.0, "z": 869.0, "yaw": 315.0},
	{"name": "balto_south", "x": -473.0, "z": 1430.0, "yaw": 60.0},
	{"name": "the_lake", "x": -560.0, "z": 780.0, "yaw": 60.0},
	{"name": "cherry_hill", "x": -630.0, "z": 880.0, "yaw": 90.0},
	{"name": "cleopatras_needle", "x": 40.0, "z": 360.0, "yaw": 250.0},
	{"name": "ramble", "x": -400.0, "z": 600.0, "yaw": 225.0},
	{"name": "cpw_skyline", "x": -600.0, "z": 1420.0, "yaw": 90.0},
	{"name": "fifth_ave_skyline", "x": 100.0, "z": 200.0, "yaw": 270.0},
	{"name": "north_woods", "x": 600.0, "z": -1315.0, "yaw": 180.0},
	{"name": "reservoir_south", "x": -200.0, "z": -300.0, "yaw": 0.0},
	{"name": "bow_bridge", "x": -540.0, "z": 740.0, "yaw": 310.0},
	{"name": "soccer_fields", "x": 390.0, "z": -1070.0, "yaw": 30.0},
	{"name": "sheep_meadow", "x": -820.0, "z": 1100.0, "yaw": 180.0},
]

const ANGLES: Array = [
	{"suffix": "_0", "yaw_offset": 0.0, "pitch": 0.0},    # forward
	{"suffix": "_1", "yaw_offset": -90.0, "pitch": 0.0},   # left 90°
	{"suffix": "_2", "yaw_offset": 0.0, "pitch": -25.0},   # down
	{"suffix": "_aerial30", "yaw_offset": 0.0, "pitch": -55.0, "height": 30.0},   # 30m aerial
	{"suffix": "_aerial80", "yaw_offset": 0.0, "pitch": -75.0, "height": 80.0},   # 80m aerial overview
]

const TIMES: Array = [7.0, 12.0, 17.0, 22.0]

const SHOWCASE_SHOTS: Array = [
	# Summer golden hour — flagship shot
	{"name": "literary_walk_summer_golden", "x": -600.0, "z": 1420.0, "yaw": 30.0, "pitch": 0.0, "hour": 17.5, "season": 1.5, "weather": "clear"},
	# Autumn morning at Bethesda
	{"name": "bethesda_autumn_morning", "x": -480.0, "z": 1020.0, "yaw": 180.0, "pitch": 0.0, "hour": 8.0, "season": 2.5, "weather": "clear"},
	# Winter snow at the Lake — Bow Bridge area
	{"name": "bow_bridge_winter_snow", "x": -540.0, "z": 740.0, "yaw": 310.0, "pitch": 0.0, "hour": 12.0, "season": 3.5, "weather": "snow"},
	# Spring dawn at the Ramble
	{"name": "ramble_spring_dawn", "x": -400.0, "z": 600.0, "yaw": 225.0, "pitch": 0.0, "hour": 6.0, "season": 0.5, "weather": "clear"},
	# Rain at Conservatory Water
	{"name": "conservatory_rain_afternoon", "x": -152.0, "z": 958.0, "yaw": 270.0, "pitch": 0.0, "hour": 15.0, "season": 2.0, "weather": "rain"},
	# Night at Literary Walk — sodium vapor lamps
	{"name": "literary_walk_night", "x": -600.0, "z": 1420.0, "yaw": 30.0, "pitch": 0.0, "hour": 22.0, "season": 1.5, "weather": "clear"},
	# Winter fog at Great Lawn
	{"name": "great_lawn_winter_fog", "x": -200.0, "z": 0.0, "yaw": 0.0, "pitch": 0.0, "hour": 7.0, "season": 3.2, "weather": "fog"},
	# Autumn golden hour at Cherry Hill
	{"name": "cherry_hill_autumn_golden", "x": -630.0, "z": 880.0, "yaw": 90.0, "pitch": 0.0, "hour": 17.5, "season": 2.6, "weather": "clear"},
	# Summer noon skyline from Fifth Ave side
	{"name": "fifth_ave_summer_noon", "x": 100.0, "z": 200.0, "yaw": 270.0, "pitch": 0.0, "hour": 12.0, "season": 1.5, "weather": "clear"},
	# Snow at North Woods
	{"name": "north_woods_snow_morning", "x": 600.0, "z": -1315.0, "yaw": 180.0, "pitch": 0.0, "hour": 9.0, "season": 3.5, "weather": "snow"},
	# Spring rain at the Mall
	{"name": "the_mall_spring_rain", "x": -550.0, "z": 1300.0, "yaw": 180.0, "pitch": 0.0, "hour": 14.0, "season": 0.6, "weather": "rain"},
	# Autumn dusk at CPW skyline
	{"name": "cpw_skyline_autumn_dusk", "x": -600.0, "z": 1420.0, "yaw": 90.0, "pitch": 0.0, "hour": 19.0, "season": 2.5, "weather": "clear"},
	# Summer dawn at Reservoir
	{"name": "reservoir_summer_dawn", "x": -200.0, "z": -300.0, "yaw": 0.0, "pitch": -5.0, "hour": 5.5, "season": 1.5, "weather": "clear"},
	# Summer golden hour at Sheep Meadow — mowing stripes visible on green grass
	{"name": "sheep_meadow_summer_golden", "x": -690.0, "z": 1250.0, "yaw": 90.0, "pitch": -3.0, "hour": 18.0, "season": 1.5, "weather": "clear"},
	# Autumn at the Lake
	{"name": "the_lake_autumn_afternoon", "x": -560.0, "z": 780.0, "yaw": 60.0, "pitch": 0.0, "hour": 15.0, "season": 2.7, "weather": "clear"},
	# Spring morning at soccer fields
	{"name": "soccer_fields_spring_morning", "x": 390.0, "z": -1070.0, "yaw": 30.0, "pitch": 0.0, "hour": 9.0, "season": 0.5, "weather": "clear"},
	# Aerial views
	{"name": "bethesda_aerial_40m", "x": -480.0, "z": 1020.0, "yaw": 180.0, "pitch": -70.0, "hour": 12.0, "season": 1.5, "weather": "clear", "height": 40.0},
	{"name": "lake_aerial_80m_autumn", "x": -540.0, "z": 740.0, "yaw": 0.0, "pitch": -80.0, "hour": 15.0, "season": 2.5, "weather": "clear", "height": 80.0},
	{"name": "great_lawn_aerial_100m", "x": -100.0, "z": 100.0, "yaw": 0.0, "pitch": -85.0, "hour": 17.5, "season": 1.5, "weather": "clear", "height": 100.0},
	{"name": "conservatory_aerial_30m_rain", "x": -152.0, "z": 958.0, "yaw": 90.0, "pitch": -60.0, "hour": 14.0, "season": 2.0, "weather": "rain", "height": 30.0},
	{"name": "north_woods_aerial_60m_snow", "x": 600.0, "z": -1315.0, "yaw": 180.0, "pitch": -75.0, "hour": 10.0, "season": 3.5, "weather": "snow", "height": 60.0},
	{"name": "reservoir_aerial_120m_dawn", "x": -200.0, "z": -400.0, "yaw": 0.0, "pitch": -80.0, "hour": 6.0, "season": 1.5, "weather": "clear", "height": 120.0},
]

const README_SHOTS: Array = [
	# --- SUMMER ---
	{"name": "readme_literary_walk_summer", "x": -600.0, "z": 1420.0, "yaw": 30.0, "pitch": 0.0, "hour": 11.0, "season": 1.5, "weather": "clear"},
	{"name": "readme_ramble_summer", "x": -350.0, "z": 650.0, "yaw": 200.0, "pitch": 0.0, "hour": 10.5, "season": 1.5, "weather": "clear"},
	{"name": "readme_bethesda_summer", "x": -480.0, "z": 1020.0, "yaw": 350.0, "pitch": -5.0, "hour": 12.0, "season": 1.5, "weather": "clear"},
	{"name": "readme_sheep_meadow_summer", "x": -800.0, "z": 1110.0, "yaw": 160.0, "pitch": 0.0, "hour": 14.0, "season": 1.5, "weather": "clear"},
	{"name": "readme_bow_bridge_summer", "x": -540.0, "z": 740.0, "yaw": 310.0, "pitch": -3.0, "hour": 13.0, "season": 1.5, "weather": "clear"},
	{"name": "readme_cpw_skyline_golden", "x": -600.0, "z": 1420.0, "yaw": 90.0, "pitch": 0.0, "hour": 16.5, "season": 1.5, "weather": "clear"},
	# --- AUTUMN ---
	{"name": "readme_literary_walk_autumn", "x": -600.0, "z": 1420.0, "yaw": 30.0, "pitch": 0.0, "hour": 12.0, "season": 2.5, "weather": "clear"},
	{"name": "readme_sheep_meadow_autumn", "x": -800.0, "z": 1110.0, "yaw": 160.0, "pitch": 0.0, "hour": 14.0, "season": 2.3, "weather": "clear"},
	{"name": "readme_cherry_hill_autumn", "x": -630.0, "z": 880.0, "yaw": 90.0, "pitch": -3.0, "hour": 13.0, "season": 2.5, "weather": "clear"},
	{"name": "readme_north_woods_autumn", "x": 600.0, "z": -1315.0, "yaw": 180.0, "pitch": 0.0, "hour": 11.0, "season": 2.5, "weather": "clear"},
	# --- WINTER ---
	{"name": "readme_great_lawn_snow", "x": -99.0, "z": 173.0, "yaw": 270.0, "pitch": 0.0, "hour": 12.0, "season": 3.5, "weather": "snow"},
	{"name": "readme_bow_bridge_snow", "x": -540.0, "z": 740.0, "yaw": 310.0, "pitch": -3.0, "hour": 11.0, "season": 3.5, "weather": "snow"},
	{"name": "readme_literary_walk_winter", "x": -600.0, "z": 1420.0, "yaw": 30.0, "pitch": 0.0, "hour": 12.0, "season": 3.5, "weather": "snow"},
	# --- SPRING ---
	{"name": "readme_cherry_hill_spring", "x": -630.0, "z": 880.0, "yaw": 90.0, "pitch": -3.0, "hour": 11.0, "season": 0.5, "weather": "clear"},
	{"name": "readme_conservatory_spring", "x": -152.0, "z": 958.0, "yaw": 200.0, "pitch": -3.0, "hour": 13.0, "season": 0.5, "weather": "clear"},
	# --- WEATHER ---
	{"name": "readme_bethesda_rain", "x": -480.0, "z": 1020.0, "yaw": 350.0, "pitch": -5.0, "hour": 13.0, "season": 1.5, "weather": "rain"},
	{"name": "readme_north_woods_fog", "x": 850.0, "z": -1300.0, "yaw": 45.0, "pitch": 0.0, "hour": 10.0, "season": 1.5, "weather": "fog"},
	# --- GOLDEN HOUR ---
	{"name": "readme_sheep_golden", "x": -690.0, "z": 1250.0, "yaw": 90.0, "pitch": -3.0, "hour": 16.5, "season": 1.5, "weather": "clear"},
	{"name": "readme_lake_autumn_golden", "x": -560.0, "z": 780.0, "yaw": 60.0, "pitch": 0.0, "hour": 16.0, "season": 2.5, "weather": "clear"},
	{"name": "readme_reservoir_autumn", "x": -200.0, "z": -300.0, "yaw": 0.0, "pitch": -2.0, "hour": 14.0, "season": 2.5, "weather": "clear"},
]

# Central Park named areas — [x_min, x_max, z_min, z_max, name]
const PARK_AREAS: Array = [
	# ── Landmarks and major areas ──
	[-700, -400, 1300, 1500, "Literary Walk"],
	[-550, -380, 1050, 1300, "The Mall"],
	[-530, -390, 900, 1050, "Bethesda Terrace"],
	[-650, -420, 700, 900, "The Lake"],
	[-550, -200, 400, 700, "The Ramble"],
	[-700, -550, 800, 1000, "Cherry Hill"],
	[-200, 200, -200, 400, "Great Lawn"],
	# Bounds measured from world_atlas.bin lawn polygon flood fill (2026-06-10);
	# previous [-900,-600,1500,2100] was ~400m too far south (Pond/Wollman area).
	[-1000, -660, 1030, 1410, "Sheep Meadow"],
	[-300, 200, -800, -400, "Reservoir"],
	[-200, 100, 800, 1050, "Conservatory Water"],
	[200, 800, -1800, -1200, "North Meadow"],
	[400, 900, -1600, -1000, "North Woods"],
	[-100, 500, -200, 200, "Turtle Pond"],
	[600, 1200, -2200, -1700, "Harlem Meer"],
	[-100, 200, 600, 900, "Belvedere Castle"],
	[-350, 0, 200, 500, "Delacorte Theater"],
	[0, 300, 300, 500, "Cleopatra's Needle"],
	[-700, -500, 1450, 1550, "Naumburg Bandshell"],
	[-250, 0, -600, -300, "Reservoir Running Track"],
	[100, 500, -900, -600, "Tennis Center"],
	[-200, 200, -1200, -800, "Conservatory Garden"],
	[-600, -350, 600, 750, "Bow Bridge"],
	[-900, -650, 1100, 1350, "Strawberry Fields"],
	[-700, -400, 1900, 2100, "The Pond"],
	[-800, -500, 2050, 2200, "Wollman Rink"],
	[700, 1100, -2100, -1800, "Lasker Pool"],
	[-300, 0, 500, 700, "Shakespeare Garden"],
	[300, 700, -1100, -700, "The Pool"],
	[400, 800, -1400, -1100, "The Loch"],
	[-200, 200, -400, -200, "The Obelisk"],
	[-1100, -800, 1400, 1800, "Tavern on the Green"],
	# ── Additional areas from Conservancy maps ──
	[-500, -200, -1950, -1700, "The Ravine"],
	[-300, 100, -350, -100, "Summit Rock"],
	[-700, -500, 450, 650, "Ladies Pavilion"],
	[100, 400, 150, 400, "Cedar Hill"],
	[-650, -350, 1100, 1250, "The Dene"],
	[-400, -100, 1600, 1800, "Heckscher Ballfields"],
	[200, 600, -1050, -750, "East Meadow"],
	[-100, 200, -1800, -1500, "Great Hill"],
	[300, 600, -1600, -1350, "Conservatory Garden East"],
	[-800, -500, 1050, 1250, "Mineral Springs"],
	[-500, -200, 750, 950, "Wagner Cove"],
	[-300, 0, 50, 300, "Arthur Ross Pinetum"],
	# ── Playgrounds (from Conservancy Playground Map) ──
	[-700, -550, -1850, -1750, "Yoseoff Playground"],
	[-700, -500, -1100, -1000, "Tarr Family Playground"],
	[-750, -600, -800, -700, "Rudin Family Playground"],
	[-750, -600, -575, -475, "Wild West Playground"],
	[-750, -600, -425, -325, "Safari Playground"],
	[-750, -600, 25, 125, "West 85th St Playground"],
	[-700, -550, 100, 200, "Toll Family Playground"],
	[-750, -600, 325, 425, "Diana Ross Playground"],
	[-750, -600, 1300, 1400, "Tarr-Coyne Tots Playground"],
	[-750, -600, 1375, 1475, "Adventure Playground"],
	[-500, -300, 1675, 1800, "Heckscher Playground"],
	[250, 450, -1850, -1750, "East 110th St Playground"],
	[250, 450, -1700, -1600, "Bernard Family Playground"],
	[250, 450, -1100, -1000, "Bendheim Playground"],
	[250, 450, -800, -700, "Kempner Playground"],
	[200, 400, 25, 125, "Ancient Playground"],
	[200, 400, 475, 575, "Smadbeck Playground"],
	[200, 400, 625, 725, "Levin Playground"],
	[200, 400, 1000, 1100, "East 72nd St Playground"],
	[200, 400, 1375, 1475, "Billy Johnson Playground"],
	# ── Facilities ──
	[300, 500, -1850, -1750, "Dana Discovery Center"],
	[-600, -400, 1375, 1475, "Dairy Visitor Center"],
	[-550, -400, 1450, 1550, "Chess & Checkers House"],
	[100, 350, 1525, 1625, "Central Park Zoo"],
	[-400, -200, 1150, 1250, "SummerStage"],
	[-300, -100, 550, 700, "Swedish Cottage"],
]
