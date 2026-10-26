#!/usr/bin/env python3
"""Minimal flattened-device-tree dumper (pure Python, no libfdt)."""
import sys, struct

MAGIC = 0xD00DFEED
BEGIN_NODE, END_NODE, PROP, NOP, END = 1, 2, 3, 4, 9


def _cstr(buf, p):
    e = buf.find(b"\0", p)
    return buf[p:e].decode("utf-8", "replace")


def parse(path):
    raw = open(path, "rb").read()
    off = raw.find(struct.pack(">I", MAGIC))
    if off < 0:
        raise SystemExit("no FDT magic in %s" % path)
    d = raw[off:]
    hdr = struct.unpack(">10I", d[:40])
    totalsize, off_struct, off_strings, off_rsvmap = hdr[1], hdr[2], hdr[3], hdr[4]
    size_strings, size_struct = hdr[8], hdr[9]
    print("FDT @0x%x totalsize=%d version=%d" % (off, totalsize, hdr[5]))
    sb = d[off_struct:off_struct + size_struct]
    st = d[off_strings:off_strings + size_strings]

    nodes = []          # (path, {name: bytes})
    stack = []
    p = 0
    while p < len(sb):
        tok = struct.unpack(">I", sb[p:p + 4])[0]
        p += 4
        if tok == BEGIN_NODE:
            nm = _cstr(sb, p)
            p += (len(nm.encode()) + 1 + 3) & ~3
            stack.append(nm)
            nodes.append(("/" + "/".join(n for n in stack if n), {}))
        elif tok == END_NODE:
            if stack:
                stack.pop()
        elif tok == PROP:
            plen, noff = struct.unpack(">II", sb[p:p + 8])
            p += 8
            val = sb[p:p + plen]
            p += (plen + 3) & ~3
            pname = _cstr(st, noff)
            if not stack:
                continue
            path = "/" + "/".join(n for n in stack if n)
            for np, props in nodes:
                if np == path:
                    props[pname] = val
                    break
        elif tok == NOP:
            continue
        elif tok == END:
            break
    return nodes


def fmt(val):
    if len(val) == 0:
        return "<empty>"
    if len(val) % 4 == 0 and len(val) <= 16:
        words = struct.unpack(">%dI" % (len(val) // 4), val)
        return " ".join("0x%x" % w for w in words)
    try:
        s = val.rstrip(b"\0").decode("utf-8")
        if s.isprintable():
            return repr(s)
    except UnicodeDecodeError:
        pass
    return "<%d bytes>" % len(val)


if __name__ == "__main__":
    want = sys.argv[2:] if len(sys.argv) > 2 else []
    for path, props in parse(sys.argv[1]):
        if want and not any(w in path for w in want):
            continue
        print("\n%s {" % path)
        for k, v in props.items():
            print("    %-28s = %s" % (k, fmt(v)))
