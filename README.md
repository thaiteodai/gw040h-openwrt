# VNPT GW040H → OpenWrt Custom Build / Build tùy chỉnh OpenWrt cho VNPT GW040H

*(Tiếng Việt dưới đây. [English below.])*

## Tiếng Việt

### Mục tiêu
Build OpenWrt tùy chỉnh cho ONT VNPT GW040H (SoC Econet EN751221, 256MB RAM, 128MB SPI NAND) với LuCI, overlay ghi được, WiFi 2.4G+5G (AP), và flash hoàn toàn qua cổng serial `/dev/ttyUSB0`.

### Điều kiện hoàn thành
- Dual-band WiFi AP (SSID `OpenWrt`)
- 4× GbE (chưa kiểm chứng toàn diện)
- LuCI web UI
- Overlay UBI write-persistent
- Flash qua UART (không cần mạng Ethernet từ máy cấu hình)
- Boot ổn định từ NAND

### Công cụ & thủ thuật
- `tools/xflash12.py` — tải rescue initramfs qua xmdm, staging firmware vào RAM, nhảy boot
- `tools/phaseE.py` — viết `tclinux`/`tclinux_alt` + UBI lên `rootfs_ubi`, verify md5, reboot
- `tools/build_hybrid8.py` — đóng gói kernel+UBI thành hybrid `2RDH` header
- `tools/postflash_verify.py` — xác minh sau flash

### Thư mục
- `files/target/linux/econet/` — DTS, image.mk, config changes để build
- `files/files/etc/uci-defaults/99-wifi-ap` — tự động bật AP sau lần boot đầu
- `tools/` — script tự động hóa flash/build
- `images/` — hybrid image đã flash (`openwrt-gw040h-hybrid8.trx`)
- `docs/` — boot log, notes, report

### Lệnh nhanh (tham khảo)
- Build: `make -j$(nproc) target/linux/compile` rồi tạo image theo cấu hình
- Flash: chạy `xflash12.py`, rồi `phaseE.py` trên console rescue

### Lưu ý quan trọng
- **GPON không hoạt động.** Không có driver xpon/EN7571 → WAN GPON không sử dụng được; thiết bị hoạt động như router/AP WiFi.
- **WiFi mở + root không có mật khẩu** sau flash. Cần đặt mật khẩu ngay.
- **Overlay mặc định 21–29 MB** theo cấu hình Option M.

## English

### Goal
Custom OpenWrt build for VNPT GW040H (Econet EN751221, 256MB RAM, 128MB SPI NAND) with LuCI, writable/persistent overlay, dual-band WiFi, and fully unattended serial flashing via `/dev/ttyUSB0`.

### Completed features
- Dual-band WiFi AP (SSID `OpenWrt`)
- 4× GbE (functionality assumed; not exhaustively validated)
- LuCI web UI
- UBI rootfs_data autoresized (~21–29 MB writable overlay)
- A/B kernel slots (`tclinux` / `tclinux_alt`)
- Stable boot from NAND

### Tools & workflow
- `tools/xflash12.py` — xmdm staging of rescue initramfs and firmware to RAM; jumps to boot
- `tools/phaseE.py` — writes `tclinux`/`tclinux_alt` and UBI (`rootfs_ubi`), verifies md5, reboots
- `tools/build_hybrid8.py` — wraps kernel+UBI into `2RDH` 256B header hybrid
- `tools/postflash_verify.py` — post-flash sanity checks

### Directory layout
- `files/` — OpenWrt source modifications (DTS, image.mk, config, uci-defaults)
- `tools/` — flashing/build automation scripts
- `images/` — final hybrid image (`openwrt-gw040h-hybrid8.trx`)
- `docs/` — logs, reports, notes
- `CREDITS.md` — references & acknowledgments
- `LICENSE` — MIT

### Quick notes
- **GPON unsupported.** No EN7571/xpon driver; fibre WAN is unusable.
- **Security:** open WiFi + empty root password on first boot — set passwords immediately.
- Partitions: `tclinux` (12M), `tclinux_alt` (12M), `rootfs_ubi` (34M), `bootloader/romfile/yaffs/safedata/reservearea` preserved.

---

*(Both languages as requested. References and attribution in CREDITS.md.)*
