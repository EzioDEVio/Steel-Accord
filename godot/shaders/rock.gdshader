// Steel Accord rock: triplanar procedural stone with lichen on upward faces.
shader_type spatial;
#include "res://shaders/fog.gdshaderinc"
#include "res://shaders/noise.gdshaderinc"
uniform vec3 tone : source_color = vec3(0.34, 0.33, 0.30);
varying vec3 wp;
varying vec3 wn;
void vertex() { wp = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz; wn = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz); }
void fragment() {
	float n = sa_fbm(wp * 1.3);
	float f = sa_fbm(wp * 6.0);
	vec3 c = tone * (0.7 + 0.5 * n) * (0.85 + 0.3 * f);
	float moss = smoothstep(0.55, 0.9, wn.y) * smoothstep(0.4, 0.6, sa_fbm(wp * 2.2 + 5.0));
	c = mix(c, vec3(0.20, 0.24, 0.10), moss * 0.85);
	float dirt = 1.0 - smoothstep(0.0, 0.5, wp.y);
	c = mix(c, vec3(0.30, 0.25, 0.18), dirt * 0.6);
	ALBEDO = (pow(max(c, vec3(0.0)), vec3(2.2))) * sa_fog_shade(wp.xz);  // authored in sRGB
	ROUGHNESS = 0.9;
}
