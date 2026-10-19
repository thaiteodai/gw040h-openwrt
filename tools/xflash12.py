#!/usr/bin/env python3
"""xflash11: boot OUR rescue initramfs (built from our tree, link addr 0x80020000,
GW040H DTB with console=) from RAM, and stage hybrid5 firmware in RAM.

Parity with the proven flash-boot path: bootbase LZMA-decompresses the kernel
payload to 0x80002000 (the 2RDH header loadaddr); that payload begins with a
4-byte stub  j 0x80020000  followed by 0x1DFFC zero bytes, so the real kernel
(a vmlinux.bin linked at 0x80020000) ends up at 0x80020000 and is entered there.
We therefore xmdm the raw initramfs-kernel.bin straight to 0x80020000 and
jump 80020000 -- the same kernel bytes at the same address, minus the stub and
bootbase fw args (unneeded: bootargs live in the DT chosen node).

xmdm quirk: receiver drops the FIRST 128-byte packet of every call, so each
call sends a 128B junk packet first, len == exact bytes sent, real chunk lands
contiguously at dest. Per-chunk head/tail verify before proceeding.

Phases: attach -> initramfs -> stage fw -> jump -> classify boot output.
Exit: 11 attach fail | 12 transfer/verify fail | 14 jump fault (bootbase
exception) | 15 no boot signal | 0 kernel up / shell up.
"""
import sys, time, serial, re, os

PORT, BAUD = "/dev/ttyUSB0", 115200
INIT_F = ("/home/qyoo/openwrt-build/bin/targets/econet/en751221/"
          "openwrt-econet-en751221-vnpt_gw040h-initramfs-kernel.bin")
FW_F = "/home/qyoo/gw040h-openwrt/openwrt-gw040h-hybrid8.trx"
INIT_ADDR = 0x80020000
FW_ADDR = 0x85000000
JUNK = b"\x00" * 128
BLK = 128

for f in (INIT_F, FW_F):
    if not os.path.exists(f):
        print("FATAL missing file:", f, flush=True)
        sys.exit(12)
INIT = open(INIT_F, "rb").read()
FW = open(FW_F, "rb").read()
print("initramfs: %d bytes, fw: %d bytes" % (len(INIT), len(FW)), flush=True)
assert len(INIT) % 128 or True  # padded per chunk anyway
if INIT[:4] == b"\0\0\0\0" or INIT == b"\0" * 16:
    print("FATAL: initramfs artifact looks empty", flush=True)
    sys.exit(12)

_T = []
for i in range(256):
    c = i << 8
    for _ in range(8):
        c = ((c << 1) ^ 0x1021) & 0xFFFF if c & 0x8000 else (c << 1) & 0xFFFF
    _T.append(c)


def xcrc(d):
    c = 0
    for b in d:
        c = ((c << 8) ^ _T[((c >> 8) ^ b) & 0xFF]) & 0xFFFF
    return c


s = serial.Serial(PORT, BAUD, timeout=0.3)
t_start = time.monotonic()


def log(m):
    print("[%6.0fs] %s" % (time.monotonic() - t_start, m), flush=True)


def rd(dur):
    t = time.monotonic()
    b = b""
    while time.monotonic() - t < dur:
        c = s.read(4096)
        if c:
            b += c
    return b


def drain_prompt(timeout=8):
    t = time.monotonic()
    while time.monotonic() - t < timeout:
        s.write(b"\r")
        o = rd(1.2)
        if b"bldr>" in o:
            return True
    return False


def send_packet(seq, blk, timeout=12, max_retry=12):
    hdr = b"\x01" + bytes([seq & 0xFF, (~seq) & 0xFF])
    pkt = hdr + blk + xcrc(blk).to_bytes(2, "big")
    retries = 0
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        s.write(pkt)
        t2 = time.monotonic()
        while time.monotonic() - t2 < timeout:
            c = s.read(1)
            if not c:
                retries += 1
                if retries > max_retry:
                    return False
                break
            if c == b"\x06":
                return True
            if c in (b"\x18",):
                return False
            if c in (b"\x15", b"C"):
                retries += 1
                if retries > max_retry:
                    return False
                break
            deadline = time.monotonic() + timeout
    return False


def eot_wait(tries=3, wait=3.0):
    for _ in range(tries):
        s.write(b"\x04")
        t = time.monotonic()
        while time.monotonic() - t < wait:
            c = s.read(1)
            if c == b"\x06":
                return True
    return False


def xfer_call(dest, payload, tag):
    assert len(payload) % BLK == 0
    s.reset_input_buffer()
    s.write(("xmdm %x %x\r" % (dest, len(payload))).encode())
    t = time.monotonic()
    poll = None
    while time.monotonic() - t < 20:
        c = s.read(1)
        if c in (b"C", b"\x15"):
            poll = c
            break
    if poll is None:
        log("FATAL %s: no XMODEM poll; tail=%r" % (tag, rd(3)[:60]))
        sys.exit(12)
    seq = 0
    for i in range(0, len(payload), BLK):
        if not send_packet(seq, payload[i:i + BLK]):
            log("FATAL %s: ack fail at +%#x" % (tag, i))
            sys.exit(12)
        seq = (seq + 1) & 0xFF
    eot_wait()
    drain_prompt(6)


LINE_RE = re.compile(rb"^([0-9a-fA-F]{8})\s+((?:[0-9a-fA-F]{2}[ \.]+)*[0-9a-fA-F]{2})")


