#!/usr/bin/env python3
"""postflash_verify -- after autoflash9 completes, independently confirm the
NAND firmware came up: boot log, mount/overlay size, WiFi APs, LuCI reachable.

Reads/writes only /dev/ttyUSB0. Run once nothing else holds the port.
"""
import re, sys, time
import serial

PORT, BAUD = "/dev/ttyUSB0", 115200
LOG = "/tmp/opencode/postflash_verify.log"

s = serial.Serial(PORT, BAUD, timeout=0.4)
open(LOG, "w").close()


def log(m):
    print(m, flush=True)
    with open(LOG, "a") as f:
        f.write(m + "\n")


def rd(dur):
    t = time.monotonic()
    b = b""
    while time.monotonic() - t < dur:
        c = s.read(4096)
        if c:
            b += c
    return b


def wait_shell(timeout=420):
    t = time.monotonic()
    buf = b""
    while time.monotonic() - t < timeout:
        seg = rd(1.0)
        if seg:
            buf += seg
            open(LOG + ".boot", "ab").write(seg)
            low = buf[-400:]
            if b"login:" in low:
                s.write(b"root\n"); time.sleep(0.6); continue
            if b"Password:" in low:
                s.write(b"\n"); time.sleep(0.6); continue
            if re.search(rb"(?:^|[\r\n])[^\r\n]{0,120}?[#$]\s*$", low):
                return True, buf
        s.write(b"\n")
    return False, buf


n = 0


def sh(cmd, timeout=60):
    global n
    n += 1
    tag = "__v%d" % n
    s.reset_input_buffer()
    s.write(('echo "%s_B"; %s; echo "%s_RC=$?"\n' % (tag, cmd, tag)).encode())
    buf = b""
    t = time.monotonic()
    rx = re.compile(re.escape(tag.encode()) + rb"_RC=(\d+)")
    while time.monotonic() - t < timeout:
        c = s.read(2048)
        if c:
            buf += c
            m = rx.search(buf)
            if m:
                out = buf[:m.start()].rsplit(tag.encode() + b"_B", 1)[-1]
                return int(m.group(1)), out.replace(b"\r", b"").decode("utf-8", "replace")
    return None, buf.replace(b"\r", b"").decode("utf-8", "replace")


ok, boot = wait_shell()
log("=== shell reached: %s (%d bytes of boot log) ===" % (ok, len(boot)))
if not ok:
    log("FATAL: no shell prompt; tail:\n" + boot[-2000:].decode("utf-8", "replace"))
    sys.exit(21)

sh("stty -echo 2>/dev/null; true", 20)

CHECKS = [
    ("release",       "cat /etc/openwrt_release"),
    ("proc/mtd",      "cat /proc/mtd"),
    ("ubi",           "ubinfo -a 2>&1 | head -40"),
    ("mounts",        "mount | grep -E 'overlay|rootfs' ; df -h"),
    ("overlay_free",  "df -h /overlay"),
    ("wifi_status",   "ubus call network.wireless status 2>&1 | grep -E '\"up\"|radio|section|ifname' | head -40"),
    ("iw_dev",        "iw dev 2>&1"),
    ("wifi_cfg",      "cat /etc/config/wireless"),
    ("net",           "ip -4 addr show 2>&1 | grep -E 'inet |^[0-9]+:'"),
    ("uhttpd",        "ps w | grep -c '[u]httpd'; netstat -ltnp 2>/dev/null | grep -E ':80|:443'"),
    ("mt7615",        "dmesg | grep -iE 'mt7615|eeprom|phy0' | tail -15"),
    ("luci_index",    "wget -qO- -T5 http://127.0.0.1/cgi-bin/luci >/dev/null 2>&1; echo http_rc=$?"),
    ("samplerate",    "free -m | head -2 ; uptime"),
]
for name, cmd in CHECKS:
    rc, out = sh(cmd)
    log("### %s (rc=%s)\n%s\n" % (name, rc, out.strip()))

log("=== postflash_verify done ===")
s.close()
