# VNPT GW040H → OpenWrt Custom Build / Build tùy chỉnh OpenWrt cho VNPT GW040H

> Custom OpenWrt build for VNPT GW040H (Econet EN751221, 256MB RAM, 128MB SPI NAND). Dual-band WiFi AP, LuCI, writable UBI overlay, A/B kernel slots, UART flashing with xmdm. GPON unsupported.

## Trạng thái / Status

*Cập nhật / updated 2026-10-26.*

| Hạng mục / Item | Kết quả / Result |
|---|---|
| Boot từ NAND, overlay UBI ghi được / NAND boot + writable UBI overlay | ✅ đã kiểm chứng trên phần cứng / verified on hardware |
| LuCI (uhttpd, cổng 80/443) | ✅ |
| WiFi 2.4 GHz + 5 GHz (MT7615E, SSID `OpenWrt`) | ✅ |
| 4× cổng LAN GbE / 4× GbE LAN ports | ✅ (test nhanh / quick test 2026-10-19) |
| Flash qua UART (`xmdm`) | ✅ |
| LED trên vỏ máy / case LEDs | ❌ **chưa hoạt động** — DTS không có node `gpio-leds`; `01_leds` chỉ tạo cấu hình trỏ tới tên LED không tồn tại / not wired up |
| Nút WPS / Reset | ❌ **chưa hoạt động** — không có node `gpio-keys`, không có `/dev/input` / no input device |
| GPON (EN7571) | ❌ không có driver / unsupported |
| VoIP FXS (Le9662) | ❌ không có trong build / not included |
| `sysupgrade` | ⚠️ chưa kiểm chứng, dùng lại quy trình UART / untested |
| Mật khẩu root / root password | ⚠️ trống sau flash, phải đặt ngay / empty, set it immediately |

