#!/bin/sh
# Chained reflash #9: LuCI + wpad build, UBI moved to the 34 MiB rootfs_ubi
# (data) region.
#   xflash12.py -> reboot to bootloader, load rescue initramfs + hybrid8, jump
#   phaseE.py   -> WiFi gate, read back staged fw, mtd write tclinux/alt,
#                  ubiformat the UBI payload onto rootfs_ubi, reboot
LOG=/tmp/opencode/autoflash9.log
: > "$LOG"
echo "AUTOFLASH9 START $(date '+%F %T')" >> "$LOG"

cd /home/qyoo/gw040h_build_session || exit 99

python3 xflash12.py > /tmp/opencode/xflash12.log 2>&1
rc=$?
echo "XFLASH12_RC=$rc" >> "$LOG"
if [ "$rc" != "0" ]; then
    echo "AUTOFLASH9 ABORT xflash12 rc=$rc" >> "$LOG"
    exit "$rc"
fi

python3 phaseE.py > /tmp/opencode/phaseE.out.log 2>&1
rc=$?
echo "PHASEE_RC=$rc" >> "$LOG"
echo "AUTOFLASH9 DONE rc=$rc" >> "$LOG"
exit $rc
