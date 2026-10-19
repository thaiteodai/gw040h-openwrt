# Credits / Cảm ơn

## Core contributors / Người đóng góp chính
- Project lead / Người thực hiện: **[Your Name]** (the user who commissioned this work)

## Community research & references / Nghiên cứu cộng đồng và tham khảo

This project builds upon prior work and public resources, particularly:

- **vnptmodemresearch** (ResearcherPT): VNPT GPON ONT firmware analysis, tools, and reference dumps  
  https://github.com/ResearcherPT/vnptmodemresearch
  - telnet_password.py, romfileedit-h.py, asp-decoder.py
  - openwrt-initramfs-en751221
  - flashdump/, squashfs-modified/, gw040ns-firmware
- **OpenWrt Project**: upstream build system, kernel, packages, and the `target/linux/econet` target  
  https://openwrt.org/
- **Econet/Linux wiki** (bootloader quirks): tclinux/trx format and free-bootbase details  
  https://econet-linux.pkt.wiki/
- File decoders:  
  https://cfgdecoder.fkrystal.qzz.io/  
  https://huggingface.co/spaces/Expl01tHunt3r/file-decoder
- **ZyXEL trx/zytrx tools & documentation** (reference for JAMCRC/tclinux header layout)

## Special thanks / Lời cảm ơn đặc biệt
- The OpenWrt econet target maintainers and contributors for EN751221/EN7528 support
- Community members who published firmware dumps and analysis for VNPT ONTs

Credit is given to all referenced work. Any omissions are accidental — please contact to correct.

---

[English below]

# Credits / Cảm ơn (English)
The work referenced above was instrumental in understanding the 2RDH/trx format, Econet bootloader behavior, and partition layout. Where code fragments or design choices follow public analysis, attribution is provided.

