// Steel Accord terrain: macro height noise, slope/noise-driven blend of grass, dry earth and rock, plus a dirt track.
shader_type spatial;
render_mode diffuse_burley;
uniform sampler2D n_macro : filter_linear_mipmap, repeat_enable;
uniform sampler2D n_detail : filter_linear_mipmap, repeat_enable;
uniform sampler2D n_normal : hint_normal, filter_linear_mipmap, repeat_enable;
uniform float height = 9.0;
uniform float flat_radius = 34.0;
varying vec3 wpos;
varying float slope;

float hgt(vec2 p) {
	float f = smoothstep(flat_radius, flat_radius + 40.0, length(p));
	return (texture(n_macro, p / 260.0).r - 0.45) * height * f + texture(n_macro, p / 37.0).r * 0.35;
}
void vertex() {
	vec3 w = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	float e = 0.8;
	float h0 = hgt(w.xz);
	VERTEX.y += h0;
	float hx = hgt(w.xz + vec2(e, 0.0)) - hgt(w.xz - vec2(e, 0.0));
	float hz = hgt(w.xz + vec2(0.0, e)) - hgt(w.xz - vec2(0.0, e));
	NORMAL = normalize(vec3(-hx, 2.0 * e, -hz));
	wpos = w + vec3(0.0, h0, 0.0);
	slope = 1.0 - NORMAL.y;
}
void fragment() {
	vec2 p = wpos.xz;
	float d1 = texture(n_detail, p / 6.0).r;
	float d2 = texture(n_detail, p / 23.0).r;
	float m = texture(n_macro, p / 90.0).r;
	vec3 grass = mix(vec3(0.13, 0.19, 0.07), vec3(0.27, 0.31, 0.11), d2);
	grass *= 0.85 + 0.3 * d1;
	vec3 earth = mix(vec3(0.24, 0.19, 0.13), vec3(0.34, 0.28, 0.19), d1);
	vec3 rock = mix(vec3(0.30, 0.29, 0.27), vec3(0.45, 0.43, 0.40), d1);
	float earth_w = smoothstep(0.60, 0.72, m + (d2 - 0.5) * 0.25);
	// dirt track running through the centre
	float road = 1.0 - smoothstep(4.0, 6.5 + d2 * 2.5, abs(p.x + sin(p.y * 0.035) * 9.0));
	vec3 c = mix(grass, earth, max(earth_w, road * 0.92));
	c = mix(c, rock, smoothstep(0.18, 0.32, slope + (d1 - 0.5) * 0.1));
	ALBEDO = c;
	ROUGHNESS = 0.92 - road * 0.1;
	NORMAL_MAP = texture(n_normal, p / 5.0).rgb;
	NORMAL_MAP_DEPTH = 0.9;
}