> **Về LED và nút bấm / About LEDs and buttons:** `gpiochip0` + `gpiochip1` (2×32 line) có trong kernel nhưng chưa gán cho thiết bị nào. Muốn dùng phải dò chân: đọc input trong lúc bấm nút (an toàn), rồi xuất output để tìm từng LED, sau đó thêm node `gpio-leds` / `gpio-keys` vào DTS và build lại. Xem mục [Known issues](#known-issues--việc-còn-lại).

## Ảnh & checksum / Images & checksums

Hai file dưới đây là đúng bản đã flash lên phần cứng / these are the exact artifacts flashed to hardware:

| File | Kích thước / Size | MD5 |
|---|---|---|
| `images/openwrt-gw040h-hybrid8.trx` | 10,092,544 B | `7b4e7c972224e7dcb50d9e184fbf5380` |
| `images/openwrt-econet-en751221-vnpt_gw040h-initramfs-kernel.bin` | 7,701,664 B | `e3a7679033fcc3b99dce65020db01e43` |

Kiểm tra trước khi flash / verify before flashing:

```bash
cd gw040h-openwrt-project
md5sum images/openwrt-gw040h-hybrid8.trx \
       images/openwrt-econet-en751221-vnpt_gw040h-initramfs-kernel.bin
```

*(Tiếng Việt dưới đây. [English below.])*

## Tiếng Việt

### Mục tiêu
Build OpenWrt tùy chỉnh cho ONT VNPT GW040H (SoC Econet EN751221, 256MB RAM, 128MB SPI NAND) với LuCI, overlay ghi được, WiFi 2.4G+5G (AP), và flash hoàn toàn qua cổng serial `/dev/ttyUSB0`.

### Điều kiện hoàn thành
- Dual-band WiFi AP (SSID `OpenWrt`)
- 4× GbE (test nhanh 2026-10-19: cả 4 cổng LAN đều hoạt động)
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
- 4× GbE (all 4 ports confirmed working)
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

### Build from source / Build lại từ source

Repo này **không phải** một cây OpenWrt đầy đủ — chỉ chứa các file cần chép đè vào cây OpenWrt để build cho GW040H. / This repo is **not** a full OpenWrt tree — it only holds the files overlaid onto an OpenWrt checkout.

```bash
git clone https://git.openwrt.org/openwrt/openwrt.git
cd openwrt
rsync -a /path/to/gw040h-openwrt-project/files/ ./
make menuconfig      # Target: Econet (EN751221) -> Device: VNPT GW040H
make -j"$(nproc)"
```

Nội dung overlay `files/`:

| Đường dẫn / Path | Vai trò / Purpose |
|---|---|
| `target/linux/econet/dts/en751221_vnpt_gw040h.dts` | flash map, GMAC, PCIe MT7615, EEPROM nvmem |
| `target/linux/econet/image/en751221.mk` | định nghĩa device `vnpt_gw040h` (kích thước kernel/rootfs) |
| `target/linux/econet/en751221/config-6.18` | bật `CONFIG_DEVMEM` (cần cho `tools/phaseE.py` đọc ảnh staged từ `/dev/mem`) |
| `target/linux/econet/base-files/etc/board.d/01_leds` | cấu hình LED — hiện chưa có tác dụng (xem bảng trạng thái) |
| `files/etc/uci-defaults/99-wifi-ap` | bật AP ở lần boot đầu (máy cấu hình chỉ có WiFi) |

Sau khi build, bọc ảnh bằng script trong repo / wrap the built image:

```bash
tools/build_hybrid8.py \
  ../openwrt/bin/targets/econet/en751221/openwrt-econet-en751221-vnpt_gw040h-squashfs-tclinux.trx \
  -o images/openwrt-gw040h-hybrid8.trx
```

Ảnh rescue `...-initramfs-kernel.bin` do cùng lần build sinh ra. / The rescue image comes from the same build.

---

*(Both languages as requested. References and attribution in CREDITS.md.)*

## Credit / Ghi công

Project commissioned and led by the user. Full attribution and references in CREDITS.md.


## Known issues / Việc còn lại

1. **LED và nút bấm / LEDs and buttons.** Không có node `gpio-leds` / `gpio-keys` trong DTS, nên `01_leds` chỉ sinh ra các mục `system.led_*` trỏ tới tên `green:wan`, `green:power`, … không tồn tại trong `/sys/class/leds`; `/dev/input` cũng trống. Cần dò chân GPIO (2×32 line trên `gpiochip0/1`) rồi thêm node vào DTS và build lại.
2. **Không dùng layout này cho GW240H / Do not reuse this layout on GW240H.** Cùng SoC EN751221 nhưng bootbase GW240H chạy `boot flag = 1` và boot slot phụ tại `0x1e80000`; đặt `rootfs_ubi` ở `0x1880000` sẽ ghi đè slot đó và máy chết (`Undefined Exception`). GW240H phải dùng `rootfs_ubi` tại `0x2a80000`.
3. **GPON / VoIP chưa hỗ trợ / unsupported.** Không có driver EN7571/xPON, không có stack VoIP cho Le9662 → chỉ dùng làm router/AP.
4. **`sysupgrade` chưa kiểm chứng / untested.** Flash lại bằng đúng quy trình UART (4.1 → 4.2); `tclinux_alt` là slot dự phòng.
5. **Mật khẩu root trống và WiFi mở sau flash** — đặt ngay sau khi boot.

## Tutorial / Hướng dẫn thực hiện

*(Tiếng Việt dưới đây. [English below.])*

## HƯỚNG DẪN THỰC HIỆN 

Phần này hướng dẫn chi tiết từng bước để flash OpenWrt tùy chỉnh lên VNPT GW040H, chỉ cần máy tính Linux, cáp USB-TTL và kết nối UART.

### 1. Yêu cầu thiết bị & phần mềm

#### Phần cứng
- ONT VNPT GW040H
- Cáp USB-TTL 3.3V (CP2102, FT232RL hoặc tương tự). **KHÔNG dùng 5V**.
- Dây nối mảnh đến pad UART trên bo mạch GW040H (TX/RX/GND)
- Nguồn điện ổn định cho ONT

#### Phần mềm (máy Linux)
- Python 3
- pyserial: `pip install pyserial` hoặc `apt install python3-serial`
- TFTP server (tùy chọn, chỉ dùng nếu cần dump firmware gốc)
- Không chạy đồng thời 2 chương trình đọc serial (vd. `picocom`, `minicom`, `screen`) cùng lúc với tool flash.

### 2. Xác định kết nối UART

GW040H có pad UART trên bo mạch (thường gần SoC). Cần xác định 3 chân: GND, TX, RX.

**Cách nối (quan trọng):** Nối RX của USB-TTL → TX của bo mạch, TX của USB-TTL → RX của bo mạch, GND ↔ GND. **Đảo ngược TX/RX nếu không nhận được log.**

Sau khi cắm USB-TTL, kiểm tra thiết bị serial:
```bash
ls -l /dev/ttyUSB*
dmesg | tail -5
```

Thông thường là `/dev/ttyUSB0`. Tất cả script trong repo mặc định dùng `/dev/ttyUSB0`, baudrate `115200 8N1`.

### 3. Chuẩn bị môi trường làm việc

Clone repo này hoặc copy vào máy:
```bash
cd gw040h-openwrt-project   # hoặc đường dẫn bạn lưu repo
chmod +x tools/*.py tools/*.sh
```

Kiểm tra pyserial:
```bash
python3 -c "import serial; print('ok')"
```

### 4. Cách flash (2 giai đoạn: RAM rescue → NAND)

Quy trình này chạy hoàn toàn qua UART, không cần Ethernet. Gồm 2 bước chính:

1. `xflash12.py` — Boot kernel rescue (initramfs) từ RAM qua giao thức xmdm (bootloader Econet). Sau đó tải hybrid image vào RAM tại `0x85000000`.
2. `phaseE.py` — Chạy trên rescue Linux (RAM), đọc lại image từ `/dev/mem`, verify MD5, ghi `tclinux` + `tclinux_alt`, ghi UBI vào `rootfs_ubi`, sync và reboot.

#### Bước 4.1: Tải rescue initramfs + staging firmware vào RAM

Đảm bảo **chưa** có chương trình nào đang giữ `/dev/ttyUSB0` (đóng picocom/minicom/screen).

Chạy:
```bash
python3 tools/xflash12.py
```

Script sẽ:
- Tìm bootloader prompt (`bldr>`) — nếu chưa thấy, nó sẽ yêu cầu **rút nguồn ONT → chờ 5s → cắm lại nguồn** (power cycle). Làm theo yêu cầu trên terminal.
- Gửi initramfs (`openwrt-econet-en751221-vnpt_gw040h-initramfs-kernel.bin`) qua xmdm đến `0x80020000`
- Gửi hybrid image (`images/openwrt-gw040h-hybrid8.trx`) qua xmdm đến `0x85000000`
- Jump đến `0x80020000` → boot rescue Linux từ RAM

Thành công khi thấy log boot Linux (kernel version, MTD, ...) và cuối cùng có dấu nhắc shell (`/ #` hoặc `root@OpenWrt:~#` sau khi login). Script sẽ tự thoát với `RESULT: SHELL_UP` hoặc in log.

**Lưu ý quan trọng:** Trong giai đoạn này, ONT đang chạy hoàn toàn từ RAM. NAND chưa bị ghi đè.

#### Bước 4.2: Ghi firmware xuống NAND

Trong cùng terminal (hoặc sau khi `xflash12.py` thành công), chạy:
```bash
python3 tools/phaseE.py
```

Script sẽ:
1. Đợi shell root trên rescue system (tự login nếu cần)
2. Kiểm tra `/dev/mem` khả dụng
3. Đọc lại firmware đã staging tại `0x85000000` (phys `0x05000000`) qua `/dev/mem`, so sánh MD5 với file gốc (bảo vệ chống corrupt khi staging)
4. Kiểm tra WiFi pre-check (MT7615E/EEPROM) — có thể bỏ qua bằng env `SKIP_WIFI_CHECK=1` nếu cần: `SKIP_WIFI_CHECK=1 python3 tools/phaseE.py`
5. Ghi kernel đến `tclinux` (mtd2), verify MD5 vùng kernel, mirror sang `tclinux_alt` (mtd3)
6. Trích xuất UBI payload, `ubidetach`, `ubiformat /dev/mtd4` (rootfs_ubi), verify volumes `rootfs` + `rootfs_data` tồn tại
7. `sync` và `reboot`

Khi thành công, ONT sẽ reboot tự động và boot từ NAND với firmware mới.

#### Dự phòng: UART hỏng giữa chừng → flash nốt qua SSH

Rescue system (initramfs, bước 4.1) chạy `dropbear` với root **mật khẩu trống**. Nếu cáp USB-TTL bị treo sau khi đã vào rescue (NAND **chưa** bị ghi), có thể ghi nốt qua cổng LAN:

```bash
# trên máy tính: cắm Ethernet vào 1 trong 4 cổng LAN
ping 192.168.1.1                         # nếu không thấy, xem `ip addr` trên console
scp images/openwrt-gw040h-hybrid8.trx root@192.168.1.1:/tmp/fw
ssh root@192.168.1.1
```

```sh
# trên ONT (rescue system)
mtd write /tmp/fw tclinux
mtd write /tmp/fw tclinux_alt             # mirror, không bắt buộc
dd if=/tmp/fw of=/tmp/ubi bs=65536 skip=64   # UBI nằm sau 4 MiB kernel pad
ubidetach -d 0 2>/dev/null; ubidetach -m 4 2>/dev/null
ubiformat /dev/mtd4 -y -q -f /tmp/ubi
ubiattach -m 4 -d 0 && ubinfo -d 0        # phải thấy rootfs + rootfs_data
sync && reboot
```

Chỉ làm khi rescue system còn đang chạy; nếu đã reboot giữa chừng, quay lại quy trình UART.

### 5. Xác minh sau flash (Post-flash verification)

Sau khi reboot (khoảng 1–2 phút để WiFi lên), có thể xác minh bằng serial hoặc WiFi.

#### Qua serial
```bash
python3 tools/postflash_verify.py
```

Script sẽ đợi shell, kiểm tra:
- `/etc/openwrt_release`
- `/proc/mtd` (kiểm tra partition map)
- `ubinfo -a` (volumes UBI)
- Mount/overlay (`/overlay` rw, dung lượng)
- WiFi APs (`iw dev`, `ubus call network.wireless status`)
- LuCI (`uhttpd` chạy, HTTP 200)

#### Qua WiFi
1. Kết nối WiFi tới SSID **`OpenWrt`** (mở, không mật khẩu)
2. Mở trình duyệt → `http://192.168.1.1` (mặc định OpenWrt; firmware gốc của nhà mạng dùng `192.168.2.1`)
3. Login: `root` (mật khẩu trống ban đầu)

### 6. Bảo mật sau flash (Quan trọng)

Sau khi flash thành công, **hãy đặt mật khẩu ngay**. Mặc định WiFi mở và root không có mật khẩu.

Cách đặt qua LuCI: `System → Administration → Router Password` và `Network → Wireless → Wireless Security (WPA2-PSK/AES)`.

Hoặc qua SSH/serial (sau khi kết nối mạng): `passwd`

### 7. Khắc phục sự cố (Troubleshooting)

| Vấn đề | Nguyên nhân | Cách xử lý |
|---|---|---|
| Không thấy `bldr>` | Bootloader chưa vào chế độ nhận xmdm | Rút nguồn → chờ 5s → cắm lại nguồn khi script đang chạy. Thử lại vài lần. |
| `xflash12.py` treo lúc transfer | UART nhiễu/đảo TX-RX | Kiểm tra lại đấu dây TX/RX (đảo ngược). Giảm nhiễu dây. Thử lại. |
| `phaseE.py` báo MD5 mismatch | Ảnh staging bị corrupt khi đọc từ RAM | Thoát, kiểm tra serial không bị chiếm, chạy lại từ bước 4.1. |
| `phaseE.py` lỗi ubiformat | UBI vẫn attached | Script tự `ubidetach`, nếu vẫn lỗi: kiểm tra log, đảm bảo không có process khác dùng UBI. |
| Boot từ NAND không lên | Kernel/UBI sai | Dùng `tclinux_alt` (slot dự phòng). Có thể flash lại. Nếu hỏng nặng: cần staging lại rescue initramfs (xflash12). |
| Không thấy SSID `OpenWrt` | WiFi module chưa init kịp | Chờ ~1–2 phút sau reboot. Power cycle lại 1 lần. |
| RX UART bị nổi (bootloader vào download mode ngẫu nhiên) | Dây UART chưa tháo hoàn toàn | Sau khi xác minh ổn định (power cycle vài lần không cần UART vẫn boot), tháo jumper/dây UART. |

### 8. Phục hồi khẩn cấp (Recovery)

Nếu thiết bị bị brick (không boot), luôn có thể phục hồi qua UART:
1. Cắm lại USB-TTL, đảm bảo serial sạch
2. Chạy `python3 tools/xflash12.py` → power cycle ONT khi được yêu cầu
3. Sau khi có shell rescue (RAM), chạy `python3 tools/phaseE.py` để ghi lại NAND
4. Reboot

Slot `tclinux_alt` là bản sao dự phòng — bootloader có thể dùng nếu slot chính hỏng.

### 9. Ghi chú quan trọng

- **GPON không hỗ trợ.** Build này không có driver xpon/EN7571. WAN GPON không hoạt động — thiết bị chỉ dùng làm Router/AP WiFi.
- **4× GbE:** đã test nhanh 2026-10-19, cả 4 cổng LAN hoạt động (một `eth0` duy nhất được bridge vào `br-lan`; không có cổng WAN Ethernet riêng — WAN quang GPON không hỗ trợ).
- **Overlay UBI:** ~21–29 MiB có thể ghi (persistent). Thay đổi config sẽ được lưu trên `/overlay`.
- **Image hybrid:** `images/openwrt-gw040h-hybrid8.trx` là file cuối cùng đã flash (có header 2RDH). Các file `.trx` khác là các bản build trung gian.
- **An toàn:** Toàn bộ quy trình không xóa `bootloader`, `romfile`, `safedata`, `yaffs`, `reservearea` (chỉ ghi `tclinux`, `tclinux_alt`, `rootfs_ubi`).

---

## TUTORIAL (English)

### 1. Requirements

**Hardware:**
- VNPT GW040H ONT
- 3.3V USB-TTL adapter (CP2102/FT232RL recommended). **Do NOT use 5V.**
- Jumper wires to UART pads (GND, TX, RX)
- Stable power supply

**Software (Linux):**
- Python 3 + pyserial (`pip install pyserial` or `apt install python3-serial`)
- No other serial terminal (picocom/minicom/screen) must be running while flashing

### 2. Connect UART

Find GND/TX/RX pads on the PCB. Connect: USB-TTL RX → board TX, USB-TTL TX → board RX, GND↔GND. If no log appears, swap TX/RX.

Check device:
```bash
ls /dev/ttyUSB*
dmesg | tail -5
```

Default is `/dev/ttyUSB0`, 115200 8N1.

### 3. Prepare workspace

```bash
cd /path/to/gw040h-openwrt-project
chmod +x tools/*.py tools/*.sh
python3 -c "import serial; print('ok')"
```

### 4. Flash (RAM rescue → NAND)

Two phases:

**4.1 Stage rescue initramfs + firmware into RAM**
```bash
python3 tools/xflash12.py
```
- Waits for `bldr>` prompt. If not seen, power-cycle ONT (unplug 5s, plug in) when prompted.
- Transfers initramfs to `0x80020000` via xmdm, hybrid image to `0x85000000`
- Jumps to rescue kernel (runs entirely from RAM). Success = shell prompt (`/ #` or `root@OpenWrt:~#`)

**4.2 Write to NAND**
```bash
python3 tools/phaseE.py
```
- Waits for root shell, verifies staged image via `/dev/mem` (MD5)
- Writes `tclinux` (mtd2), verifies, mirrors to `tclinux_alt` (mtd3)
- Extracts UBI payload, formats `rootfs_ubi` (mtd4) with `ubiformat`, verifies volumes
- `sync` + reboot → boots from NAND

To bypass WiFi pre-check if needed: `SKIP_WIFI_CHECK=1 python3 tools/phaseE.py`

**Fallback if the UART adapter dies mid-flash (SSH):** the rescue initramfs runs `dropbear` with an empty root password. As long as NAND has not been touched yet, finish over the LAN:

```bash
# on the PC: plug Ethernet into one of the 4 LAN ports
scp images/openwrt-gw040h-hybrid8.trx root@192.168.1.1:/tmp/fw
ssh root@192.168.1.1
```

```sh
# on the ONT (rescue system)
mtd write /tmp/fw tclinux
mtd write /tmp/fw tclinux_alt                # mirror (optional)
dd if=/tmp/fw of=/tmp/ubi bs=65536 skip=64   # UBI follows the 4 MiB kernel pad
ubidetach -d 0 2>/dev/null; ubidetach -m 4 2>/dev/null
ubiformat /dev/mtd4 -y -q -f /tmp/ubi
ubiattach -m 4 -d 0 && ubinfo -d 0           # must list rootfs + rootfs_data
sync && reboot
```

Only works while the rescue system is still running; if it already rebooted, go back to the UART flow.

### 5. Verify

```bash
python3 tools/postflash_verify.py
```
Or WiFi: connect to `OpenWrt` (open) → `http://192.168.1.1` (OpenWrt default; the stock OEM firmware used `192.168.2.1`), login `root` (empty).

### 6. Secure it

Set WiFi security + root password immediately (LuCI → System → Administration, Network → Wireless).

### 7. Troubleshooting & Recovery

See Vietnamese section above for table. If bricked: rerun 4.1 then 4.2. `tclinux_alt` is the fallback slot.

### 8. Important notes

- **GPON unsupported.** No xpon/EN7571 driver — fibre WAN unusable (router/AP only).
- **4× GbE:** quick test on 2026-10-19 showed all 4 LAN ports working (single `eth0` bridged into `br-lan`; there is no dedicated Ethernet WAN port — fibre WAN via GPON is unsupported).
- **Security:** open WiFi + no root password by default — secure immediately.
- **UART removal:** After confirming stable boots across power-cycles with UART disconnected, you may remove the jumper/wiring. Keep pinout for recovery.

## Update / Cập nhật

- **2026-10-26:** Viết lại tài liệu: bảng trạng thái đã kiểm chứng, checksum ảnh, hướng dẫn build từ source, phương án dự phòng flash qua SSH, mục Known issues (LED/nút bấm/GPON/VoIP/sysupgrade), sửa IP LAN mặc định thành `192.168.1.1` (firmware gốc dùng `192.168.2.1`) và thống nhất kết quả test 4 cổng LAN. / Docs overhaul: verified status table, image checksums, build-from-source, SSH fallback, known issues, corrected default LAN IP to `192.168.1.1`, consistent 4×GbE result.
- 2026-10-19: Quick test confirmed **all 4 Ethernet ports work** (LAN). Updated documentation to reflect this.

