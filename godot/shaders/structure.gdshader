// Steel Accord - structure impostor: the building concept art as a camera-facing card.
// Construction: pixels above the build line are replaced by a scaffold lattice over a faint blueprint ghost;
// a warm band marks the line as it rises. Fog of war dims the card like the terrain under it.
shader_type spatial;
render_mode unshaded, cull_disabled, depth_draw_opaque;
#include "res://shaders/fog.gdshaderinc"

uniform sampler2D art : source_color, filter_linear_mipmap;
uniform float progress = 1.0;        // 0..1 construction
uniform vec3 team_color : source_color = vec3(0.2, 0.4, 0.9);
uniform float team_tint = 0.0;
uniform float burnt = 0.0;
uniform float highlight = 0.0;
uniform float ghost = 0.0;           // placement preview: 1 = translucent
uniform vec3 ghost_color : source_color = vec3(0.4, 1.0, 0.5);
uniform vec2 art_px = vec2(768.0, 512.0);
uniform vec2 fog_xz = vec2(0.0);

void vertex() {
	// spherical billboard around the node origin; local XY are camera right / up
	MODELVIEW_MATRIX = VIEW_MATRIX * mat4(INV_VIEW_MATRIX[0], INV_VIEW_MATRIX[1], INV_VIEW_MATRIX[2], MODEL_MATRIX[3]);
	MODELVIEW_NORMAL_MATRIX = mat3(MODELVIEW_MATRIX);
}

void fragment() {
	vec4 c = texture(art, UV);
	if (c.a < 0.45) discard;
	vec3 col = c.rgb;
	float line = 1.0 - progress;             // UV.y below this (higher on the card) is not built yet
	if (ghost > 0.5) {
		col = mix(col * 0.6, ghost_color, 0.55);
		if (mod(floor(FRAGCOORD.x) + floor(FRAGCOORD.y), 2.0) < 0.5) discard;   // screen-door translucency
	} else if (UV.y < line) {
		vec2 px = UV * art_px;
		float gx = step(fract(px.x / 34.0), 0.10);
		float gy = step(fract(px.y / 28.0), 0.12);
		float diag = step(fract((px.x + px.y) / 48.0), 0.06);
		float lattice = max(max(gx, gy), diag);
		if (lattice < 0.5) {
			// blueprint ghost of the finished building
			col = mix(col, vec3(0.45, 0.6, 0.75), 0.6) * 0.8;
			if (mod(floor(FRAGCOORD.x), 3.0) + mod(floor(FRAGCOORD.y), 3.0) > 0.5) discard;
		} else {
			col = vec3(0.72, 0.62, 0.38) * (0.75 + 0.25 * gy);
		}
	}
	float band = 1.0 - smoothstep(0.0, 0.02, abs(UV.y - line));
	col = mix(col, vec3(1.0, 0.75, 0.3), band * step(0.001, line) * 0.8);
	col = mix(col, team_color, team_tint);
	col = mix(col, vec3(0.05, 0.045, 0.04), burnt * 0.85);
	col += vec3(0.12) * highlight;
	ALBEDO = col * sa_fog_shade(fog_xz);
}
