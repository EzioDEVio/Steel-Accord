#!/usr/bin/env python3
"""Steel Accord QA - classify every path touched in an `strace -f -e trace=%file` log of a Wine run (read-only).

Categories (first match wins):
  clean_folder   under --clean (the folder holding SteelAccord.exe)
  user_data      the game's Godot user:// dir in the Wine prefix (AppData/Roaming/Godot/app_userdata/<name>)
  wine_prefix    anything else in the Wine prefix (registry, system32, fonts, dosdevices)
  wine_runtime   Wine's own install and server socket dirs
  system         host OS: /usr /lib /etc /sys /proc /dev, fontconfig caches, nix store
  ancestor_dir   a parent directory of the clean folder or prefix (stat/readlink during path resolution)
  OTHER          everything else  <- must be empty for a self-contained build
Also flags any path matching an EA / Steam / Command & Conquer pattern, whatever its category.

Usage: python3 -I tools/qa/filter_strace.py <strace.log> --clean <dir> --prefix <wineprefix> --cwd <dir>
                                            [--app "Steel Accord"] [--out report.json]
"""
import argparse
import collections
import json
import os
import re

LINE = re.compile(r"^(\d+)\s+(\S+)\s+(.*)$")
CALL = re.compile(r"^(\w+)\((.*)\)\s+=\s+(-?\d+|\?)\s*(.*)$")
QSTR = re.compile(r'"((?:[^"\\]|\\.)*)"')
EA_RE = re.compile(r"steam|command\s*&\s*conquer|command_conquer|c&c|\bcnc|generals|zero[ _-]?hour|"
                   r"electronic[ _-]?arts|\bea[ _-]games|\.big$", re.I)
TWO_PATH = {"rename", "renameat", "renameat2", "link", "linkat", "symlink", "symlinkat"}
NOT_PATH_2ND = {"getxattr", "lgetxattr", "setxattr", "lsetxattr", "removexattr", "lremovexattr", "listxattr",
                "llistxattr"}
SYSTEM_PREFIXES = ("/usr/", "/lib/", "/lib64/", "/etc/", "/sys/", "/proc/", "/dev/", "/var/cache/fontconfig",
                   "/var/lib/", "/run/", "/nix/", "/root/.nix-profile", "/root/.cache/fontconfig", "/root/.cache",
                   "/root/.fontconfig", "/root/.fonts", "/root/.local/share/fonts", "/root/.config/fontconfig",
                   "/root/.Xauthority", "/root/.XCompose", "/root/.config", "/root/.local", "/usr")
WINE_PREFIXES = ("/usr/lib/wine", "/usr/lib/x86_64-linux-gnu/wine", "/usr/lib/i386-linux-gnu/wine",
                 "/usr/share/wine", "/opt/wine", "/tmp/wine-", "/tmp/.wine-")


