// Steel Accord - construction reveal for 3D structures. Everything below the build height is the finished model;
// above it, a scaffold lattice (world-space grid) is drawn over a faint ghost of the model; a warm band marks the line.
// Swapped onto a structure's meshes while it is being built, then the imported materials are restored.
shader_type spatial;
render_mode cull_back;
#include "res://shaders/fog.gdshaderinc"

uniform sampler2D albedo_tex : source_color, filter_linear_mipmap, hint_default_white;
uniform vec4 albedo_col : source_color = vec4(1.0);
uniform float build_y = 100.0;      // world height of the build line
uniform float base_y = 0.0;

varying vec3 wp;

void vertex() {
	wp = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	vec3 col = texture(albedo_tex, UV).rgb * albedo_col.rgb;
	float above = wp.y - build_y;
	if (above > 0.0) {
		vec3 g = abs(fract(wp / 2.2) - 0.5);
		float lattice = step(0.44, max(g.x, g.z)) + step(0.45, g.y);
		if (lattice < 0.5) {
			if (mod(floor(FRAGCOORD.x) + floor(FRAGCOORD.y), 3.0) > 0.5) discard;   // faint ghost
			col = mix(col, vec3(0.45, 0.6, 0.75), 0.6) * 0.8;
		} else {
			col = vec3(0.72, 0.62, 0.38);
		}
	}
	float band = 1.0 - smoothstep(0.0, 0.25, abs(above));
	col = mix(col, vec3(1.0, 0.75, 0.3), band * 0.8);
	ALBEDO = col * sa_fog_shade(wp.xz);
	ROUGHNESS = 0.85;
}
