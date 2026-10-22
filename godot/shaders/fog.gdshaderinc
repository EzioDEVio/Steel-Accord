// Steel Accord fog of war (driven by Battle: 1 = visible, ~0.43 = explored, 0 = never seen).
global uniform sampler2D fog_tex : filter_linear;
global uniform vec4 fog_rect;
global uniform float fog_on;
float sa_fog(vec2 p) {
	if (fog_on < 0.5) return 1.0;
	vec2 uv = (p - fog_rect.xy) / fog_rect.zw;
	if (uv.x < 0.0 || uv.y < 0.0 || uv.x > 1.0 || uv.y > 1.0) return 0.0;
	return texture(fog_tex, uv).r;
}
// albedo multiplier: clear in view, dimmed when explored, near-black when unexplored
float sa_fog_shade(vec2 p) { return mix(0.06, 1.0, smoothstep(0.0, 1.0, sa_fog(p))); }