def dump16(addr, timeout=2.0):
    s.reset_input_buffer()
    s.write(b"dump %08x 10\r" % addr)
    t = time.monotonic()
    buf = b""
    while time.monotonic() - t < timeout:
        c = s.read(64)
        if not c:
            continue
        buf += c
        lines = buf.replace(b"\r", b"").split(b"\n")
        for line in lines[:-1]:  # complete lines only (ignore echo)
            m = LINE_RE.match(line)
            if m and int(m.group(1), 16) == addr:
                hb = re.sub(rb"[ \.]+", b"", m.group(2))
                if len(hb) % 2:
                    hb = hb[:-1]
                return bytes.fromhex(hb.decode())
    return None


def pad128(chunk):
    if len(chunk) % BLK:
        chunk = chunk + b"\x1a" * (BLK - len(chunk) % BLK)
    return chunk


def xfer_abort():
    """Properly abort a stuck xmdm receive: CAN bytes then wait for prompt."""
    for _ in range(5):
        s.write(b"\x18\x18\x18")
        time.sleep(0.2)
    return drain_prompt(90)


def load_image(data, base, name, chunk_size=0x8000):
    nfull = len(data) // chunk_size
    rem = len(data) % chunk_size
    nchunks = nfull + (1 if rem else 0)
    # NOTE: no "resume"/skip optimisation. A previous run may have left a
    # similar-but-not-identical image in RAM (e.g. only the appended DTB
    # differs), and comparing just the head+tail of a chunk would then keep
    # stale bytes in the middle. Every chunk is (re)transferred; xmdm
    # carries a CRC per packet and phaseE re-verifies the whole image md5
    # out of /dev/mem before touching NAND.
    for i in range(nchunks):
        chunk = data[i * chunk_size:(i + 1) * chunk_size]
        dest = base + i * chunk_size
        for attempt in range(4):
            try:
                xfer_call(dest, JUNK + pad128(chunk), "%s[%d]" % (name, i))
            except SystemExit:
                if attempt < 3:
                    log("%s[%d] xfer died (attempt %d), aborting session..." % (name, i, attempt))
                    if not xfer_abort():
                        log("FATAL: cannot recover bldr> prompt")
                        sys.exit(11)
                    continue
                raise
            got = dump16(dest)
            if got == chunk[:16]:
                break
            log("VERIFY FAIL %s[%d] @%#x: got=%s exp=%s (attempt %d)" % (
                name, i, dest, got.hex() if got else None, chunk[:16].hex(), attempt))
            if not xfer_abort():
                log("FATAL: cannot recover bldr> prompt")
                sys.exit(11)
        else:
            return False
        if i % 16 == 0 or i == nchunks - 1:
            tail = dump16(dest + len(pad128(chunk)) - 16)
            if tail != pad128(chunk)[-16:]:
                log("TAIL FAIL %s[%d] @%#x" % (name, i, dest))
                return False
        if i % 8 == 0:
            log("%s chunk %d/%d ok" % (name, i, nchunks))
    return True


# ---------- attach ----------
# clear any xmdm session left stuck by a previous failed run
s.write(b"\x18\x18\x18")
time.sleep(0.5)

SHELL_MARK = (b"root@", b"Please press Enter", b"login:", b"/ #", b"~#")


def at_shell(buf):
    return any(m in buf for m in SHELL_MARK)


if not drain_prompt(6):
    # Not at bldr> yet. If an OS shell is running, reboot and catch the
    # bootloader's 3 second "press any key" window; otherwise just wait.
    s.reset_input_buffer()
    s.write(b"\r")
    probe = rd(3.0)
    log("attach probe: %r" % probe[-160:])
    if at_shell(probe):
        log("OS shell detected -> rebooting to reach boot command mode")
        s.write(b"\r\nreboot\r")
        got = False
        t = time.monotonic()
        while time.monotonic() - t < 90:
            s.write(b"\r")
            o = rd(0.5)
            if b"bldr>" in o:
                got = True
                break
        if got:
            log("attached at bldr>")
        else:
            log("reboot did not yield bldr>; falling through to wait loop")

if not drain_prompt(15):
    log("no prompt yet; sending aborts; waiting up to ~600s for bldr> "
        "(POWER-CYCLE THE ONT NOW: unplug, wait 5s, plug back in)")
    ok = False
    for _ in range(20):
        s.write(b"\x18\x18\x18")
        if drain_prompt(30):
            ok = True
            break
    if not ok:
        log("FATAL: no bldr> (device wedged -- power cycle needed)")
        sys.exit(11)
log("attached")

# ---------- phase 1: initramfs ----------
if not load_image(INIT, INIT_ADDR, "init"):
    sys.exit(12)
log("initramfs staged at %#x (%d bytes)" % (INIT_ADDR, len(INIT)))

# ---------- phase 2: stage firmware ----------
if not load_image(FW, FW_ADDR, "fw"):
    sys.exit(12)
log("firmware staged at %#x (%d bytes)" % (FW_ADDR, len(FW)))

# ---------- phase 3: jump ----------
log("jumping to rescue kernel...")
s.reset_input_buffer()
s.write(b"jump 80020000\r")
boot = rd(150)
open("/tmp/opencode/x12_boot.txt", "wb").write(boot)
log("boot capture: %d bytes" % len(boot))
print(boot[-3500:].decode("utf-8", "replace"), flush=True)

if b"Exception happen" in boot or b"Undefined Exception" in boot:
    log("RESULT: JUMP_FAULT")
    sys.exit(14)
shell_markers = (b"/ #", b"login:", b"Please press Enter", b"root@")
if any(m in boot for m in shell_markers):
    log("RESULT: SHELL_UP")
    sys.exit(0)
if b"Linux version" in boot:
    log("RESULT: KERNEL_BOOTED")
    sys.exit(0)
log("RESULT: NO_SIGNAL")
sys.exit(15)
