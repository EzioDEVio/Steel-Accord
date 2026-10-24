// Steel Accord - paved road carriageway strip draped on the heightfield (map_infra.gd builds the strips).
// Vertices carry x/z in world space and y = lift above the ground; the ground height is read from the same half-float
// height texture the terrain shader uses, so a strip follows any later terrain edit (building pads) by itself.
// UV.x = metres across from the centre line, UV.y = metres along the road. COLOR.r = kerbs (town streets),
// COLOR.g = lane markings (main roads), COLOR.b = carriageway width / 20.
// No third-party textures: asphalt grain comes from the terrain's procedural detail noise.
shader_type spatial;
render_mode diffuse_burley, world_vertex_coords;
#include "res://shaders/fog.gdshaderinc"

uniform sampler2D hmap : filter_linear, repeat_disable;
uniform vec4 hmap_info = vec4(-600.0, -600.0, 2.0, 601.0);
uniform sampler2D n_detail : filter_linear_mipmap, repeat_enable;
uniform float lift = 0.05;
uniform float to_camera = 0.12;      // metres pulled toward the camera: no z-fighting with the terrain triangles

varying vec3 wp;
varying vec2 ruv;
varying vec4 vc;

float hgt(vec2 p) {
	return texture(hmap, ((p - hmap_info.xy) / hmap_info.z + 0.5) / hmap_info.w).r;
}

void vertex() {
	vec2 p = VERTEX.xz;
	float d = 1.5;
	VERTEX.y += hgt(p) + lift;
	NORMAL = normalize(vec3(hgt(p - vec2(d, 0.0)) - hgt(p + vec2(d, 0.0)), 2.0 * d, hgt(p - vec2(0.0, d)) - hgt(p + vec2(0.0, d))));
	wp = VERTEX;
	VERTEX += normalize(CAMERA_POSITION_WORLD - VERTEX) * to_camera;
	ruv = UV;
	vc = COLOR;
}

void fragment() {
	float u = ruv.x, v = ruv.y;
	float hw = vc.b * 10.0;
	vec4 F = texture(n_detail, wp.xz / 4.3);
	vec4 G = texture(n_detail, wp.xz / 19.0 + vec2(0.31, 0.77));
	vec3 asph = mix(vec3(0.25, 0.25, 0.24), vec3(0.33, 0.32, 0.30), G.r) * (0.88 + 0.22 * F.b);
	asph *= 1.0 - 0.07 * (1.0 - smoothstep(0.2, 0.9, abs(abs(u) - hw * 0.5)));          // darker wheel paths
	asph = mix(asph, asph * vec3(0.8, 0.8, 0.82), smoothstep(0.6, 0.66, G.a) * 0.8);       // patch repairs
	asph = mix(asph, asph * 1.18 + 0.03, smoothstep(0.66, 0.8, F.a) * 0.4);               // sun-bleached / cracked
	float edge = smoothstep(hw - 1.4, hw, abs(u));
	asph = mix(asph, vec3(0.55, 0.50, 0.42), edge * 0.5 * (0.5 + 0.5 * F.r));            // sand blown onto the edge
	float wear = smoothstep(0.3, 0.7, F.g * 0.7 + G.b * 0.3);
	float centre = (1.0 - smoothstep(0.06, 0.1, abs(u))) * step(fract(v / 9.0), 0.45);
	float edgel = 1.0 - smoothstep(0.05, 0.09, abs(abs(u) - (hw - 0.5)));
	asph = mix(asph, vec3(0.86, 0.84, 0.76), vc.g * max(centre, edgel) * (0.45 + 0.5 * wear));
	float kerb = vc.r * smoothstep(hw - 0.38, hw - 0.32, abs(u));
	asph = mix(asph, vec3(0.64, 0.63, 0.59) * (0.9 + 0.15 * F.r), kerb);
	asph = mix(asph, asph * 0.72, vc.r * (1.0 - smoothstep(hw - 0.6, hw - 0.38, abs(u))) * smoothstep(hw - 1.0, hw - 0.6, abs(u)));  // gutter
	ALBEDO = pow(max(asph, vec3(0.0)), vec3(2.2)) * sa_fog_shade(wp.xz);
	ROUGHNESS = mix(0.84, 0.92, kerb);
}
