# Tools / Công cụ

[Tiếng Việt dưới đây. [English below.]]

## Tiếng Việt

Script tự động hóa: flash qua UART (xmdm), đóng gói hybrid image, verify sau flash.
Tất cả mặc định dùng `/dev/ttyUSB0` @ `115200 8N1` (đổi trong đầu file nếu cần).

| Script | Chức năng |
|---|---|
| `xflash12.py` | Giai đoạn 1: đợi `bldr>`, nạp rescue initramfs vào `0x80020000`, nạp hybrid vào `0x85000000`, nhảy vào rescue kernel (chạy từ RAM) |
| `phaseE.py` | Giai đoạn 2: đọc lại ảnh từ `/dev/mem` + so MD5, ghi `tclinux` (mtd2) + `tclinux_alt` (mtd3), `ubiformat` UBI vào `rootfs_ubi` (mtd4), verify volume, `sync` + `reboot` |
| `build_hybrid8.py` | Bọc ảnh build (`...-squashfs-tclinux.trx`) thành hybrid `2RDH` |
| `postflash_verify.py` | Kiểm tra sau flash: release, `/proc/mtd`, `ubinfo`, overlay, WiFi, LuCI |
| `autoflash9.sh` | Chạy liền `xflash12.py` → `phaseE.py`, log vào `/tmp/opencode/autoflash9.log` |
| `fdt_dump.py`, `dump_gw040h.py` | Công cụ thăm dò FDT/partition lúc nghiên cứu (không cần cho flash) |

Cách dùng:

```bash
python3 tools/xflash12.py
python3 tools/phaseE.py                     # SKIP_WIFI_CHECK=1 để bỏ qua cổng kiểm tra WiFi
python3 tools/postflash_verify.py

# Đóng gói hybrid (mặc định tìm ../openwrt/bin/targets/... và ghi vào images/)
tools/build_hybrid8.py
tools/build_hybrid8.py /duong/dan/openwrt-econet-en751221-vnpt_gw040h-squashfs-tclinux.trx \
    -o images/openwrt-gw040h-hybrid8.trx
# hoặc dùng biến môi trường BUILT_TRX / OUT_TRX
```

Lưu ý:
- Đóng terminal/picocom/minicom trước khi chạy (chúng giữ `/dev/ttyUSB0`).
- UART có thể treo (`could not open port`): rút và cắm lại cáp USB-TTL.
- Nếu đã vào rescue system mà UART chết, có thể ghi nốt qua SSH — xem README mục *Dự phòng: UART hỏng giữa chừng*.

## English

Automation scripts: UART/xmdm flashing, hybrid image construction, post-flash verification.
Defaults: `/dev/ttyUSB0` @ `115200 8N1` (edit the constants at the top of each script to change).

| Script | Purpose |
|---|---|
| `xflash12.py` | Phase 1: wait for `bldr>`, stage rescue initramfs at `0x80020000`, stage the hybrid at `0x85000000`, jump to the RAM rescue kernel |
| `phaseE.py` | Phase 2: read the staged image back from `/dev/mem` + MD5 check, write `tclinux` (mtd2) and `tclinux_alt` (mtd3), `ubiformat` the UBI onto `rootfs_ubi` (mtd4), verify volumes, `sync` + `reboot` |
| `build_hybrid8.py` | Wrap a built `...-squashfs-tclinux.trx` into the `2RDH` hybrid layout |
| `postflash_verify.py` | Post-flash checks: release, `/proc/mtd`, `ubinfo`, overlay, WiFi, LuCI |
| `autoflash9.sh` | Chain `xflash12.py` → `phaseE.py`, logs to `/tmp/opencode/autoflash9.log` |
| `fdt_dump.py`, `dump_gw040h.py` | Research helpers for FDT/partition probing (not needed for flashing) |

Usage:

```bash
python3 tools/xflash12.py
python3 tools/phaseE.py                     # SKIP_WIFI_CHECK=1 to bypass the WiFi gate
python3 tools/postflash_verify.py

# Package the hybrid (defaults to ../openwrt/bin/targets/... and writes to images/)
tools/build_hybrid8.py
tools/build_hybrid8.py /path/to/openwrt-econet-en751221-vnpt_gw040h-squashfs-tclinux.trx \
    -o images/openwrt-gw040h-hybrid8.trx
# or use the BUILT_TRX / OUT_TRX environment variables
```

Notes:
- Close picocom/minicom/screen first (they hold `/dev/ttyUSB0`).
- The UART can wedge (`could not open port`): unplug and replug the USB-TTL adapter.
- If the UART dies after the rescue system is up, you can finish over SSH — see the README *SSH fallback* section.
