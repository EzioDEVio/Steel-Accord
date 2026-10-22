"""Steel Accord - converts the client's source sound clips into game-ready mono OGG files.

usage: python3 -I tools/audio/prepare_audio.py <source_dir> <out_dir> <manifest_json>
Each entry: trim window, peak normalisation, short fades, and (for loops) an equal-power crossfade
of the tail into the head so the clip repeats without a click. Deterministic; re-run to regenerate.
"""
import hashlib, json, subprocess, sys, os
import numpy as np

SR = 44100
# id: (source file, start s, end s, peak dBFS, loop, use, provenance)
PIX = "Pixabay sound effects (client confirmed 2026-10-22, downloaded from pixabay.com/sound-effects); Pixabay Content License. Record each item page URL + uploader before release"
UNK = PIX
CLIPS = {
    "a10_cannon":      ("a-10-warthog-brrrt.mp3", 0.0, None, -2.0, False, "A-10 GAU-style cannon burst", UNK),
    "rifle_burst":     ("assault-rifle-ar15-1.mp3", 0.40, 1.60, -4.0, False, "infantry rifle fire", UNK),
    "mg_burst":        ("machine-gun-bursts-gun-sounds-309721.mp3", 0.0, 1.38, -4.0, False, "vehicle/heli machine gun", PIX),
    "explosion_big":   ("massive-explosion-2-397983.mp3", 0.0, 3.2, -1.0, False, "unit destroyed / bomb impact", PIX),
    "rocket_launch":   ("rocket-launcher-307512.mp3", 0.0, None, -3.0, False, "missile / rocket launch", PIX),
    "sam_launch":      ("base-defense-missle-launching.mp3", 0.0, None, -3.0, False, "base defence missile launch", UNK),
    "bomb_fall":       ("falling-bomb-41038.mp3", 0.0, None, -4.0, False, "falling bomb whistle", PIX),
    "jet_flyby":       ("fighter-jet-overhead-355468.mp3", 2.1, 10.6, -2.0, False, "jet pass overhead", PIX),
    "jet_takeoff":     ("f-16-launch-75873.mp3", 0.0, 15.3, -3.0, False, "jet take-off roll (f-15 file is byte-identical)", UNK),
    "heli_loop":       ("helicopter-sound-8d-372463.mp3", 0.0, 9.7, -5.0, True, "helicopter rotor loop (8D stereo downmixed)", PIX),
    "tank_loop":       ("tank-moving-143104.mp3", 0.25, 10.0, -5.0, True, "tracked vehicle engine/track loop", PIX),
    "construction_loop": ("base-building-and-construction-work-26897.mp3", 0.4, 29.6, -6.0, True, "building under construction", PIX),
    "radar_ping":      ("base-radar-ping-306440.mp3", 0.0, None, -6.0, False, "radar / UI ping", PIX),
}


def decode(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         check=True, capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32).copy()


def main(src, out, man):
    os.makedirs(out, exist_ok=True)
    entries = {}
    for cid, (fn, a, b, peak, loop, use, prov) in CLIPS.items():
        p = os.path.join(src, fn)
        x = decode(p)
        i0 = int(a * SR); i1 = len(x) if b is None else min(len(x), int(b * SR))
        x = x[i0:i1]
        x = x - x.mean()
        if loop:
            d = int(0.6 * SR)
            t = np.linspace(0, np.pi / 2, d)
            head, tail = x[:d], x[-d:]
            body = x[d:-d]
            mixed = tail * np.cos(t) + head * np.sin(t)
            x = np.concatenate([body, mixed])   # end flows into the start of body
        else:
            f = int(0.008 * SR); x[:f] *= np.linspace(0, 1, f)
            g = int(0.12 * SR); x[-g:] *= np.linspace(1, 0, g)
        x = x / max(1e-6, np.abs(x).max()) * (10 ** (peak / 20))
        dst = os.path.join(out, cid + ".ogg")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-",
                        "-c:a", "libvorbis", "-q:a", "5", "-map_metadata", "-1", "-fflags", "+bitexact", dst],
                       input=x.astype(np.float32).tobytes(), check=True)
        entries[cid] = {"file": "res://assets/audio/%s.ogg" % cid, "loop": loop, "use": use,
                        "source_file": fn, "source_sha256": hashlib.sha256(open(p, "rb").read()).hexdigest(),
                        "window_s": [a, b], "duration_s": round(len(x) / SR, 2), "provenance": prov,
                        "status": "dev_ok; release needs per-item page URL",
                        "edits": "mono downmix 44.1 kHz, trim, DC removal, peak normalise, fades/loop crossfade, OGG q5"}
    json.dump({"generated_by": "tools/audio/prepare_audio.py", "clips": entries}, open(man, "w"), indent=1)
    print("wrote", len(entries), "clips")


if __name__ == "__main__":
    main(*sys.argv[1:4])
