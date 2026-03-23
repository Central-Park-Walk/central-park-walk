GODOT   ?= godot
VERSION := $(shell git describe --tags --always 2>/dev/null || echo dev)

.PHONY: data import export-linux export-windows release clean

# ---------- Data pipeline (run locally, commit .bin files to LFS) ----------

data:
	python3 download_osm.py
	python3 download_terrain.py
	python3 download_buildings.py
	python3 download_assets.py
	python3 download_models.py
	python3 download_sounds.py
	python3 convert_to_godot.py

# ---------- Godot export ----------

import:
	$(GODOT) --headless --import

export-linux:
	@mkdir -p build/linux
	$(GODOT) --headless --export-release "Linux" build/linux/central-park-walk.x86_64

export-windows:
	@mkdir -p build/windows
	$(GODOT) --headless --export-release "Windows" build/windows/central-park-walk.exe

export-macos:
	@mkdir -p build/macos
	$(GODOT) --headless --export-release "macOS" "build/macos/Central Park Walk.app"

# ---------- Package for distribution ----------

release: export-linux export-windows export-macos
	cd build/linux   && chmod +x central-park-walk.x86_64 && tar czf ../../central-park-walk-$(VERSION)-linux-x86_64.tar.gz *
	cd build/windows && zip -qr ../../central-park-walk-$(VERSION)-windows-x86_64.zip *
	cd build/macos   && zip -qr ../../central-park-walk-$(VERSION)-macos-universal.zip "Central Park Walk.app"
	@echo ""
	@echo "Packages:"
	@ls -lh central-park-walk-$(VERSION)-*

clean:
	rm -rf build/ central-park-walk-*.tar.gz central-park-walk-*.zip
