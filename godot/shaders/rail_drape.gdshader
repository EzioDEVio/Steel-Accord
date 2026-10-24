// Steel Accord - railway track parts draped on the heightfield (map_infra.gd): ballast bed, sleepers (MultiMesh) and
// rails. World-space vertices; y is the height above the ground, which is read from the terrain's height texture, so the
// track follows terrain edits. kind 0 = ballast (procedural gravel), 1 = rail steel (polished head), 2 = sleepers.
shader_type spatial;
render_mode diffuse_burley, world_vertex_coords;
#include "res://shaders/fog.gdshaderinc"

uniform sampler2D hmap : filter_linear, repeat_disable;
uniform vec4 hmap_info = vec4(-600.0, -600.0, 2.0, 601.0);
uniform sampler2D n_detail : filter_linear_mipmap, repeat_enable;
uniform int kind = 0;
uniform vec3 base_color : source_color = vec3(0.45, 0.43, 0.40);
uniform float to_camera = 0.05;

varying vec3 wp;
varying float hy;

float hgt(vec2 p) {
	return texture(hmap, ((p - hmap_info.xy) / hmap_info.z + 0.5) / hmap_info.w).r;
}

void vertex() {
	hy = VERTEX.y;
	VERTEX.y += hgt(VERTEX.xz);
	wp = VERTEX;
	VERTEX += normalize(CAMERA_POSITION_WORLD - VERTEX) * to_camera;
}

void fragment() {
	vec3 c = base_color;
	float r = 0.9;
	float m = 0.0;
	if (kind == 0) {
		vec4 F = texture(n_detail, wp.xz / 1.3);
		vec4 G = texture(n_detail, wp.xz / 7.0 + vec2(0.4, 0.2));
		c *= 0.75 + 0.45 * F.b * F.g + 0.1 * G.r;
		c = mix(c, c * vec3(0.78, 0.66, 0.52), smoothstep(0.55, 0.8, G.a) * 0.5);   // rust-brown staining
	} else if (kind == 1) {
		float head = smoothstep(0.6, 0.66, hy);
		c = mix(vec3(0.30, 0.22, 0.17), vec3(0.62, 0.62, 0.62), head);            // rusty web, polished head
		r = mix(0.7, 0.35, head);
		m = mix(0.2, 0.8, head);
	} else {
		vec4 F = texture(n_detail, wp.xz / 2.1);
		c *= 0.85 + 0.25 * F.b;
	}
	ALBEDO = pow(max(c, vec3(0.0)), vec3(2.2)) * sa_fog_shade(wp.xz);
	ROUGHNESS = r;
	METALLIC = m;
}
