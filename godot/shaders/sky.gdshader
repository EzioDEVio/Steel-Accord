// Steel Accord sky: atmospheric gradient, sun disc + halo, two-layer cumulus field.
shader_type sky;
uniform sampler2D cloud_a : filter_linear_mipmap, repeat_enable;
uniform sampler2D cloud_b : filter_linear_mipmap, repeat_enable;
uniform vec3 zenith = vec3(0.12, 0.27, 0.58);
uniform vec3 horizon = vec3(0.55, 0.64, 0.74);
void sky() {
	vec3 d = EYEDIR;
	float h = max(d.y, 0.0);
	vec3 col = mix(horizon, zenith, pow(h, 0.45));
	if (d.y < 0.0) col = horizon * 0.85;
	float sd = max(dot(d, LIGHT0_DIRECTION), 0.0);
	if (d.y > 0.0) {
		vec2 uv = d.xz / (d.y + 0.08);
		float c = texture(cloud_a, uv * 0.11 + vec2(0.3, 0.1)).r * 0.65 + texture(cloud_b, uv * 0.37).r * 0.35;
		float cov = smoothstep(0.50, 0.68, c) * smoothstep(0.0, 0.18, d.y);
		float shade = smoothstep(0.5, 0.85, c);
		vec3 cc = mix(vec3(1.0, 0.98, 0.95) * 1.25, vec3(0.62, 0.66, 0.72), shade * 0.8);
		cc += LIGHT0_COLOR * pow(sd, 6.0) * 0.4;
		col = mix(col, cc, cov * 0.92);
	}
	col += LIGHT0_COLOR * LIGHT0_ENERGY * (pow(sd, 2200.0) * 40.0 + pow(sd, 12.0) * 0.12);
	COLOR = col;
}
