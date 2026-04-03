#ifndef GPU_GRASS_H
#define GPU_GRASS_H

#include <godot_cpp/classes/camera3d.hpp>
#include <godot_cpp/classes/mesh.hpp>
#include <godot_cpp/classes/multi_mesh_instance3d.hpp>
#include <godot_cpp/classes/node3d.hpp>
#include <godot_cpp/classes/rendering_device.hpp>
#include <godot_cpp/classes/shader_material.hpp>
#include <godot_cpp/classes/texture2d.hpp>
#include <godot_cpp/variant/rid.hpp>

namespace godot {

class GPUGrass : public Node3D {
	GDCLASS(GPUGrass, Node3D)

private:
	// Configuration
	Ref<Mesh> grass_mesh;
	Ref<Material> grass_material;
	int max_instances = 262144;
	float spacing = 0.5f;
	float max_distance = 50.0f;
	float world_size = 5000.0f;
	int target_biome = -1;  // -1 = all biomes, 0-3 = specific biome

	// Wind state (set from GDScript each frame)
	Vector2 wind_vec;
	double elapsed_time = 0.0;

	// Terrain data textures (set from GDScript)
	Ref<Texture2D> heightmap_texture;
	Ref<Texture2D> landuse_texture;
	Ref<Texture2D> canopy_texture;

	// MultiMesh (created via RenderingServer for indirect draw)
	RID mm_rid;
	RID mm_instance_rid;
	RID instance_buffer;
	RID command_buffer;

	// Compute pipeline
	RenderingDevice *rd = nullptr;
	RID compute_shader;
	RID compute_pipeline;
	RID uniform_set;
	RID heightmap_sampler;

	// State
	bool initialized = false;
	bool init_attempted = false;

	void _initialize();
	void _setup_multimesh();
	void _setup_compute();
	void _dispatch_compute();
	void _cleanup();

	RID _get_texture_rd_rid(const Ref<Texture2D> &p_tex);

protected:
	static void _bind_methods();
	void _notification(int p_what);

public:
	GPUGrass();
	~GPUGrass();

	void _ready() override;
	void _process(double p_delta) override;

	void set_grass_mesh(const Ref<Mesh> &p_mesh);
	Ref<Mesh> get_grass_mesh() const;

	void set_grass_material(const Ref<Material> &p_mat);
	Ref<Material> get_grass_material() const;

	void set_max_instances(int p_count);
	int get_max_instances() const;

	void set_spacing(float p_spacing);
	float get_spacing() const;

	void set_max_distance(float p_dist);
	float get_max_distance() const;

	void set_world_size(float p_size);
	float get_world_size() const;

	void set_heightmap_texture(const Ref<Texture2D> &p_tex);
	Ref<Texture2D> get_heightmap_texture() const;

	void set_landuse_texture(const Ref<Texture2D> &p_tex);
	Ref<Texture2D> get_landuse_texture() const;

	void set_canopy_texture(const Ref<Texture2D> &p_tex);
	Ref<Texture2D> get_canopy_texture() const;

	void set_target_biome(int p_biome);
	int get_target_biome() const;

	void set_wind_vec(const Vector2 &p_wind);
	Vector2 get_wind_vec() const;
};

} // namespace godot

#endif // GPU_GRASS_H
