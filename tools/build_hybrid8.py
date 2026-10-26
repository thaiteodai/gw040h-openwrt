#!/usr/bin/env python3
"""Wrap a built GW040H tclinux-trx image in the 2RDH hybrid layout.

The bootbase reads the "2RDH" header at flash offset 0 of tclinux (upstream
tclinux-trx format); the 503-byte scrambled prefix in the factory file is a
web-download envelope only. Layout:
  [0x000 .. 0x100)    fresh 256B "2RDH" header
  [0x100 .. 0x400000) LZMA kernel (from built image) + zero pad
  [0x400000 ..)       UBI payload (lands at flash 0x480000 = DTS rootfs_ubi)

Usage:
  tools/build_hybrid8.py [BUILT_TRX] [-o OUT_TRX]

BUILT_TRX defaults to ../openwrt/bin/targets/econet/en751221/
openwrt-econet-en751221-vnpt_gw040h-squashfs-tclinux.trx (i.e. a sibling
OpenWrt checkout) and can also come from the BUILT_TRX environment variable.
OUT_TRX defaults to images/openwrt-gw040h-hybrid8.trx in this repo.
"""
import argparse
import os
import struct
import sys
import zlib
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_BUILT = (
    REPO.parent
    / "openwrt/bin/targets/econet/en751221"
    / "openwrt-econet-en751221-vnpt_gw040h-squashfs-tclinux.trx"
)
DEFAULT_OUT = REPO / "images/openwrt-gw040h-hybrid8.trx"

HDR_LEN = 256
UBI_OFF = 0x400000      # UBI must land at file/flash-slot offset 0x400000

ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
ap.add_argument(
    "built",
    nargs="?",
    default=os.environ.get("BUILT_TRX", str(DEFAULT_BUILT)),
    help="built squashfs-tclinux.trx (default: %(default)s)",
)
ap.add_argument(
    "-o", "--out",
    default=os.environ.get("OUT_TRX", str(DEFAULT_OUT)),
    help="hybrid output file (default: %(default)s)",
)
args = ap.parse_args()

BUILT = Path(args.built)
OUT = Path(args.out)

if not BUILT.is_file():
    sys.exit(
        f"error: built image not found: {BUILT}\n"
        "Build the firmware first (make menuconfig -> Econet EN751221 -> "
        "VNPT GW040H) or pass the path explicitly."
    )

built = BUILT.read_bytes()
assert built[UBI_OFF:UBI_OFF + 3] == b"UBI", "no UBI# at 0x400000 in built image"

kernel_region = built[0:UBI_OFF - HDR_LEN]     # LZMA + zero pad
ubi = built[UBI_OFF:]
content = kernel_region + ubi

kernellen = len(kernel_region)                 # 0x400000 - 0x100 = 0x3FF00
rootfslen = len(ubi)
totlen = HDR_LEN + kernellen + rootfslen
crc = zlib.crc32(content) ^ 0xFFFFFFFF         # JAMCRC

hdr = bytearray(HDR_LEN)
hdr[0:4] = b"2RDH"
struct.pack_into(">I", hdr, 4, HDR_LEN)
struct.pack_into(">I", hdr, 8, totlen)
struct.pack_into(">I", hdr, 12, crc)
hdr[16:48] = b"G040DEVN00T009\n".ljust(32, b"\0")
hdr[48:80] = b"003_000_000_003\n".ljust(32, b"\0")
struct.pack_into(">I", hdr, 80, kernellen)
struct.pack_into(">I", hdr, 84, rootfslen)
struct.pack_into(">I", hdr, 88, 0)             # romfilelen
hdr[92:124] = b"3 6035 122 0\n".ljust(32, b"\0")
struct.pack_into(">I", hdr, 124, 0x80002000)   # loadaddr

img = bytes(hdr) + content

# verify as bootbase would (header at 0)
v = memoryview(img)
assert v[0:4] == b"2RDH"
hdrlen, tl, vcrc = struct.unpack(">III", v[4:16])
klen, rlen, romlen = struct.unpack(">III", v[80:92])
loadaddr = struct.unpack(">I", v[124:128])[0]
calc = zlib.crc32(bytes(v[HDR_LEN:HDR_LEN + klen + rlen])) ^ 0xFFFFFFFF
assert hdrlen == 256
assert tl == HDR_LEN + klen + rlen == len(img), (tl, len(img))
assert klen == UBI_OFF - HDR_LEN == 0x3FFF00
assert rlen == rootfslen
assert calc == vcrc, (hex(calc), hex(vcrc))
assert loadaddr == 0x80002000
assert v[UBI_OFF:UBI_OFF + 3] == b"UBI"
assert bytes(v[128:256]) == b"\0" * 128

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_bytes(img)
print(f"OK wrote {OUT} ({len(img)} bytes)")
print(f"kernellen=0x{klen:x} rootfslen=0x{rlen:x} totlen=0x{tl:x} crc=0x{vcrc:08x}")
