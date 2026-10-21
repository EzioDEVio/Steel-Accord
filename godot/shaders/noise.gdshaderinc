// Steel Accord shared procedural noise (3D value noise + fbm).
float sa_hash(vec3 p) { p = fract(p * 0.3183099 + vec3(0.1, 0.2, 0.3)); p *= 17.0; return fract(p.x * p.y * p.z * (p.x + p.y + p.z)); }
float sa_noise(vec3 x) {
	vec3 i = floor(x); vec3 f = fract(x); f = f * f * (3.0 - 2.0 * f);
	return mix(mix(mix(sa_hash(i), sa_hash(i + vec3(1, 0, 0)), f.x), mix(sa_hash(i + vec3(0, 1, 0)), sa_hash(i + vec3(1, 1, 0)), f.x), f.y),
	           mix(mix(sa_hash(i + vec3(0, 0, 1)), sa_hash(i + vec3(1, 0, 1)), f.x), mix(sa_hash(i + vec3(0, 1, 1)), sa_hash(i + vec3(1, 1, 1)), f.x), f.y), f.z);
}
float sa_fbm(vec3 p) { float a = 0.5, s = 0.0; for (int i = 0; i < 4; i++) { s += a * sa_noise(p); p *= 2.03; a *= 0.5; } return s; }
