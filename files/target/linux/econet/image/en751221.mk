TRX_ENDIAN := be

define Device/chinamobile_gs3101
  DEVICE_VENDOR := ChinaMobile
  DEVICE_MODEL := GS3101
  DEVICE_DTS := en7526f_chinamobile_gs3101
  # KERNEL is built with kernel-trx, which ff-pads the kernel so the rootfs
  # always starts at 4 MiB (see PAD_ROOTFS_OFFSET_TO in tclinux-trx.sh) and
  # records that offset in the trx header. KERNEL_SIZE must therefore be at
  # least 4096k, otherwise the padded kernel fails the KERNEL_SIZE check
  # (and the subsequent "pad-to KERNEL_SIZE" would push the rootfs past the
  # offset the header advertises). Restored to 4096k accordingly.
  KERNEL_SIZE := 4096k
  NAND_SIZE := 256m
  KERNEL := kernel-bin | append-dtb | lzma | kernel-trx
  KERNEL_INITRAMFS := kernel-bin | append-dtb
  IMAGES := tclinux.trx sysupgrade.bin
  IMAGE/tclinux.trx := append-kernel | pad-to $$$$(KERNEL_SIZE) | append-ubi
  IMAGE/sysupgrade.bin := sysupgrade-tar | append-metadata
  DEVICE_PACKAGES := kmod-usb3 kmod-mt7603
endef
TARGET_DEVICES += chinamobile_gs3101

define Device/en751221_generic
  DEVICE_VENDOR := EN751221 Family
  DEVICE_MODEL := Initramfs Image
  DEVICE_TITLE := EN751221 Initramfs Image
  DEVICE_DESCRIPTION := In-memory build for testing and recovery of EN751221 SoCs
  DEVICE_DTS := en751221_generic
endef
TARGET_DEVICES += en751221_generic

define Device/huawei_hg2821t-u
  DEVICE_VENDOR := Huawei
  DEVICE_MODEL := HG2821T-U
  DEVICE_DTS := en751221_huawei_hg2821t-u
  KERNEL_DECOMPRESSED_SIZE := 7672k
  KERNEL_SIZE := 3328k
  IMAGE_SIZE := 57344k
  FACTORY_SIZE := 40960k
  NAND_SIZE := 256m
  KERNEL := kernel-bin | append-dtb | tclinux-free-bootbase-jump | \
    check-size $$(KERNEL_DECOMPRESSED_SIZE) | lzma
  KERNEL_INITRAMFS := kernel-bin | append-dtb
  IMAGES := kernel.bin rootfs.bin sysupgrade.bin
  IMAGE/kernel.bin := append-kernel
  IMAGE/rootfs.bin := append-ubi | check-size $$(FACTORY_SIZE)
  IMAGE/sysupgrade.bin := sysupgrade-tar | append-metadata
  DEVICE_PACKAGES := kmod-usb3
endef
TARGET_DEVICES += huawei_hg2821t-u

define Device/nokia_g240g-e
  DEVICE_VENDOR := Nokia
  DEVICE_MODEL := G-240G-E
  DEVICE_DTS := en751221_nokia_g240g-e
  IMAGES := tclinux.trx
  IMAGE/tclinux.trx := append-kernel | lzma | tclinux-trx
  DEVICE_PACKAGES := kmod-usb3
endef
TARGET_DEVICES += nokia_g240g-e

define Device/smartfiber_xp8421-b
  DEVICE_VENDOR := SmartFiber
  DEVICE_MODEL := XP8421-B
  DEVICE_DTS := en751221_smartfiber_xp8421-b
  IMAGES := tclinux.trx
  IMAGE/tclinux.trx := append-kernel | lzma | tclinux-trx
  DEVICE_PACKAGES := kmod-usb3 kmod-mt7603 kmod-mt76x2
endef
TARGET_DEVICES += smartfiber_xp8421-b

# NOTE: This will not work for upgrading from factory because it requires a cryptographic signature
#       however, it it can be flashed, then it will boot correctly.
define Device/tplink_archer-vr1200v-v2
  DEVICE_VENDOR := TP-Link
  DEVICE_MODEL := Archer vr1200v
  DEVICE_VARIANT := v2
  TPLINK_FLASHLAYOUT := 16Mmtk
  TPLINK_HWID := 0x0b473502
  TPLINK_HWREV := 0x0006007c
  TPLINK_HWREVADD := 0x0
  TPLINK_HVERSION := 3
  DEVICE_DTS := en751221_tplink_archer-vr1200v-v2
  DEVICE_PACKAGES := kmod-mt7603 kmod-mt7615e kmod-mt7663-firmware-ap
  IMAGES := sysupgrade.bin
  IMAGE/sysupgrade.bin := append-kernel | lzma | pad-to 4193792 | append-rootfs | \
    tplink-v2-header -R 0x400000
endef
TARGET_DEVICES += tplink_archer-vr1200v-v2

define Device/zyxel_pmg5617ga
  DEVICE_VENDOR := Zyxel
  DEVICE_MODEL := PMG5617GA
  DEVICE_DTS := en751221_zyxel_pmg5617ga
  IMAGES := tclinux.trx
  IMAGE/tclinux.trx := append-kernel | lzma | tclinux-trx
  DEVICE_PACKAGES := kmod-usb3 kmod-mt7603 kmod-mt76x2
endef
# VNPT GW040H: 2RDH/tclinux image written to the 12 MiB tclinux slot, UBI on
# the 34 MiB rootfs_ubi (OEM "data") region. The trx produced here is only a
# carrier - build_hybrid*.py turns its kernel+UBI into the 2RDH image (so the
# bootbase still sees a valid kernel+rootfs CRC) and phaseE.py writes the UBI
# part onto rootfs_ubi with ubiformat. IMAGE_SIZE nonetheless drives the
# UBI_NAND_SIZE_LIMIT guard in append-ubi (IMAGE_SIZE - 20/1024*NAND -
# 4*BLOCKSIZE), which assumes the UBI sits inside this image and is therefore
# far too small for us; 15360k makes that guard allow the whole 12 MiB tclinux
# window. FACTORY_SIZE is the real, enforced limit.
define Device/vnpt_gw040h
  DEVICE_VENDOR := VNPT
  DEVICE_MODEL := GW040H
  DEVICE_DTS := en751221_vnpt_gw040h
  KERNEL_DECOMPRESSED_SIZE := 7672k
  KERNEL_SIZE := 4096k
  IMAGE_SIZE := 15360k
  FACTORY_SIZE := 12288k
  NAND_SIZE := 128m
  KERNEL := kernel-bin | append-dtb | tclinux-free-bootbase-jump | \
    check-size $$(KERNEL_DECOMPRESSED_SIZE) | lzma
  KERNEL_INITRAMFS := kernel-bin | append-dtb
  IMAGES := tclinux.trx sysupgrade.bin
  IMAGE/tclinux.trx := append-kernel | pad-to $$$$(KERNEL_SIZE) | append-ubi | \
    check-size $$$$(FACTORY_SIZE)
  IMAGE/sysupgrade.bin := sysupgrade-tar | append-metadata
  DEVICE_PACKAGES := kmod-mt7615e kmod-mt7615-firmware wpad-basic-mbedtls luci-light
endef
TARGET_DEVICES += vnpt_gw040h
