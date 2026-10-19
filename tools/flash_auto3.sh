#!/bin/bash
# GW040H OpenWrt flash round 3 (hybrid4). One serial session does
# download -> verify (size + 2RDH + UBI#) -> conditional write, so the image
# is flashed immediately after verification. Retries up to 3x with device
# re-detection (round 2 died from a spurious device reboot during download,
# which wiped /tmp before we could flash). ALWAYS restores home WiFi.
set -u
LOG=/tmp/opencode/flash_auto3.log
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

ts "preflight"
curl -sI --max-time 5 "http://127.0.0.1:8000/$FW" | head -1 || { ts "no HTTP server"; exit 1; }
nmcli con mod "$ONT" connection.autoconnect no ipv4.method auto ipv6.method ignore 2>/dev/null
nmcli con mod "$LANTX" connection.autoconnect no 2>/dev/null

success=0
for attempt in 1 2 3; do
    ts "================ attempt $attempt ================"

    # wait for a responsive device shell (covers post-reboot states too)
    up=0
    for i in $(seq 1 40); do
        OUT=$(printf 'python3 /tmp/opencode/serial_probe.py 4\n' | newgrp uucp)
        if echo "$OUT" | grep -q -E 'login:|^# |Linux version'; then up=1; break; fi
    done
    [ "$up" = 1 ] || { ts "device never responded"; continue; }
    ts "device shell up - settling 60s"
    sleep 60

    # (re)join ONT AP
    nmcli con up "$ONT" >/dev/null 2>&1
    sleep 3
    IP=$(nmcli -g IP4.ADDRESS dev show "$IFACE" 2>/dev/null | sed -n '1s|/.*||p')
    ts "laptop IP on ONT net: ${IP:-NONE}"
    [ -n "$IP" ] || { ts "no IP on ONT net, retry"; continue; }

    # one serial session: download, verify, write only if verified
    # NOTE: single quotes around the device command - the intermediate zsh
    # (newgrp login shell) must NOT expand $(...) / $? before serial_run
    CMD="python3 /tmp/opencode/serial_run.py 'rm -f /tmp/fw; /userfs/bin/curl -sS --connect-timeout 10 --max-time 150 -o /tmp/fw http://$IP:8000/$FW; echo CURL_RC=\$?; ls -l /tmp/fw; M=\$(grep -c 2RDH /tmp/fw); U=\$(grep -c UBI# /tmp/fw); S=\$(ls -l /tmp/fw | grep -c $FWSIZE); echo VERIFY_M=\$M VERIFY_U=\$U VERIFY_S=\$S; if [ \$M -ge 1 ] && [ \$U -ge 1 ] && [ \$S -ge 1 ]; then echo START_WRITE; /userfs/bin/mtd -f -r write /tmp/fw tclinux; echo WRITE_RC=\$?; else echo WRITE_SKIPPED; fi' 340"
    OUT=$(ser "$CMD"); echo "$OUT"
    if ! echo "$OUT" | grep -q "START_WRITE"; then
        ts "attempt $attempt: verify failed or write skipped - retrying"
        continue
    fi
    ts "attempt $attempt: write issued, watching boot"

    printf 'python3 /tmp/opencode/serial_watch.py 150 > /tmp/opencode/boot3.log 2>&1\n' | newgrp uucp
    ts "boot3.log: $(wc -c < /tmp/opencode/boot3.log) bytes"
    tail -c 3000 /tmp/opencode/boot3.log
    echo
    if grep -q "OpenWrt" /tmp/opencode/boot3.log; then
        ts "RESULT: SUCCESS - OpenWrt booted"
        success=1
        break
    fi
    ts "attempt $attempt: no OpenWrt banner"
done

if [ "$success" != 1 ]; then
    ts "RESULT: all attempts exhausted"
fi
ts "flash_auto3 finished"
