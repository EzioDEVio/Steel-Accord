// Steel Accord unit material: PBR paint with baked AO, triplanar mud/grime toward the lower hull, team colour, emissive optics.
shader_type spatial;
uniform vec3 base_color : source_color = vec3(0.2);
uniform float roughness_v = 0.6;
uniform float metallic_v = 0.0;
uniform vec3 emission_c : source_color = vec3(0.0);
uniform bool is_team = false;
uniform bool is_paint = false;
uniform vec3 camo_a : source_color = vec3(0.30, 0.32, 0.20);
uniform vec3 camo_b : source_color = vec3(0.20, 0.21, 0.14);
uniform vec3 camo_c : source_color = vec3(0.40, 0.36, 0.26);
uniform vec3 team_color : source_color = vec3(0.15, 0.45, 0.95);
uniform sampler2D ao_tex : hint_default_white, filter_linear_mipmap;
uniform sampler2D grime : filter_linear_mipmap, repeat_enable;
varying vec3 lp;
varying vec3 ln;
void vertex() { lp = VERTEX; ln = NORMAL; }
void fragment() {
	vec3 bw = abs(ln); bw /= (bw.x + bw.y + bw.z);
	float g = texture(grime, lp.zy * 0.45).r * bw.x + texture(grime, lp.xz * 0.45).r * bw.y + texture(grime, lp.xy * 0.45).r * bw.z;
	float fine = texture(grime, lp.zy * 3.1 + lp.xx * 2.7).r;
	float ao = texture(ao_tex, UV).r;
	vec3 c = is_team ? team_color : base_color;
	if (is_paint) {
		// three-tone disruptive camouflage, projected in model space so it wraps panels consistently
		float k = texture(grime, lp.xz * 0.07 + lp.yy * 0.03).r;
		float k2 = texture(grime, lp.zx * 0.09 + vec2(0.37, 0.11)).r;
		c = camo_a;
		c = mix(c, camo_b, smoothstep(0.52, 0.56, k));
		c = mix(c, camo_c, smoothstep(0.58, 0.62, k2) * (1.0 - smoothstep(0.52, 0.56, k)));
	}
	c *= 0.9 + 0.2 * fine;                                   // paint variation
	float mud = clamp((1.3 - lp.y) * 0.9, 0.0, 1.0) * smoothstep(0.3, 0.7, g);
	float dust = smoothstep(0.55, 0.85, g) * 0.35;
	c = mix(c, vec3(0.29, 0.24, 0.17), clamp(max(mud * 0.85, dust) * float(metallic_v < 0.5), 0.0, 0.85));
	ALBEDO = c * mix(0.45, 1.0, ao);
	ROUGHNESS = clamp(roughness_v + mud * 0.25 - fine * 0.08, 0.05, 1.0);
	METALLIC = metallic_v;
	AO = ao;
	AO_LIGHT_AFFECT = 0.4;
	EMISSION = emission_c;
}
