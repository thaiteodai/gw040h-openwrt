#!/bin/bash
# GW040H OpenWrt flash round 2 (hybrid4: 2RDH header at flash offset 0).
# Stage 0 waits for the user to power-cycle the ONT (device currently halted
# in bootbase after a failed decompress in round 1), detected over serial.
# Then: device downloads hybrid4 over HTTP from the laptop (which switches to
# the ONT AP), erase+write tclinux, watch boot, ALWAYS restore home WiFi.
set -u
LOG=/tmp/opencode/flash_auto2.log
: > "$LOG"
exec >>"$LOG" 2>&1

LANTX="QUOC THAI"
ONT="GW040-H_2.4G_8ADEC8"
IFACE="wlp1s0"
FW="openwrt-gw040h-hybrid4.trx"
FWSIZE=8912896

ts() { echo "[$(date +%H:%M:%S)] $*"; }
ser() { printf '%s\n' "$1" | newgrp uucp; }

restore_wifi() {
    ts "EXIT: restoring $LANTX"
    nmcli con mod "$LANTX" connection.autoconnect yes 2>/dev/null
    nmcli con up "$LANTX" 2>/dev/null
    nmcli con mod "$ONT" connection.autoconnect no ipv4.method auto ipv4.addresses "" 2>/dev/null
    ts "EXIT: wifi restore attempted"
}
trap restore_wifi EXIT
trap 'ts "TERM/INT"; exit 130' TERM INT

ts "preflight: HTTP server"
curl -sI --max-time 5 "http://127.0.0.1:8000/$FW" | head -1 || { ts "no HTTP server"; exit 1; }
nmcli con mod "$ONT" connection.autoconnect no ipv4.method auto ipv6.method ignore 2>/dev/null
nmcli con mod "$LANTX" connection.autoconnect no 2>/dev/null

# ---- stage 0: wait for the ONT to come back after power cycle ------------
ts "stage 0: waiting for device serial activity (power-cycle the ONT!)"
deadline=$((SECONDS + 5400))
found=0
while [ "$SECONDS" -lt "$deadline" ]; do
    OUT=$(printf 'python3 /tmp/opencode/serial_probe.py 8\n' | newgrp uucp)
    if echo "$OUT" | grep -q -E 'login:|Linux version|bldr>'; then
        ts "stage 0: serial activity seen"
        echo "$OUT" | tail -5
        found=1
        break
    fi
done
[ "$found" = 1 ] || { ts "FAILED: device never came back (90 min)"; exit 1; }
ts "stage 0: letting boot + wifi AP settle (45s)"
sleep 45

# ---- switch to ONT AP ----------------------------------------------------
ts "switching to $ONT"
nmcli device wifi rescan 2>/dev/null; sleep 4
nmcli con up "$ONT" || { ts "FAILED: cannot activate $ONT"; exit 1; }
IP=""
for i in $(seq 1 40); do
    IP=$(nmcli -g IP4.ADDRESS dev show "$IFACE" 2>/dev/null | sed -n '1s|/.*||p')
    [ -n "$IP" ] && break
    sleep 1
done
ts "laptop IPv4 on ONT net (DHCP): ${IP:-NONE}"
if [ -z "$IP" ]; then
    ts "DHCP gave nothing - static 192.168.1.77"
    nmcli con mod "$ONT" ipv4.method manual ipv4.addresses 192.168.1.77/24
    nmcli con up "$ONT" 2>/dev/null; sleep 5
    IP=$(nmcli -g IP4.ADDRESS dev show "$IFACE" 2>/dev/null | sed -n '1s|/.*||p')
fi
[ -n "$IP" ] || { ts "FAILED: no IPv4 on ONT network"; exit 1; }
sleep 3

# ---- stage A: download ---------------------------------------------------
ts "stage A: device downloads $FW from http://$IP:8000/"
CMD_A="python3 /tmp/opencode/serial_run.py \"rm -f /tmp/fw; /userfs/bin/curl -sS --connect-timeout 10 --max-time 120 -o /tmp/fw http://$IP:8000/$FW; echo CURL_RC=\$?; ls -l /tmp/fw\" 150"
OUT=$(ser "$CMD_A"); echo "$OUT"
echo "$OUT" | grep -q "$FWSIZE" || { ts "FAILED: size check (need $FWSIZE)"; exit 1; }
ts "stage A OK"

# ---- stage B: magic at offset 0 ------------------------------------------
ts "stage B: verify 2RDH magic at offset 0"
CMD_B="python3 /tmp/opencode/serial_run.py \"dd if=/tmp/fw bs=1 count=4 2>/dev/null; echo MAGIC_END\" 8"
OUT=$(ser "$CMD_B"); echo "$OUT"
echo "$OUT" | grep -q "2RDH" || { ts "FAILED: magic check"; exit 1; }
ts "stage B OK"

# ---- stage C: erase tclinux ----------------------------------------------
ts "stage C: mtd erase tclinux"
CMD_C="python3 /tmp/opencode/serial_run.py \"/userfs/bin/mtd erase tclinux; echo ERASE_RC=\$?\" 110"
OUT=$(ser "$CMD_C"); echo "$OUT"
echo "$OUT" | grep -q "ERASE_RC=0" || ts "WARN: erase rc unconfirmed (continuing; shell queues in order)"

# ---- stage D: write + reboot ---------------------------------------------
ts "stage D: mtd -f -r write /tmp/fw tclinux"
CMD_D="python3 /tmp/opencode/serial_run.py \"/userfs/bin/mtd -f -r write /tmp/fw tclinux; echo WRITE_RC=\$?\" 170"
OUT=$(ser "$CMD_D"); echo "$OUT"

# ---- stage E: watch boot -------------------------------------------------
ts "stage E: watching serial for 120s"
printf 'python3 /tmp/opencode/serial_watch.py 120 > /tmp/opencode/boot2.log 2>&1\n' | newgrp uucp
ts "boot2.log: $(wc -c < /tmp/opencode/boot2.log) bytes"
echo "---------- boot2.log ----------"
cat /tmp/opencode/boot2.log
echo "-------------------------------"
if grep -q "OpenWrt" /tmp/opencode/boot2.log; then
    ts "RESULT: SUCCESS - OpenWrt booted"
elif grep -q "login:" /tmp/opencode/boot2.log; then
    ts "RESULT: up but NOT OpenWrt (fell back to os2/OEM again)"
else
    ts "RESULT: no boot output seen"
fi
ts "flash_auto2 finished"
