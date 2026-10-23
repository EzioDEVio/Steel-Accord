// Steel Accord - dry-basin terrain material for heightfield maps (sand / rock / gravel / scrub / riverbed / road).
// Weights come from the map's splat.png (R rock, G gravel, B scrub, A riverbed) and the baked road mask; steep slopes
// add rock. Detail is procedural noise generated at runtime (terrain_map.gd), so no third-party textures are shipped.
// Colours are authored in sRGB (same convention as terrain.gdshader). Fog of war is applied like every other world
// material.
//
// Anti-tiling (docs/TERRAIN_TILING.md):
//  * n_macro is ONE unique (non-repeating) noise texture stretched over the whole map: it carries every variation
//    larger than ~10 m (brightness/hue drift, clay and dust fields, scrub clusters, splat-border warp).
//  * n_detail is a small seamless tile (4 noise layers in RGBA) for 0.2-6 m detail. The coarse sample uses hex-tile
//    blending (Mikkelsen 2022): every cell of a triangle grid gets a random offset + rotation and the three cells are
//    blended with variance-preserving weights, so the tile has no visible period. The fine grain is a plain, rotated
//    tile (its period is a few pixels wide at RTS distances).
//  * slope / height tint: steep ground darkens, low flat basin floors get a pale dust film.
shader_type spatial;
render_mode diffuse_burley;
#include "res://shaders/fog.gdshaderinc"

uniform sampler2D splat : filter_linear_mipmap, repeat_disable;     // mipmapped copy (rendering only)
uniform sampler2D roads : filter_linear, repeat_disable;
uniform sampler2D n_macro : filter_linear, repeat_disable;          // R ~350 m, G ~100 m, B ~30 m, A ~60 m (warp)
uniform sampler2D n_detail : filter_linear_mipmap, repeat_enable;   // R ~6 m, G ~2 m, B ~0.7 m, A ~3 m  (at 19 m/tile)
uniform sampler2D n_normal : hint_normal, filter_linear_mipmap, repeat_enable;
uniform sampler2D hmap : filter_linear, repeat_disable;            // the height grid itself (R16F), for shading normals
uniform vec4 hmap_info = vec4(-600.0, -600.0, 2.0, 601.0);          // origin x, origin z, step, samples per side
uniform float shade_smooth = 0.8;                                   // 0 = mesh normals, 1 = smoothed height normals
uniform vec4 map_rect = vec4(-600.0, -600.0, 1200.0, 1200.0);
uniform float detail_tile_m = 19.0;
uniform float grain_tile_m = 4.3;

varying vec3 wpos;
varying vec3 wnrm;

