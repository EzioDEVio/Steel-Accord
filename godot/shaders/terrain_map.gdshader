// Steel Accord - dry-basin terrain material for heightfield maps (sand / rock / gravel / scrub / riverbed / road).
// Weights come from the map's splat.png (R rock, G gravel, B scrub, A riverbed) and the baked road mask; steep slopes
// add rock. Detail is procedural noise generated at runtime, so no third-party textures are shipped. Colours are
// authored in sRGB (same convention as terrain.gdshader). Fog of war is applied like every other world material.
shader_type spatial;
render_mode diffuse_burley;
#include "res://shaders/fog.gdshaderinc"

uniform sampler2D splat : filter_linear, repeat_disable;
uniform sampler2D roads : filter_linear, repeat_disable;
uniform sampler2D n_detail : filter_linear_mipmap, repeat_enable;
uniform sampler2D n_normal : hint_normal, filter_linear_mipmap, repeat_enable;
uniform vec4 map_rect = vec4(-600.0, -600.0, 1200.0, 1200.0);

varying vec3 wpos;
varying vec3 wnrm;

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	wnrm = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
}

void fragment() {
	vec2 p = wpos.xz;
	vec2 uv = (p - map_rect.xy) / map_rect.zw;
	vec4 sp = texture(splat, uv);
	float road = texture(roads, uv).r;
	float slope = 1.0 - clamp(wnrm.y, 0.0, 1.0);
	float d1 = texture(n_detail, p / 3.1).r;
	float d2 = texture(n_detail, p / 17.0).r;
	float d3 = texture(n_detail, p / 61.0).r;
	float d4 = texture(n_detail, p / 230.0).r;

	vec3 sand = mix(vec3(0.56, 0.46, 0.33), vec3(0.66, 0.55, 0.40), d3) * (0.86 + 0.24 * d1);
	sand = mix(sand, vec3(0.66, 0.52, 0.38), smoothstep(0.55, 0.8, d4) * 0.5);       // reddish clay patches
	vec3 rock = mix(vec3(0.40, 0.36, 0.31), vec3(0.55, 0.50, 0.44), d2) * (0.8 + 0.3 * d1);
	rock = mix(rock, vec3(0.62, 0.56, 0.47), smoothstep(0.6, 0.75, fract(wpos.y * 0.18 + d2 * 0.6)) * 0.35); // strata
	vec3 gravel = mix(vec3(0.50, 0.47, 0.42), vec3(0.62, 0.58, 0.51), d1) * (0.9 + 0.15 * d2);
	vec3 scrub = mix(vec3(0.33, 0.33, 0.19), vec3(0.45, 0.43, 0.26), d2);
	scrub = mix(sand, scrub, smoothstep(0.38, 0.62, d1 * 0.6 + d3 * 0.6));
	vec3 river = mix(vec3(0.66, 0.62, 0.54), vec3(0.76, 0.72, 0.64), d2) * (0.92 + 0.1 * d1);
	vec3 dirt = mix(vec3(0.53, 0.48, 0.40), vec3(0.60, 0.55, 0.46), d1);   // compacted gravel track, lighter than shadow
	vec3 ruts = vec3(0.42, 0.37, 0.30);

	float rock_w = clamp(sp.r + smoothstep(0.22, 0.42, slope + (d1 - 0.5) * 0.08), 0.0, 1.0);
	vec3 c = sand;
	c = mix(c, gravel, sp.g);
	c = mix(c, scrub, sp.b);
	c = mix(c, river, sp.a);
	c = mix(c, rock, rock_w);
	float rd = smoothstep(0.2, 0.75, road + (d1 - 0.5) * 0.12);
	c = mix(c, dirt, rd);
	c = mix(c, ruts, smoothstep(0.85, 1.0, road) * smoothstep(0.45, 0.6, d1) * 0.5);

	// map boundary: darken the strip outside the playable rectangle
	vec2 e = min(uv, 1.0 - uv);
	c *= mix(0.45, 1.0, smoothstep(0.0, 0.015, min(e.x, e.y)));

	ALBEDO = pow(max(c, vec3(0.0)), vec3(2.2)) * sa_fog_shade(p);
	ROUGHNESS = mix(0.96, 0.88, rd);
	NORMAL_MAP = mix(texture(n_normal, p / 2.2).rgb, vec3(0.5, 0.5, 1.0), 0.35 + rd * 0.35);
	NORMAL_MAP_DEPTH = 0.7;
}
