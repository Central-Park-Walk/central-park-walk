#include "gpu_grass.h"

#include <godot_cpp/classes/engine.hpp>
#include <godot_cpp/classes/file_access.hpp>
#include <godot_cpp/classes/multi_mesh.hpp>
#include <godot_cpp/classes/rd_sampler_state.hpp>
#include <godot_cpp/classes/rd_shader_source.hpp>
#include <godot_cpp/classes/rd_shader_spirv.hpp>
#include <godot_cpp/classes/rd_uniform.hpp>
#include <godot_cpp/classes/rendering_server.hpp>
#include <godot_cpp/classes/viewport.hpp>
#include <godot_cpp/classes/world3d.hpp>
#include <godot_cpp/core/class_db.hpp>
#include <godot_cpp/variant/utility_functions.hpp>

#include <cstring>

using namespace godot;

// Push constants layout — must match grass_compute.glsl exactly
struct GrassPushConstants {
	float camera_x, camera_y, camera_z, spacing;       // 16 bytes
	float grid_side, max_distance, max_instances, world_size; // 16 bytes
};
static_assert(sizeof(GrassPushConstants) == 32, "Push constants must be 32 bytes");

void GPUGrass::_bind_methods() {
	ClassDB::bind_method(D_METHOD("set_grass_mesh", "mesh"), &GPUGrass::set_grass_mesh);
	ClassDB::bind_method(D_METHOD("get_grass_mesh"), &GPUGrass::get_grass_mesh);
	ADD_PROPERTY(PropertyInfo(Variant::OBJECT, "grass_mesh", PROPERTY_HINT_RESOURCE_TYPE, "Mesh"),
			"set_grass_mesh", "get_grass_mesh");

	ClassDB::bind_method(D_METHOD("set_grass_material", "material"), &GPUGrass::set_grass_material);
	ClassDB::bind_method(D_METHOD("get_grass_material"), &GPUGrass::get_grass_material);
	ADD_PROPERTY(PropertyInfo(Variant::OBJECT, "grass_material", PROPERTY_HINT_RESOURCE_TYPE, "Material"),
			"set_grass_material", "get_grass_material");

	ClassDB::bind_method(D_METHOD("set_max_instances", "count"), &GPUGrass::set_max_instances);
	ClassDB::bind_method(D_METHOD("get_max_instances"), &GPUGrass::get_max_instances);
	ADD_PROPERTY(PropertyInfo(Variant::INT, "max_instances", PROPERTY_HINT_RANGE, "1024,1048576"),
			"set_max_instances", "get_max_instances");

	ClassDB::bind_method(D_METHOD("set_spacing", "spacing"), &GPUGrass::set_spacing);
	ClassDB::bind_method(D_METHOD("get_spacing"), &GPUGrass::get_spacing);
	ADD_PROPERTY(PropertyInfo(Variant::FLOAT, "spacing", PROPERTY_HINT_RANGE, "0.03,2.0,0.01"),
			"set_spacing", "get_spacing");

	ClassDB::bind_method(D_METHOD("set_max_distance", "distance"), &GPUGrass::set_max_distance);
	ClassDB::bind_method(D_METHOD("get_max_distance"), &GPUGrass::get_max_distance);
	ADD_PROPERTY(PropertyInfo(Variant::FLOAT, "max_distance", PROPERTY_HINT_RANGE, "10.0,200.0,1.0"),
			"set_max_distance", "get_max_distance");

	ClassDB::bind_method(D_METHOD("set_world_size", "size"), &GPUGrass::set_world_size);
	ClassDB::bind_method(D_METHOD("get_world_size"), &GPUGrass::get_world_size);
	ADD_PROPERTY(PropertyInfo(Variant::FLOAT, "world_size"),
			"set_world_size", "get_world_size");

	ClassDB::bind_method(D_METHOD("set_heightmap_texture", "texture"), &GPUGrass::set_heightmap_texture);
	ClassDB::bind_method(D_METHOD("get_heightmap_texture"), &GPUGrass::get_heightmap_texture);
	ADD_PROPERTY(PropertyInfo(Variant::OBJECT, "heightmap_texture", PROPERTY_HINT_RESOURCE_TYPE, "Texture2D"),
			"set_heightmap_texture", "get_heightmap_texture");

	ClassDB::bind_method(D_METHOD("set_landuse_texture", "texture"), &GPUGrass::set_landuse_texture);
	ClassDB::bind_method(D_METHOD("get_landuse_texture"), &GPUGrass::get_landuse_texture);
	ADD_PROPERTY(PropertyInfo(Variant::OBJECT, "landuse_texture", PROPERTY_HINT_RESOURCE_TYPE, "Texture2D"),
			"set_landuse_texture", "get_landuse_texture");

	ClassDB::bind_method(D_METHOD("set_canopy_texture", "texture"), &GPUGrass::set_canopy_texture);
	ClassDB::bind_method(D_METHOD("get_canopy_texture"), &GPUGrass::get_canopy_texture);
	ADD_PROPERTY(PropertyInfo(Variant::OBJECT, "canopy_texture", PROPERTY_HINT_RESOURCE_TYPE, "Texture2D"),
			"set_canopy_texture", "get_canopy_texture");
}

