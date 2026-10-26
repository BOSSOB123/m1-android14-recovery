# M1 tablet: boot recovery and Android 14 field notes

[中文完整文档](README.md)

A single-device case study of restoring a boot-blocked NEXTClass.ai / 最美课本 M1 tablet and running a TrebleDroid Android 14 GSI on its existing kernel and vendor partition.

The documented technical baseline was a previously working Android 11 phh GSI. It subsequently stopped reaching Android after boot-mode transitions. The precise original boot failure was not established. This repository does not claim to document a fully evidenced factory-to-Android-11 conversion or a recovery from damaged preloader firmware.

## Tested configuration

- MT6765 / MT8768T platform, ARM64, 3 GB RAM, Linux 4.9.117, VNDK 28.
- Static, slotless 4 GiB system partition, separate 800 MiB vendor partition.
- Unlocked bootloader and existing vbmeta flags 3.
- TrebleDroid `ci-20240508`, Android 14 / API 34, security patch 2024-05-05.
- Original boot, vendor, recovery, dtbo and partition table were preserved.

The upgrade went directly from Android 11 to 14. Existing FDE user data was discarded with the owner's explicit agreement. System write and complete readback matched. Android boot completion was verified.

## Scope and limitations

This is not OEM firmware, a universal unbricking guide or an automatic flasher. The old security patch, Bluetooth crash records, incomplete camera validation and untested rollback remain material limitations. The owner reports normal usability; this is not a comprehensive hardware certification.

Only documentation, original read-only Python tools and sanitized evidence are included. No firmware, proprietary APKs, private backups, device identities, accounts or proxy subscriptions are distributed.

```sh
python3 tools/verify_image.py /path/to/system.img.xz --expected-sha256 YOUR_EXPECTED_RAW_SHA256
python3 tools/gpt_report.py /path/to/gpt-primary.bin
python3 -m unittest discover -s tests -v
```

The image tool validates size, XZ decoding, ext superblock fields and an optional expected hash. It does not validate the complete filesystem, AVB trust or device compatibility. The GPT tool checks primary header/table CRCs and omits GUIDs; its output still requires review before sharing.

See the [Chinese guide](README.md) for the recovery sequence, evidence boundaries, fixes and upstream sources. Original material in this repository is MIT licensed; upstream licenses remain separate.
