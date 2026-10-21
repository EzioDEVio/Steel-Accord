// Steel Accord terrain v2: gentle hills, grass with dry/lush variation, rutted dirt road, rock on slopes.
shader_type spatial;
render_mode diffuse_burley;
#include "res://shaders/noise.gdshaderinc"
uniform sampler2D n_macro : filter_linear_mipmap, repeat_enable;
uniform sampler2D n_detail : filter_linear_mipmap, repeat_enable;
uniform sampler2D n_normal : hint_normal, filter_linear_mipmap, repeat_enable;
uniform float height = 14.0;
uniform vec2 flat_center = vec2(0.0, -20.0);
uniform float flat_radius = 60.0;
varying vec3 wpos;
varying float slope;

float road_center(float z) { return -sin(z * 0.035) * 9.0; }
float hgt(vec2 p) {
	float f = smoothstep(flat_radius, flat_radius + 90.0, length(p - flat_center));
	float road = 1.0 - smoothstep(4.0, 10.0, abs(p.x - road_center(p.y)));
	return (texture(n_macro, p / 330.0).r - 0.4) * height * f * (1.0 - road * 0.8);
}
void vertex() {
	vec3 w = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	float e = 1.0;
	float h0 = hgt(w.xz);
	VERTEX.y += h0;
	NORMAL = normalize(vec3(hgt(w.xz - vec2(e, 0)) - hgt(w.xz + vec2(e, 0)), 2.0 * e, hgt(w.xz - vec2(0, e)) - hgt(w.xz + vec2(0, e))));
	wpos = w + vec3(0, h0, 0);
	slope = 1.0 - NORMAL.y;
}
void fragment() {
	vec2 p = wpos.xz;
	float d1 = texture(n_detail, p / 3.1).r;
	float d2 = texture(n_detail, p / 17.0).r;
	float d3 = texture(n_detail, p / 61.0).r;
	float m = texture(n_macro, p / 140.0).r;
	// grass: lush / mid / dry, varied at three scales
	vec3 lush = vec3(0.10, 0.16, 0.05), mid = vec3(0.19, 0.23, 0.08), dry = vec3(0.36, 0.33, 0.17);
	vec3 grass = mix(lush, mid, smoothstep(0.3, 0.6, d3));
	grass = mix(grass, dry, smoothstep(0.55, 0.8, m + (d2 - 0.5) * 0.3));
	grass *= 0.8 + 0.4 * d1;
	// road: compacted dirt, gravel speckle, two wheel/track ruts, worn verges
	float dist = abs(p.x - road_center(p.y));
	float road = 1.0 - smoothstep(2.8, 3.7 + d2 * 1.2, dist);
	float rut = (1.0 - smoothstep(0.2, 0.55, abs(dist - 1.3))) * road;
	float verge = (1.0 - smoothstep(3.5, 6.5 + d2 * 3.0, dist)) * (1.0 - road);
	vec3 dirt = mix(vec3(0.23, 0.205, 0.165), vec3(0.31, 0.28, 0.22), d1);
	dirt = mix(dirt, vec3(0.36, 0.34, 0.30), smoothstep(0.72, 0.8, texture(n_detail, p * 1.7).r) * 0.6);
	vec3 rutc = vec3(0.13, 0.10, 0.07);
	vec3 c = mix(grass, mix(grass, dirt, 0.55), verge * smoothstep(0.35, 0.7, d1));
	c = mix(c, dirt, road);
	c = mix(c, rutc, rut * 0.8);
	vec3 rock = mix(vec3(0.33, 0.31, 0.28), vec3(0.47, 0.45, 0.41), d1);
	c = mix(c, rock, smoothstep(0.2, 0.35, slope + (d1 - 0.5) * 0.1));
	ALBEDO = pow(max(c, vec3(0.0)), vec3(2.2));  // authored in sRGB
	ROUGHNESS = mix(0.96, 0.85, road) - rut * 0.25;
	NORMAL_MAP = mix(texture(n_normal, p / 2.2).rgb, vec3(0.5, 0.5, 1.0), 0.45 + road * 0.3);
	NORMAL_MAP_DEPTH = 0.6;
}
