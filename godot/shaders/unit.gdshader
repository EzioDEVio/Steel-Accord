// Steel Accord unit material v2.
// kind: 0 metal, 1 camouflaged paint, 2 team marking, 3 track/rubber, 4 decal/canvas, 5 glass
shader_type spatial;
#include "res://shaders/noise.gdshaderinc"
uniform vec3 base_color : source_color = vec3(0.2);
uniform float roughness_v = 0.6;
uniform float metallic_v = 0.0;
uniform int kind = 0;
uniform vec3 team_color : source_color = vec3(0.1, 0.3, 0.75);
uniform vec3 camo_offset = vec3(0.0);
uniform vec3 camo_green : source_color = vec3(0.26, 0.30, 0.17);
uniform vec3 camo_brown : source_color = vec3(0.27, 0.21, 0.14);
uniform vec3 camo_black : source_color = vec3(0.08, 0.08, 0.07);
uniform vec3 dust_color : source_color = vec3(0.50, 0.43, 0.32);
uniform sampler2D ao_tex : hint_default_white, filter_linear_mipmap;
varying vec3 lp;
varying vec3 ln;
void vertex() { lp = VERTEX; ln = NORMAL; }

float band(float v, float t) { float w = max(fwidth(v) * 1.2, 0.004); return smoothstep(t - w, t + w, v); }

void fragment() {
	float ao = texture(ao_tex, UV).r;
	vec3 c = base_color;
	float rough = roughness_v;
	if (kind == 1) {
		// three-tone disruptive pattern: large domain-warped 3D noise, crisp edges, no UV stretching
		vec3 q = lp * 0.36 + camo_offset;
		q += vec3(sa_fbm(q * 1.6), sa_fbm(q * 1.6 + 3.1), sa_fbm(q * 1.6 + 6.7)) * 0.9;
		float n1 = sa_fbm(q);
		float n2 = sa_fbm(q * 1.25 + vec3(11.3));
		c = camo_green;
		c = mix(c, camo_brown, band(n1, 0.57));
		c = mix(c, camo_black, band(n2, 0.60) * (1.0 - band(n1, 0.57) * 0.6));
		// paint chips exposing dark primer on edges of the pattern noise
		float chip = band(sa_fbm(lp * 14.0), 0.74);
		c = mix(c, vec3(0.012), chip * 0.7);
		rough = mix(rough, 0.45, chip);
	} else if (kind == 2) {
		c = team_color * 0.7;
		rough = 0.7;
	}
	if (kind != 5) {
		// dust: heavy toward the running gear, light film on upward faces
		float low = 1.0 - smoothstep(0.05, 0.95, lp.y + (sa_fbm(lp * 2.5) - 0.5) * 0.6);
		float top = smoothstep(0.65, 0.95, ln.y) * smoothstep(0.45, 0.75, sa_fbm(lp * 1.8 + 4.0));
		float amt = kind == 3 ? 0.3 + low * 0.35 : low * 0.45 + top * 0.25;
		amt *= 0.75 + 0.5 * sa_noise(lp * 9.0);
		c = mix(c, dust_color, clamp(amt, 0.0, 0.85));
		rough = mix(rough, 0.95, clamp(amt, 0.0, 1.0));
	}
	ALBEDO = c * mix(0.4, 1.0, ao);
	ROUGHNESS = rough;
	METALLIC = kind == 5 ? 0.3 : metallic_v;
	SPECULAR = kind == 5 ? 0.8 : 0.45;
	AO = ao;
	AO_LIGHT_AFFECT = 0.5;
}
