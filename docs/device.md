# 实机与候选镜像

## 单台设备的观察值

| 项目 | 本例记录 |
| --- | --- |
| 产品 | 最美课本 M1 / NEXTClass.ai M1 |
| 平台 | MT6765 / MT8768T；引导层报告 hwcode 1894 |
| 内存 | 3 GB |
| CPU ABI | arm64-v8a，系统另支持 armeabi-v7a / armeabi |
| 内核 | Linux 4.9.117 |
| Treble / VNDK | Treble true；VNDK 28 |
| 启动布局 | 静态分区、无双槽；传统 system-as-root |
| system | p32，起始 0x50000000，长度 0x100000000（4 GiB） |
| vendor | p31，长度 0x32000000（800 MiB） |
| userdata | p35，23,413,636,608 字节，Android 显示的文件系统容量更小 |
| metadata | p8，33,554,432 字节 |
| 解锁状态 | unlocked；Orange State；当前 vbmeta flags=3 |
| 面板 | 1200×1920，原始 density 320 |

偏移和分区编号是复盘证据，不是其他机器的写入参数。必须重新读取自己的 GPT，并验证表头、分区项 CRC 和边界。同名设备的批次差异尚未调查。

## 为什么选择这个 GSI

实测文件为 `system-td-arm64-ab-vanilla.img.xz`，上游 [TrebleDroid ci-20240508](https://github.com/TrebleDroid/treble_experimentations/releases/tag/ci-20240508)。上游明确将它标为实验性发布，并提及旧内核设备修复。它并非当前最新镜像，也没有证明所有同平台设备兼容。

- ARM64 与系统架构匹配。
- 本例 `ab` 对应选择的 SAR 镜像布局，并不意味着这台平板存在 A/B 双槽。不能把该命名规则套用于所有项目。
- 展开长度为 2,022,539,264 字节，低于 system 分区上限。
- 镜像是 raw ext 文件系统，不是 Android sparse。
- 镜像内发现 VNDK 28 APEX；这是检查项，不是兼容性保证。
- VNDK 28 不自动等于需要 vndklite；本例先选择普通 vanilla。

## AVB 的三个层次

1. XZ 完整解码、文件系统检查和 SHA256 用于确认取得的文件及后续副本一致。
2. 原始 GSI 内嵌 AVB 的摘要和 RSA 签名曾核验通过，但信任止于镜像内嵌公钥；没有独立认证到厂商或发布者身份。未独立重算整个文件系统 hashtree。
3. 实机启动使用既有解锁状态和 vbmeta flags=3，保留原配置。本次没有把修改后的镜像伪装为厂商签名固件，也没有重新锁定引导。

flags=3 的含义参见 [AOSP avbtool](https://android.googlesource.com/platform/external/avb/+/master/avbtool.py)。关闭验证降低了启动信任保护，不能将 Orange State 消失作为此项目的目标。
