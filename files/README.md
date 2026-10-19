# Source modifications / Thay đổi mã nguồn

[Tiếng Việt dưới đây. [English below.]]

## Tiếng Việt
Các thay đổi cần thêm vào cây OpenWrt để build thành công cho VNPT GW040H.

## English
Modifications to the OpenWrt tree required to build for VNPT GW040H.

Structure mirrors OpenWrt tree layout:
- `target/linux/econet/dts/en751221_vnpt_gw040h.dts` — device DTS
- `target/linux/econet/image/en751221.mk` — device definition (vnpt_gw040h)
- `target/linux/econet/en751221/config-6.18` — kernel config diff (CONFIG_DEVMEM=y)
- `files/etc/uci-defaults/99-wifi-ap` — enables APs on first boot (WiFi-only access)