GPUGrass::GPUGrass() {}

GPUGrass::~GPUGrass() {
	_cleanup();
}

void GPUGrass::_notification(int p_what) {
	if (p_what == NOTIFICATION_PREDELETE) {
		_cleanup();
	}
}

void GPUGrass::_ready() {
	if (Engine::get_singleton()->is_editor_hint()) {
		return;
	}
	set_process(true);
}

void GPUGrass::_process(double p_delta) {
	if (Engine::get_singleton()->is_editor_hint()) {
		return;
	}

	if (!initialized) {
		if (!init_attempted) {
			init_attempted = true;
			_initialize();
		}
		return;
	}

	_dispatch_compute();
}

void GPUGrass::_initialize() {
	rd = RenderingServer::get_singleton()->get_rendering_device();
	if (!rd) {
		UtilityFunctions::push_warning("GPUGrass: RenderingDevice not available");
		return;
	}

	if (grass_mesh.is_null()) {
		UtilityFunctions::push_warning("GPUGrass: No grass_mesh assigned");
		return;
	}

	_setup_multimesh();
	if (!instance_buffer.is_valid()) {
		return;
	}

	_setup_compute();
	if (!compute_pipeline.is_valid()) {
		return;
	}

	initialized = true;
	UtilityFunctions::print("GPUGrass: Initialized — max_instances=", max_instances,
			" spacing=", spacing, " max_distance=", max_distance);
}

void GPUGrass::_setup_multimesh() {
	RenderingServer *rs = RenderingServer::get_singleton();

	mm_rid = rs->multimesh_create();
	rs->multimesh_allocate_data(mm_rid, max_instances,
			RenderingServer::MULTIMESH_TRANSFORM_3D,
			/*use_colors=*/true,
			/*use_custom_data=*/true,
			/*use_indirect=*/true);
	rs->multimesh_set_mesh(mm_rid, grass_mesh->get_rid());

	mm_instance_rid = rs->instance_create();
	rs->instance_set_base(mm_instance_rid, mm_rid);

	RID scenario = get_world_3d()->get_scenario();
	rs->instance_set_scenario(mm_instance_rid, scenario);
	rs->instance_set_visible(mm_instance_rid, true);
	rs->instance_geometry_set_cast_shadows_setting(mm_instance_rid,
			RenderingServer::SHADOW_CASTING_SETTING_OFF);

	if (grass_material.is_valid()) {
		rs->instance_geometry_set_material_override(mm_instance_rid, grass_material->get_rid());
	}

	AABB big_aabb(Vector3(-3000, -100, -3000), Vector3(6000, 200, 6000));
	rs->multimesh_set_custom_aabb(mm_rid, big_aabb);

	instance_buffer = rs->multimesh_get_buffer_rd_rid(mm_rid);
	command_buffer = rs->multimesh_get_command_buffer_rd_rid(mm_rid);

	if (!instance_buffer.is_valid() || !command_buffer.is_valid()) {
		UtilityFunctions::push_error("GPUGrass: Failed to get MultiMesh buffer RIDs");
	}
}

RID GPUGrass::_get_texture_rd_rid(const Ref<Texture2D> &p_tex) {
	if (p_tex.is_null()) {
		return RID();
	}
	RID tex_rid = p_tex->get_rid();
	return RenderingServer::get_singleton()->texture_get_rd_texture(tex_rid);
}

