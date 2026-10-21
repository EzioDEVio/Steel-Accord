// Steel Accord grass tufts: alpha-cut blades on crossed cards, ground-matched normals, instance-tinted.
shader_type spatial;
render_mode cull_disabled, diffuse_burley;
uniform vec3 c_base : source_color = vec3(0.10, 0.14, 0.05);
uniform vec3 c_tip : source_color = vec3(0.34, 0.37, 0.15);
varying vec3 tint;
void vertex() {
	tint = COLOR.rgb;
	NORMAL = vec3(0.0, 1.0, 0.0);
}
float rnd(float x) { return fract(sin(x * 12.9898) * 43758.5453); }
void fragment() {
	float x = UV.x * 11.0;
	float id = floor(x);
	float fx = fract(x) - 0.5;
	float t = 1.0 - UV.y;                       // 0 at root, 1 at card top
	float h = 0.35 + 0.65 * rnd(id + tint.r * 31.0);
	float lean = t * t * (rnd(id * 1.7) - 0.5) * 1.4;
	float w = 0.48 * (1.0 - t / h);
	if (t > h || abs(fx - lean) > w) discard;
	vec3 c = mix(c_base, c_tip, smoothstep(0.0, 1.0, t / h)) * tint;
	ALBEDO = c * mix(0.5, 1.0, t);
	ROUGHNESS = 0.85;
	SPECULAR = 0.3;
	BACKLIGHT = c * 0.4;
}
