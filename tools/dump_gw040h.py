#!/usr/bin/env python3
"""
GW040H firmware dumper — run AFTER providing the admin password.
Usage: GW040H_PASS=<password> python3 dump_gw040h.py
Dumps all MTD partitions to ./dumps/ (TFTP preferred, base64 fallback).
"""
import os, serial, time, sys, subprocess, base64, re

PASS = os.environ.get("GW040H_PASS")
if not PASS:
    print("Set GW040H_PASS env var to the device admin password."); sys.exit(1)
USER = os.environ.get("GW040H_USER", "admin")
PORT = os.environ.get("GW040H_PORT", "/dev/ttyUSB0")
BAUD = 115200
OUTDIR = os.environ.get("GW040H_OUT", "./dumps")
os.makedirs(OUTDIR, exist_ok=True)

ser = serial.Serial(PORT, BAUD, timeout=2)
ser.dtr = False; ser.rts = False
log = open(os.path.join(OUTDIR, "session.log"), "w")

def rd(t=2):
    buf = b""
    end = time.time() + t
    while time.time() < end:
        try:
            d = ser.read(4096)
            if d: buf += d
        except Exception:
            pass
        time.sleep(0.1)
    log.write(buf.decode("utf-8","replace")); log.flush()
    sys.stdout.buffer.write(buf); sys.stdout.flush()
    return buf.decode("utf-8","replace")

def send(cmd, wait=1):
    ser.write((cmd + "\r\n").encode()); ser.flush()
    time.sleep(0.3)
    return rd(wait)

# --- login ---
ser.write(b"\r\n"); time.sleep(0.8); rd(1)
ser.write((USER + "\r\n").encode()); time.sleep(0.8); rd(1)
ser.write((PASS + "\r\n").encode()); time.sleep(2)
buf = rd(2)
if "Login incorrect" in buf or "locked" in buf.lower():
    print("LOGIN FAILED"); ser.close(); sys.exit(1)
print("LOGGED IN")

# --- probe partitions + tools ---
send("cat /proc/mtd", 2)
send("which dd base64 tftp uuencode od hexdump 2>/dev/null; echo TOOLS_DONE", 2)

# parse mtd list
# expect lines like: mtd0: 00040000 00020000 "bootloader"
parts = []
out = send("cat /proc/mtd", 2)
for line in out.splitlines():
    m = re.match(r'mtd(\d+):\s+([0-9a-f]+)\s+([0-9a-f]+)\s+"([^"]+)"', line, re.I)
    if m:
        parts.append((int(m.group(1)), m.group(4), int(m.group(2),16)))

if not parts:
    print("Could not parse /proc/mtd; dumping aborted."); ser.close(); sys.exit(1)

# --- dump strategy: try tftp first ---
# Check if tftp exists
toolcheck = send("command -v tftp || echo NO_TFTP", 1)
has_tftp = "NO_TFTP" not in toolcheck

if has_tftp:
    host_ip = os.environ.get("GW040H_HOSTIP", "192.168.1.7")
    print("Using TFTP ->", host_ip, "(start a TFTP server on host first!)")
    for idx, name, size in parts:
        remote = f"mtd{idx}_{name}.bin"
        send(f"dd if=/dev/mtd{idx} of=/tmp/{remote} bs=65536 2>/dev/null; echo DD_DONE_{idx}", 3)
        send(f"tftp -p -l /tmp/{remote} -r {remote} {host_ip}; echo TFTP_DONE_{idx}", max(5, size//115200 + 5))
        print(f"partition {idx} ({name}) {size} bytes -> {remote}")
else:
    print("No tftp; falling back to base64 over serial (slow).")
    for idx, name, size in parts:
        print(f"Dumping mtd{idx} ({name}) {size} bytes via base64...")
        ser.write(f"dd if=/dev/mtd{idx} bs=65536 2>/dev/null | base64\n".encode()); ser.flush()
        # collect until we see a prompt-ish marker
        collected = b""
        end = time.time() + max(30, size//5000 + 30)
        while time.time() < end:
            try:
                d = ser.read(4096)
                if d: collected += d
            except Exception:
                pass
            time.sleep(0.1)
        text = collected.decode("utf-8","replace")
        # strip non-base64 lines
        b64 = "".join(l for l in text.splitlines() if re.fullmatch(r"[A-Za-z0-9+/=]+", l.strip()))
        try:
            raw = base64.b64decode(b64)
            path = os.path.join(OUTDIR, f"mtd{idx}_{name}.bin")
            with open(path, "wb") as f: f.write(raw)
            print(f"  wrote {len(raw)} bytes -> {path}")
        except Exception as e:
            print(f"  decode failed: {e}")

ser.write(b"exit\r\n"); ser.close()
print("DONE. Dumps in", OUTDIR)
EOF
echo "written"