void GPUGrass::_setup_compute() {
	// Load GLSL source
	Ref<FileAccess> f = FileAccess::open("res://shaders/grass_compute.glsl", FileAccess::READ);
	if (f.is_null()) {
		UtilityFunctions::push_error("GPUGrass: Cannot open res://shaders/grass_compute.glsl");
		return;
	}
	String glsl = f->get_as_text();
	f->close();

	// Compile GLSL → SPIR-V
	Ref<RDShaderSource> source;
	source.instantiate();
	source->set_stage_source(RenderingDevice::SHADER_STAGE_COMPUTE, glsl);

	Ref<RDShaderSPIRV> spirv = rd->shader_compile_spirv_from_source(source);
	String err = spirv->get_stage_compile_error(RenderingDevice::SHADER_STAGE_COMPUTE);
	if (!err.is_empty()) {
		UtilityFunctions::push_error("GPUGrass: Shader compile error: ", err);
		return;
	}

	compute_shader = rd->shader_create_from_spirv(spirv);
	if (!compute_shader.is_valid()) {
		UtilityFunctions::push_error("GPUGrass: shader_create_from_spirv failed");
		return;
	}

	compute_pipeline = rd->compute_pipeline_create(compute_shader);

	// Create sampler for texture lookups
	Ref<RDSamplerState> sampler_state;
	sampler_state.instantiate();
	sampler_state->set_mag_filter(RenderingDevice::SAMPLER_FILTER_LINEAR);
	sampler_state->set_min_filter(RenderingDevice::SAMPLER_FILTER_LINEAR);
	sampler_state->set_repeat_u(RenderingDevice::SAMPLER_REPEAT_MODE_CLAMP_TO_EDGE);
	sampler_state->set_repeat_v(RenderingDevice::SAMPLER_REPEAT_MODE_CLAMP_TO_EDGE);
	heightmap_sampler = rd->sampler_create(sampler_state);

	// --- Set 0: Storage buffers ---
	TypedArray<RDUniform> set0_uniforms;

	Ref<RDUniform> u_instances;
	u_instances.instantiate();
	u_instances->set_uniform_type(RenderingDevice::UNIFORM_TYPE_STORAGE_BUFFER);
	u_instances->set_binding(0);
	u_instances->add_id(instance_buffer);
	set0_uniforms.push_back(u_instances);

	Ref<RDUniform> u_cmd;
	u_cmd.instantiate();
	u_cmd->set_uniform_type(RenderingDevice::UNIFORM_TYPE_STORAGE_BUFFER);
	u_cmd->set_binding(1);
	u_cmd->add_id(command_buffer);
	set0_uniforms.push_back(u_cmd);

	// --- Texture uniforms at bindings 2, 3, 4 ---
	// Heightmap
	RID hm_rd = _get_texture_rd_rid(heightmap_texture);
	if (hm_rd.is_valid()) {
		Ref<RDUniform> u_hm;
		u_hm.instantiate();
		u_hm->set_uniform_type(RenderingDevice::UNIFORM_TYPE_SAMPLER_WITH_TEXTURE);
		u_hm->set_binding(2);
		u_hm->add_id(heightmap_sampler);
		u_hm->add_id(hm_rd);
		set0_uniforms.push_back(u_hm);
	}

	// Landuse
	RID lu_rd = _get_texture_rd_rid(landuse_texture);
	if (lu_rd.is_valid()) {
		Ref<RDUniform> u_lu;
		u_lu.instantiate();
		u_lu->set_uniform_type(RenderingDevice::UNIFORM_TYPE_SAMPLER_WITH_TEXTURE);
		u_lu->set_binding(3);
		u_lu->add_id(heightmap_sampler);
		u_lu->add_id(lu_rd);
		set0_uniforms.push_back(u_lu);
	}

	// Canopy
	RID cn_rd = _get_texture_rd_rid(canopy_texture);
	if (cn_rd.is_valid()) {
		Ref<RDUniform> u_cn;
		u_cn.instantiate();
		u_cn->set_uniform_type(RenderingDevice::UNIFORM_TYPE_SAMPLER_WITH_TEXTURE);
		u_cn->set_binding(4);
		u_cn->add_id(heightmap_sampler);
		u_cn->add_id(cn_rd);
		set0_uniforms.push_back(u_cn);
	}

	uniform_set = rd->uniform_set_create(set0_uniforms, compute_shader, 0);
	if (!uniform_set.is_valid()) {
		UtilityFunctions::push_error("GPUGrass: uniform_set_create failed");
	}

	UtilityFunctions::print("GPUGrass: Compute pipeline ready — heightmap=",
			hm_rd.is_valid(), " landuse=", lu_rd.is_valid(), " canopy=", cn_rd.is_valid());
}

