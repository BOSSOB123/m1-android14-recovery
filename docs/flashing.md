# 本例实际刷写流程

这是一份操作记录和门槛说明，不是可粘贴执行的通用刷机命令。进入底层写入前，必须明确授权具体分区、数据丢失和回退边界。

## 为什么不能沿用原 data

原 Android 11 的 data 为 FDE 整盘加密。AOSP 已从 Android 13 移除 FDE 支持，见 [AOSP 全盘加密文档](https://source.android.com/docs/security/features/encryption/full-disk)。候选的旧 FDE 解密路径没有得到支持证据，因此保留原 data 的方案判为 NO-GO。

原机内核配置确认有 ext4/fs encryption；本次候选的固定源码还将旧 forcefdeorfbe 标记映射到 FBE 参数。但这两项只提供准备依据，最终仍以实机能建立并挂载新 data 为准。

源码参考：[该候选对应 system/core 的 fstab 解析](https://github.com/TrebleDroid/platform_system_core/blob/069ddcf0f5dc70dd4e8ea2355c5c023f6642811c/fs_mgr/libfstab/fstab.cpp)。

## 成功执行的顺序

1. 核验本地候选长度和 SHA256，确认恢复材料完整，明确旧个人数据不保留。
2. 通过离线通道确认芯片、机主自己的设备身份、eMMC 类型/容量，重新读取 GPT 并校验 CRC。
3. 用自己的 GPT 确认 system、userdata、metadata、vbmeta 边界；确认当前 vbmeta 为预期 flags=3。
4. 只把原始 Android 14 GSI 写到 system。**不写 boot/vendor/recovery/dtbo/vbmeta/GPT 或 preloader。**
5. 从设备完整读回与源镜像相同的字节数，重新计算 SHA256；任何失败都停止，不继续清 data。
6. 仅在已经明确获得丢弃数据授权的前提下，清除 userdata 和 metadata，允许 Android 14 重建数据。
7. 再核对 GPT 和 vbmeta 与写入前一致。
8. 尝试正常启动；底层 shutdown 返回成功仍不等于安卓开机。
9. 等待实际屏幕与 ADB，确认 API 34、预期系统和 `sys.boot_completed=1`；再检查 data 挂载及 FBE。

读取前 4096 字节为空，只是清除命令之后的头部抽查，不能称为整分区安全擦除或完整数据销毁证明。

## 串口传输经验

第一次 system 写入返回失败，执行在清 data 之前停止；第二次调整工作区包装器后成功。局部失败并不保证 system 保持原状。

针对本例的 MTKClient/macOS 串口路径，工作包装器采用：

- 握手有总期限和小的读写超时，避免无限等待读取。
- Preloader 握手与 DA bulk 阶段分开；只有切到 bulk 阶段才使用流式发送。
- 每次最多发送 65536 字节，正确推进部分写入的偏移；零进度视为错误。
- XFLASH 参数按其协议头和数据长度分块，读回设备状态并检查返回值。
- 使用本机 boot1 中的 EMI 数据初始化 DRAM，绝不把这理解为需要写入 boot1。

这些是本例调试经验，不是上游通用修复结论。本仓库不包含能绕过版本、身份和分区核验的 monkey patch 或自动 flasher。若要工程化写入工具，应首先增加协议测试、断点失败恢复、版本兼容检查和人工确认界面。

## 成功证据

原始 GSI 的写入长度和完整读回为 **2,022,539,264 字节**，SHA256 为 `0c3276a30b0a45b9b87eb629d50d90fb1dafbbb8e556f0b5dd60dcc4ef22d42d`。GPT 与 vbmeta 前后一致，Android 14 实际开机完成。脱敏摘要见 [verification.json](../manifests/verification.json)。