void vertex() {
	wpos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	wnrm = normalize((MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz);
}

vec2 hash2(vec2 c) {
	vec3 p3 = fract(vec3(c.xyx) * vec3(0.1031, 0.1030, 0.0973));
	p3 += dot(p3, p3.yzx + 33.33);
	return fract((p3.xx + p3.yz) * p3.zy);
}

// One tap of the tile with a per-cell random rotation and offset (explicit gradients: no mip seams at cell edges).
vec4 cell_tap(vec2 uv, vec2 dx, vec2 dy, vec2 cell) {
	vec2 h = hash2(cell);
	float a = h.x * 6.2831853;
	mat2 r = mat2(vec2(cos(a), sin(a)), vec2(-sin(a), cos(a)));
	return textureGrad(n_detail, r * uv + h * 7.31, r * dx, r * dy);
}

// Hex-tile sampling: triangle grid in skewed space, three randomised taps, variance-preserving blend.
vec4 hex_detail(vec2 uv) {
	vec2 dx = dFdx(uv), dy = dFdy(uv);
	vec2 st = uv * 3.4641016;   // 2*sqrt(3): about one hex per tile
	vec2 sk = vec2(st.x, -0.57735027 * st.x + 1.15470054 * st.y);
	vec2 base = floor(sk);
	vec3 t = vec3(fract(sk), 0.0);
	t.z = 1.0 - t.x - t.y;
	float s = step(0.0, -t.z);
	float s2 = 2.0 * s - 1.0;
	vec3 w = vec3(-t.z * s2, s - t.y * s2, s - t.x * s2);
	vec4 a = cell_tap(uv, dx, dy, base + vec2(s, s));
	vec4 b = cell_tap(uv, dx, dy, base + vec2(s, 1.0 - s));
	vec4 c = cell_tap(uv, dx, dy, base + vec2(1.0 - s, s));
	w = w * w * w;                        // sharpen the blend a little (fewer triple-mixed pixels)
	w /= (w.x + w.y + w.z);
	vec4 m = a * w.x + b * w.y + c * w.z;
	// keep the contrast of a single tap (linear blends of noise lose variance toward the cell corners)
	return (m - 0.5) / sqrt(dot(w, w)) * 0.92 + 0.5;
}

float hgt(vec2 p) {
	return texture(hmap, ((p - hmap_info.xy) / hmap_info.z + 0.5) / hmap_info.w).r;
}

// World normal of the bilinear height grid differenced over +-d metres. The benches on the anticline flanks are
// 2-6 m steps sampled on a 2 m grid; lit per vertex they alias into a regular field of triangular facets. This
// normal (and the slope from it) reads them as soft bands instead. Geometry and gameplay heights are unchanged.
// Returns xyz = normal, w = mean height of the taps (a smoothed height for the strata bands).
vec4 smooth_normal(vec2 p, float d) {
	float e = hgt(p + vec2(d, 0.0)), w = hgt(p - vec2(d, 0.0));
	float s = hgt(p + vec2(0.0, d)), n = hgt(p - vec2(0.0, d));
	return vec4(normalize(vec3(w - e, 2.0 * d, n - s)), (e + w + s + n) * 0.25);
}

// Softens a splat weight into a noisy, patchy border instead of a uniform cross-fade.
float breakup(float w, float n) {
	return smoothstep(0.12, 0.88, w + (n - 0.5) * 0.55) * smoothstep(0.0, 0.06, w);
}

void fragment() {
	vec2 p = wpos.xz;
	vec2 uv = (p - map_rect.xy) / map_rect.zw;
	vec4 M = texture(n_macro, uv);                           // unique over the map
	vec4 H = clamp(hex_detail(p / detail_tile_m), 0.0, 1.0); // non-repeating 0.5-6 m detail
	const mat2 GR = mat2(vec2(0.8, 0.6), vec2(-0.6, 0.8));
	vec4 F = texture(n_detail, GR * p / grain_tile_m);        // fine grain (0.1-0.5 m)
	float dist = length(VERTEX);
	float fine_amt = 1.0 - smoothstep(90.0, 320.0, dist) * 0.6;

	// splat with a warped lookup (+-3 m) so material borders do not follow the 2 m splat raster
	vec2 warp = (vec2(M.a, M.b) - 0.5) * 5.0 + (H.rg - 0.5) * 2.0;
	vec4 sp = textureLod(splat, uv + warp / map_rect.zw, 0.0);
	// rock is painted on every 2-6 m bench riser as 1-2 px lines; at full resolution they alias into a regular field of
	// facets, so the colour reads rock from a blurred mip (strata from the smoothed height draw the bands instead)
	sp.r = mix(sp.r, textureLod(splat, uv + warp / map_rect.zw, 1.6).r, 0.8);
	float road = texture(roads, uv).r;
	vec4 s3 = smooth_normal(p, 3.0), s8 = smooth_normal(p, 8.0);   // the wide one averages across a whole bench
	vec3 sn = normalize(s3.xyz * 0.35 + s8.xyz * 0.65);
	float hs = mix(s3.w, s8.w, 0.6);                         // smoothed height: strata follow contours, not facets
	vec3 nw = normalize(mix(normalize(wnrm), sn, shade_smooth));
	float slope = 1.0 - clamp(nw.y, 0.0, 1.0);
	float grain = mix(0.5, F.b, fine_amt);
	float mid = H.r * 0.55 + M.b * 0.45;                     // 2-30 m mottling

	// --- sand: drifts between two sand tones on 30-100 m fields, clay patches, pale dust in flat low basins
	vec3 sand = mix(vec3(0.56, 0.46, 0.33), vec3(0.66, 0.55, 0.40), clamp(M.g * 0.65 + mid * 0.55 - 0.1, 0.0, 1.0));
	sand *= 0.88 + 0.22 * mix(H.g, grain, 0.5);
	sand = mix(sand, vec3(0.66, 0.52, 0.38), smoothstep(0.58, 0.8, M.r * 0.6 + M.g * 0.25 + H.r * 0.2) * 0.55);
	sand = mix(sand, sand * vec3(0.86, 0.85, 0.84), smoothstep(0.6, 0.85, M.b * 0.7 + H.a * 0.4) * 0.6);  // darker pavement
	// --- rock: tone on 6-30 m, strata following height but warped so they are not ruler-straight
	vec3 rock = mix(vec3(0.40, 0.36, 0.31), vec3(0.55, 0.50, 0.44), clamp(H.r * 0.6 + M.b * 0.5 - 0.05, 0.0, 1.0));
	rock *= 0.8 + 0.3 * mix(H.b, grain, 0.5);
	rock = mix(rock, vec3(0.62, 0.56, 0.47), smoothstep(0.6, 0.75, fract(hs * 0.18 + H.g * 0.5 + M.a * 1.6)) * 0.35);
	rock *= mix(1.0, 0.8, smoothstep(0.3, 0.75, slope));     // steep faces darker
	// --- gravel: pebbly grain plus 2-6 m clusters of darker / lighter stone
	vec3 gravel = mix(vec3(0.50, 0.47, 0.42), vec3(0.62, 0.58, 0.51), clamp(grain * 0.6 + H.g * 0.5 - 0.05, 0.0, 1.0));
	gravel *= 0.9 + 0.15 * H.a + 0.06 * (M.b - 0.5);
	// --- scrub: olive bushes in clusters (cells) whose density varies on 30-100 m
	vec3 scrub = mix(vec3(0.33, 0.33, 0.19), vec3(0.45, 0.43, 0.26), H.g);
	scrub = mix(sand, scrub, smoothstep(0.42, 0.66, H.a * 0.55 + grain * 0.2 + M.b * 0.35 + M.g * 0.15));
	// --- dry riverbed: pale silt with darker damp streaks
	vec3 river = mix(vec3(0.66, 0.62, 0.54), vec3(0.76, 0.72, 0.64), H.r) * (0.92 + 0.1 * grain);
	river *= mix(1.0, 0.9, smoothstep(0.6, 0.8, H.b * 0.6 + M.a * 0.4));
	vec3 dirt = mix(vec3(0.53, 0.48, 0.40), vec3(0.60, 0.55, 0.46), mix(H.b, grain, 0.5));   // compacted gravel track
	vec3 ruts = vec3(0.42, 0.37, 0.30);

	float rock_w = clamp(breakup(sp.r, H.r) + smoothstep(0.22, 0.42, slope + (H.b - 0.5) * 0.08), 0.0, 1.0);
	vec3 c = sand;
	c = mix(c, gravel, breakup(sp.g, H.g * 0.6 + M.b * 0.4));
	c = mix(c, scrub, breakup(sp.b, H.a * 0.6 + M.g * 0.4));
	c = mix(c, river, breakup(sp.a, H.r * 0.7 + M.a * 0.3));
	c = mix(c, rock, rock_w);

	// low, flat basin floors: thin pale dust film in broad irregular fields
	float flat_low = (1.0 - smoothstep(0.04, 0.16, slope)) * (1.0 - smoothstep(4.0, 12.0, wpos.y));
	c = mix(c, vec3(0.74, 0.66, 0.54), flat_low * smoothstep(0.42, 0.75, M.g * 0.7 + H.r * 0.3) * 0.32 * (1.0 - rock_w));
	// map-scale brightness / hue drift (+-11 %), so no two hillsides read identical
	c *= 0.89 + 0.22 * M.r;
	c = mix(c, c * vec3(1.04, 0.99, 0.93), smoothstep(0.35, 0.75, M.a) * 0.6);
	c *= mix(1.0, 0.9, smoothstep(0.35, 0.85, slope));        // shade steep ground slightly (rough AO)

	float rd = smoothstep(0.2, 0.75, road + (H.b - 0.5) * 0.12 + (grain - 0.5) * 0.06);
	c = mix(c, dirt, rd);
	c = mix(c, ruts, smoothstep(0.85, 1.0, road) * smoothstep(0.45, 0.6, mix(H.b, F.b, 0.5)) * 0.5);

	// map boundary: darken the strip outside the playable rectangle
	vec2 e = min(uv, 1.0 - uv);
	c *= mix(0.45, 1.0, smoothstep(0.0, 0.015, min(e.x, e.y)));

	NORMAL = normalize((VIEW_MATRIX * vec4(nw, 0.0)).xyz);
	ALBEDO = pow(max(c, vec3(0.0)), vec3(2.2)) * sa_fog_shade(p);
	ROUGHNESS = mix(0.96, 0.88, rd);
	// two decorrelated normal taps (different scale and rotation) so the bump pattern has no short period
	vec3 n1 = texture(n_normal, p / 2.2).rgb;
	vec3 n2 = texture(n_normal, GR * p / 6.7 + vec2(0.37, 0.61)).rgb;
	vec3 nm = normalize(vec3((n1.xy - 0.5) + (n2.xy - 0.5) * 0.8, 1.0)) * 0.5 + 0.5;
	NORMAL_MAP = mix(nm, vec3(0.5, 0.5, 1.0), 0.35 + rd * 0.35);
	NORMAL_MAP_DEPTH = 0.7;
}