void GPUGrass::_dispatch_compute() {
	if (!rd || !compute_pipeline.is_valid() || !uniform_set.is_valid()) {
		return;
	}

	Viewport *vp = get_viewport();
	if (!vp) {
		return;
	}
	Camera3D *camera = vp->get_camera_3d();
	if (!camera) {
		return;
	}
	Vector3 cam_pos = camera->get_global_position();

	int grid_side = (int)(max_distance * 2.0f / spacing);
	if (grid_side > 2048) {
		grid_side = 2048;
	}
	int total_positions = grid_side * grid_side;

	// Zero instanceCount (byte offset 4 in command buffer)
	PackedByteArray zero_bytes;
	zero_bytes.resize(4);
	memset(zero_bytes.ptrw(), 0, 4);
	rd->buffer_update(command_buffer, 4, 4, zero_bytes);

	GrassPushConstants pc;
	pc.camera_x = cam_pos.x;
	pc.camera_y = cam_pos.y;
	pc.camera_z = cam_pos.z;
	pc.spacing = spacing;
	pc.grid_side = (float)grid_side;
	pc.max_distance = max_distance;
	pc.max_instances = (float)max_instances;
	pc.world_size = world_size;

	PackedByteArray push_bytes;
	push_bytes.resize(sizeof(GrassPushConstants));
	memcpy(push_bytes.ptrw(), &pc, sizeof(GrassPushConstants));

	int groups = (total_positions + 63) / 64;

	int64_t cl = rd->compute_list_begin();
	rd->compute_list_bind_compute_pipeline(cl, compute_pipeline);
	rd->compute_list_bind_uniform_set(cl, uniform_set, 0);
	rd->compute_list_set_push_constant(cl, push_bytes, push_bytes.size());
	rd->compute_list_dispatch(cl, groups, 1, 1);
	rd->compute_list_end();
}

void GPUGrass::_cleanup() {
	if (rd) {
		if (uniform_set.is_valid()) {
			rd->free_rid(uniform_set);
			uniform_set = RID();
		}
		if (compute_pipeline.is_valid()) {
			rd->free_rid(compute_pipeline);
			compute_pipeline = RID();
		}
		if (compute_shader.is_valid()) {
			rd->free_rid(compute_shader);
			compute_shader = RID();
		}
		if (heightmap_sampler.is_valid()) {
			rd->free_rid(heightmap_sampler);
			heightmap_sampler = RID();
		}
		rd = nullptr;
	}

	RenderingServer *rs = RenderingServer::get_singleton();
	if (rs) {
		if (mm_instance_rid.is_valid()) {
			rs->free_rid(mm_instance_rid);
			mm_instance_rid = RID();
		}
		if (mm_rid.is_valid()) {
			rs->free_rid(mm_rid);
			mm_rid = RID();
		}
	}

	instance_buffer = RID();
	command_buffer = RID();
	initialized = false;
}

// Property accessors
void GPUGrass::set_grass_mesh(const Ref<Mesh> &p_mesh) { grass_mesh = p_mesh; }
Ref<Mesh> GPUGrass::get_grass_mesh() const { return grass_mesh; }

void GPUGrass::set_grass_material(const Ref<Material> &p_mat) { grass_material = p_mat; }
Ref<Material> GPUGrass::get_grass_material() const { return grass_material; }

void GPUGrass::set_max_instances(int p_count) { max_instances = p_count; }
int GPUGrass::get_max_instances() const { return max_instances; }

void GPUGrass::set_spacing(float p_spacing) { spacing = p_spacing; }
float GPUGrass::get_spacing() const { return spacing; }

void GPUGrass::set_max_distance(float p_dist) { max_distance = p_dist; }
float GPUGrass::get_max_distance() const { return max_distance; }

void GPUGrass::set_world_size(float p_size) { world_size = p_size; }
float GPUGrass::get_world_size() const { return world_size; }

void GPUGrass::set_heightmap_texture(const Ref<Texture2D> &p_tex) { heightmap_texture = p_tex; }
Ref<Texture2D> GPUGrass::get_heightmap_texture() const { return heightmap_texture; }

void GPUGrass::set_landuse_texture(const Ref<Texture2D> &p_tex) { landuse_texture = p_tex; }
Ref<Texture2D> GPUGrass::get_landuse_texture() const { return landuse_texture; }

void GPUGrass::set_canopy_texture(const Ref<Texture2D> &p_tex) { canopy_texture = p_tex; }
Ref<Texture2D> GPUGrass::get_canopy_texture() const { return canopy_texture; }
