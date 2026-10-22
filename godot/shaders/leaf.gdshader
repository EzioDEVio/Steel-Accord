// Steel Accord foliage: clumped leaf masses via 3D noise (dark gaps, lit clusters), normal jitter, backlight.
shader_type spatial;
#include "res://shaders/fog.gdshaderinc"
#include "res://shaders/noise.gdshaderinc"
uniform vec3 tint : source_color = vec3(1.0);
varying vec3 lp;
varying vec3 fwp;
void vertex() { lp = VERTEX; fwp = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz; }
void fragment() {
	float clump = sa_fbm(lp * 3.2);
	float leaf = sa_noise(lp * 22.0);
	vec3 dark = vec3(0.05, 0.08, 0.03), lit = vec3(0.22, 0.30, 0.09), tip = vec3(0.36, 0.40, 0.14);
	vec3 c = mix(dark, lit, smoothstep(0.35, 0.65, clump));
	c = mix(c, tip, smoothstep(0.7, 0.9, leaf) * smoothstep(0.45, 0.7, clump));
	ALBEDO = (pow(max(c * tint, vec3(0.0)), vec3(2.2))) * sa_fog_shade(fwp.xz);  // authored in sRGB
	NORMAL = normalize(NORMAL + (vec3(sa_noise(lp * 15.0), sa_noise(lp * 15.0 + 3.0), sa_noise(lp * 15.0 + 7.0)) - 0.5) * 0.9);
	ROUGHNESS = 0.8;
	BACKLIGHT = pow(c, vec3(2.2)) * 0.5;
	AO = smoothstep(0.25, 0.6, clump);
}