def unescape(s):
    return s.encode("latin1", "backslashreplace").decode("unicode_escape").encode("latin1").decode("utf-8", "replace")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    ap.add_argument("--clean", required=True)
    ap.add_argument("--prefix", required=True)
    ap.add_argument("--cwd", required=True)
    ap.add_argument("--app", default="Steel Accord")
    ap.add_argument("--out")
    a = ap.parse_args()
    clean = os.path.abspath(a.clean)
    prefix = os.path.abspath(a.prefix)
    userdir = None

    def norm(p):
        p = os.path.normpath(p)
        for drv, target in (("c:", prefix + "/drive_c"), ("z:", "")):
            pre = prefix + "/dosdevices/" + drv
            if p == pre or p.startswith(pre + "/"):
                p = os.path.normpath(target + p[len(pre):] or "/")
        return p

    ancestors = set()
    for base in (clean, prefix):
        d = base
        while True:
            d = os.path.dirname(d)
            ancestors.add(d)
            if d in ("/", ""):
                break

    def classify(p):
        if p == clean or p.startswith(clean + "/"):
            return "clean_folder"
        ud = prefix + "/drive_c/users/"
        if p.startswith(ud) and ("/AppData/Roaming/Godot/app_userdata/" + a.app) in p:
            return "user_data"
        if p.startswith(ud) and re.search(r"/AppData/Roaming/Godot(/app_userdata)?$", p):
            return "user_data"
        if p == prefix or p.startswith(prefix + "/"):
            return "wine_prefix"
        if p.startswith(WINE_PREFIXES):
            return "wine_runtime"
        if p in ancestors:
            return "ancestor_dir"
        if p.startswith(SYSTEM_PREFIXES) or p in ("/usr", "/lib", "/etc", "/tmp"):
            return "system"
        return "OTHER"

    cwd = {}
    fdmap = {}          # (pid, fd) -> path
    fdglob = {}         # fd -> path (fallback; threads/children share descriptors)
    pending = {}
    rows = []
    unresolved = collections.Counter()
    for raw in open(a.log, encoding="latin1"):
        m = LINE.match(raw.rstrip("\n"))
        if not m:
            continue
        pid, ts, rest = m.groups()
        if rest.endswith("<unfinished ...>"):
            pending[pid] = rest[: -len("<unfinished ...>")]
            continue
        rm = re.match(r"<\.\.\. (\w+) resumed>(.*)$", rest)
        if rm:
            rest = pending.pop(pid, rm.group(1) + "(") + rm.group(2)
        c = CALL.match(rest)
        if not c:
            continue
        name, args, ret, tail = c.groups()
        paths = [unescape(s) for s in QSTR.findall(args)]
        if not paths:
            continue
        if name in NOT_PATH_2ND or name not in TWO_PATH:
            paths = paths[:1]
        dirfd, dirpath = None, None
        dm = re.match(r"(AT_FDCWD|-?\d+)(?:<([^>]*)>)?,", args)     # strace -y decorates fds: 3</path>
        if dm and (name.endswith("at") or name in ("openat2", "faccessat2", "newfstatat", "statx", "readlinkat",
                                                   "mkdirat", "unlinkat", "renameat2")):
            dirfd, dirpath = dm.group(1), dm.group(2)
            if dirfd == "AT_FDCWD" and dirpath:
                cwd[pid] = dirpath          # exact cwd from strace -y (covers forked children)
        res = []
        for p in paths:
            if p.startswith("/"):
                full = p
            else:
                if dirpath:
                    base = dirpath
                elif dirfd and dirfd != "AT_FDCWD":
                    base = fdmap.get((pid, dirfd)) or fdglob.get(dirfd)
                else:
                    base = cwd.get(pid, a.cwd)
                if base is None:
                    unresolved[p] += 1
                    base = "<unresolved-dirfd>"
                full = base + "/" + p
            res.append(norm(full))
        ok = ret != "?" and not ret.startswith("-")
        if name in ("chdir",) and ok:
            cwd[pid] = res[0]
        if name in ("open", "openat", "openat2") and ok and ret.isdigit():
            fdmap[(pid, ret)] = res[0]
            fdglob[ret] = res[0]
        err = re.match(r"(E[A-Z]+)", tail).group(1) if (not ok and re.match(r"E[A-Z]+", tail or "")) else None
        mode = "write" if re.search(r"O_WRONLY|O_RDWR|O_CREAT|O_TRUNC", args) or name.startswith(
            ("mkdir", "unlink", "rename", "rmdir", "creat", "link", "symlink", "setxattr", "truncate", "chmod")) else "read"
        for p in res:
            rows.append((p, name, ok, err, mode))

    agg = {}
    for p, name, ok, err, mode in rows:
        r = agg.setdefault(p, {"path": p, "category": classify(p) if not p.startswith("<unresolved") else "OTHER",
                               "calls": collections.Counter(), "ok": 0, "failed": 0, "errors": collections.Counter(),
                               "write": False})
        r["calls"][name] += 1
        if ok:
            r["ok"] += 1
        else:
            r["failed"] += 1
            if err:
                r["errors"][err] += 1
        if mode == "write" and ok:
            r["write"] = True
    for r in agg.values():
        r["calls"] = dict(r["calls"])
        r["errors"] = dict(r["errors"])

    by_cat = collections.defaultdict(list)
    for r in agg.values():
        by_cat[r["category"]].append(r)
    summary = {}
    for k, v in sorted(by_cat.items()):
        summary[k] = {"unique_paths": len(v), "paths_with_success": sum(1 for r in v if r["ok"]),
                      "paths_only_failed_lookups": sum(1 for r in v if not r["ok"]),
                      "paths_written": sum(1 for r in v if r["write"])}
    ea = sorted((r for r in agg.values() if EA_RE.search(r["path"])), key=lambda r: r["path"])
    sys_tops = collections.Counter("/".join(r["path"].split("/")[:3]) for r in by_cat.get("system", []) if r["ok"])
    pre_tops = collections.Counter("/".join(r["path"][len(prefix):].split("/")[:4]) for r in by_cat.get("wine_prefix", [])
                                   if r["ok"])
    out = {
        "log": os.path.abspath(a.log), "clean_folder": clean, "wine_prefix": prefix,
        "syscall_lines_with_paths": len(rows), "summary_by_category": summary,
        "ea_steam_pattern_matches": ea,
        "clean_folder": sorted(by_cat.get("clean_folder", []), key=lambda r: r["path"]),
        "user_data": sorted(by_cat.get("user_data", []), key=lambda r: r["path"]),
        "ancestor_dir": sorted(by_cat.get("ancestor_dir", []), key=lambda r: r["path"]),
        "OTHER": sorted(by_cat.get("OTHER", []), key=lambda r: r["path"]),
        "system_successful_by_top_dir": dict(sys_tops.most_common()),
        "wine_prefix_successful_by_top_dir": dict(pre_tops.most_common()),
        "wine_runtime_unique_paths": summary.get("wine_runtime", {}).get("unique_paths", 0),
        "unresolved_relative": dict(unresolved),
    }
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=1)
    print(json.dumps(out["summary_by_category"], indent=1))
    print("EA/Steam pattern matches:", [(r["path"], r["ok"]) for r in ea])
    for k in ("clean_folder", "user_data", "ancestor_dir", "OTHER"):
        print("== %s" % k)
        for r in out[k]:
            print("  %-4s %-5s %s %s" % ("ok" if r["ok"] else "FAIL", "W" if r["write"] else "", r["path"], r["calls"]))


if __name__ == "__main__":
    main()
