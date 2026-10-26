# GW040H build/flash log — "Option M" (writable overlay + LuCI + WiFi defaults)

> **Historical session log / ghi chú lịch sử.** Paths below (`/home/qyoo/openwrt-build`,
> `/home/qyoo/gw040h-openwrt`) refer to the build machine used at the time; the current
> tree is `openwrt/` next to this repo and `tools/build_hybrid8.py` now takes the built
> image as an argument (see `tools/README.md`). The recorded sizes/MD5 still match
> `images/openwrt-gw040h-hybrid8.trx`.

## Goal
Custom OpenWrt for VNPT GW040H (Econet EN751221, 256 MB RAM, 128 MB SPI NAND),
with **LuCI**, a **writable, persistent overlay**, dual-band WiFi, and flashing
done fully unattended over serial (`/dev/ttyUSB0`). The only management machine
available is **WiFi-only**, so the AP must come up on first boot without any
Ethernet cable.

## What changed this session

### Build tree (`/home/qyoo/openwrt-build`)
* `target/linux/econet/image/en751221.mk`
  * `chinamobile_gs3101` `KERNEL_SIZE` **3328k -> 4096k** (restored to HEAD).
    That device uses `kernel-trx`, which ff-pads the kernel so the rootfs always
    starts at 4 MiB (`PAD_ROOTFS_OFFSET_TO` in `tclinux-trx.sh`) and records that
    offset in the trx header. With `KERNEL_SIZE < 4096k` the padded kernel
    (always 4 MiB) fails `check-size` and the whole target fails to build; it also
    made the following `pad-to KERNEL_SIZE` push the rootfs past the offset the
    header advertises. `huawei_hg2821t-u` was left at 3328k (its kernel is not
    padded, and 3328k keeps more room for its UBI).
  * added the `vnpt_gw040h` device (this session's target): `KERNEL_SIZE 4096k`,
    `IMAGE_SIZE 15360k`, `FACTORY_SIZE 12288k`, `NAND_SIZE 128m`,
    `KERNEL := kernel-bin | append-dtb | tclinux-free-bootbase-jump | check-size $(KERNEL_DECOMPRESSED_SIZE) | lzma`,
    `IMAGE/tclinux.trx := append-kernel | pad-to KERNEL_SIZE | append-ubi`.
* `target/linux/econet/en751221/config-6.18`: `+CONFIG_DEVMEM=y` (needed so the
  rescue initramfs can read the staged image back through `/dev/mem`).
* `target/linux/econet/dts/en751221_vnpt_gw040h.dts` (new):
  * `rootfs_ubi` moved to the 34 MiB OEM `data` region: `reg = <0x1880000 0x2200000>`.
  * the OEM `data` node **removed**, so no second UBI can attach to the same region.
  * bootargs `console=ttyS0,115200 ubi.mtd=rootfs_ubi` (explicit `ubi.mtd=`
    disables auto-attach, which is what we want).
  * partition map (verified in the built DTB):

    | mtd | label        | offset    | size      |
    |-----|--------------|-----------|-----------|
    | 0   | bootloader   | 0x0       | 0x40000   |
    | 1   | romfile      | 0x40000   | 0x40000   |
    | 2   | tclinux      | 0x80000   | 0xc00000  |
    | 3   | tclinux_alt  | 0xc80000  | 0xc00000  |
    | 4   | rootfs_ubi   | 0x1880000 | 0x2200000 |
    | 5   | yaffs        | 0x3a80000 | 0x2400000 |
    | 6   | safedata     | 0x5e80000 | 0xa00000  |
    | 7   | reservearea  | 0x7520000 | 0x80000   |

* `files/etc/uci-defaults/99-wifi-ap` (new): on first boot, runs `wifi config`
  and flips every auto-generated `wireless.default_radioN` to `disabled=0`,
  i.e. brings up an **open** AP with the default SSID `OpenWrt` on both radios.
  Reason: `lib/wifi/mac80211.uc` leaves the AP `disabled` unless the board
  supplies WLAN defaults in `/etc/board.json`; this board has none. The script
  exits non-zero if no radios were detected so uci-defaults keeps and retries it.

### Why the overlay is now big
The UBI lives in the 34 MiB `rootfs_ubi` region (was an ~8 MiB window inside
`tclinux`), so the standard OpenWrt `rootfs_data` autoresize yields ~29 MiB.

## Build result
`make -j12` => `MAKE_EXIT=0`, no warnings.
`bin/targets/econet/en751221/`:
* `openwrt-econet-en751221-vnpt_gw040h-squashfs-tclinux.trx`     10092544 B
  (kernel region 4 MiB + UBI at 0x400000; `UBI#` verified at 0x400000)
* `openwrt-econet-en751221-vnpt_gw040h-initramfs-kernel.bin`     7701664 B (rescue)
* `openwrt-econet-en751221-vnpt_gw040h-squashfs-sysupgrade.bin`

Manifest contains `luci-light` + modules, `wpad-basic-mbedtls`,
`kmod-mt7615e`/`-common`/`-firmware`, `uhttpd`+`uhttpd-mod-ubus`,
`rpcd`+`rpcd-mod-luci`, `dnsmasq`, `firewall4`.

## Hybrid image
`build_hybrid8.py` wraps the trx in a 256-byte `2RDH` header (loadaddr
`0x80002000`, UBI forced to land at file offset `0x400000`):
`/home/qyoo/gw040h-openwrt/openwrt-gw040h-hybrid8.trx`
* size 10092544, `klen=0x3fff00`, `rootfslen=0x5a0000`, `crc=0xd610c057`
* md5 `7b4e7c972224e7dcb50d9e184fbf5380`

## Flash procedure (`autoflash9.sh`)
1. `xflash12.py` — reboot into `bldr>`, xmdm the rescue initramfs to `0x80020000`
   and hybrid8 to `0x85000000`, then `jump 80020000`.
2. `phaseE.py` — WiFi pre-check (`phy0` present, EEPROM valid), read the staged
   image back out of `/dev/mem` and check md5, `mtd write` it to `tclinux`,
   mirror to `tclinux_alt`, extract the UBI (`dd ... skip=64`) and
   `ubiformat` it onto `rootfs_ubi`, verify `rootfs`+`rootfs_data`, then reboot.

## After the flash — to verify
```
cat /etc/openwrt_release
cat /proc/mtd            # expect rootfs_ubi = 0x2200000, no data
ubinfo -a                # rootfs_data ~29 MiB
df -h                    # /overlay writable
ubus call network.wireless status | grep -E 'radio|"up"'
iw dev                   # phy0*/phy1* APs
```
Then, from the WiFi-only laptop: join SSID **OpenWrt** (open), browse
**http://192.168.1.1**, log in as **root** with an **empty password**
(`/etc/config/rpcd` maps root to `$p$root`, and `/etc/shadow` has an empty hash,
so any password is accepted — set a real one in LuCI immediately).

## Known limitations
* **GPON / EN7571 (xpon)** — no driver or firmware in this target; not possible.
* **4x GbE** — `econet_eth` exposes only `eth0`; the MT7530 ports are `disabled`
  in the DTS. Unverifiable from a WiFi-only host.
* The AP is **open** on first boot; secure it in LuCI right away.
