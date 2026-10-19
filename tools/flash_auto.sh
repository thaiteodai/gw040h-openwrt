#!/bin/bash
# GW040H OpenWrt flash watchdog - fully autonomous flash over USB-serial + LAN.
# Switches laptop to the ONT's AP, makes the device pull hybrid3 from the
# laptop's HTTP server, flashes tclinux (slot A), watches the boot over serial,
# then ALWAYS restores the home WiFi. Designed to run under `timeout` (TERM).
set -u
LOG=/tmp/opencode/flash_auto.log
: > "$LOG"
exec >>"$LOG" 2>&1

LANTX="QUOC THAI"
ONT="GW040-H_2.4G_8ADEC8"
IFACE="wlp1s0"
FW="openwrt-gw040h-hybrid3.trx"
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
trap 'ts "TERM/INT received"; exit 130' TERM INT

# ---- preflight ------------------------------------------------------------
ts "preflight: HTTP server"
curl -sI --max-time 5 "http://127.0.0.1:8000/$FW" | head -1 || { ts "HTTP server not serving $FW"; exit 1; }

ts "preflight: connection profiles"
nmcli con mod "$ONT" connection.autoconnect no ipv4.method auto ipv6.method ignore 2>/dev/null
nmcli con mod "$LANTX" connection.autoconnect no 2>/dev/null

# ---- switch to ONT AP -----------------------------------------------------
ts "switching to $ONT"
nmcli device wifi rescan 2>/dev/null
sleep 4
nmcli con up "$ONT" || { ts "FAILED: cannot activate $ONT"; exit 1; }

IP=""
for i in $(seq 1 40); do
    IP=$(nmcli -g IP4.ADDRESS dev show "$IFACE" 2>/dev/null | sed -n '1s|/.*||p')
    [ -n "$IP" ] && break
    sleep 1
done
ts "laptop IPv4 on ONT net (DHCP): ${IP:-NONE}"
if [ -z "$IP" ]; then
    ts "DHCP gave nothing - falling back to static 192.168.1.77"
    nmcli con mod "$ONT" ipv4.method manual ipv4.addresses 192.168.1.77/24
    nmcli con up "$ONT" 2>/dev/null
    sleep 5
    IP=$(nmcli -g IP4.ADDRESS dev show "$IFACE" 2>/dev/null | sed -n '1s|/.*||p')
fi
ts "laptop IPv4 on ONT net: ${IP:-NONE}"
[ -n "$IP" ] || { ts "FAILED: no IPv4 on ONT network"; exit 1; }
sleep 3

# ---- stage A: device downloads the firmware ------------------------------
ts "stage A: device downloads $FW from http://$IP:8000/"
CMD_A="python3 /tmp/opencode/serial_run.py \"rm -f /tmp/fw; /userfs/bin/curl -sS --connect-timeout 10 --max-time 120 -o /tmp/fw http://$IP:8000/$FW; echo CURL_RC=\$?; ls -l /tmp/fw\" 150"
OUT=$(ser "$CMD_A"); echo "$OUT"
echo "$OUT" | grep -q "$FWSIZE" || { ts "FAILED: device download size check (need $FWSIZE)"; exit 1; }
ts "stage A OK: size verified on device"

# ---- stage B: verify image magic on device --------------------------------
ts "stage B: verify 2RDH magic at offset 503"
CMD_B="python3 /tmp/opencode/serial_run.py \"dd if=/tmp/fw bs=1 skip=503 count=4 2>/dev/null; echo MAGIC_END\" 8"
OUT=$(ser "$CMD_B"); echo "$OUT"
echo "$OUT" | grep -q "2RDH" || { ts "FAILED: magic check"; exit 1; }
ts "stage B OK"

# ---- stage C: erase stale content of tclinux ------------------------------
# (clears OEM leftovers beyond the image so UBI sees erased PEBs, not corrupt)
ts "stage C: mtd erase tclinux"
CMD_C="python3 /tmp/opencode/serial_run.py \"/userfs/bin/mtd erase tclinux; echo ERASE_RC=\$?\" 110"
OUT=$(ser "$CMD_C"); echo "$OUT"
echo "$OUT" | grep -q "ERASE_RC=0" || ts "WARN: erase rc not confirmed (continuing; shell queues commands in order)"
ts "stage C done"

# ---- stage D: write image + reboot ---------------------------------------
ts "stage D: mtd -f -r write /tmp/fw tclinux"
CMD_D="python3 /tmp/opencode/serial_run.py \"/userfs/bin/mtd -f -r write /tmp/fw tclinux; echo WRITE_RC=\$?\" 170"
OUT=$(ser "$CMD_D"); echo "$OUT"
ts "stage D issued (device should be rebooting)"

# ---- stage E: watch boot over serial -------------------------------------
ts "stage E: watching serial for 100s"
printf 'python3 /tmp/opencode/serial_watch.py 100 > /tmp/opencode/boot.log 2>&1\n' | newgrp uucp
ts "boot log captured ($(wc -c < /tmp/opencode/boot.log) bytes)"
echo "---------- boot.log ----------"
cat /tmp/opencode/boot.log
echo "-------------------------------"
if grep -q "OpenWrt" /tmp/opencode/boot.log; then
    ts "RESULT: SUCCESS - OpenWrt booted"
elif grep -q "login:" /tmp/opencode/boot.log; then
    ts "RESULT: device up but NOT OpenWrt (bootloader likely fell back to os2/OEM)"
else
    ts "RESULT: no boot output seen - check boot.log"
fi
ts "flash_auto finished"
