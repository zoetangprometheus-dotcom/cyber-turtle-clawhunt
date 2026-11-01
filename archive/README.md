# 项目完整归档索引

归档日期：2026-11-01。本次按项目所有者要求，将共享仓库外的 PRD、A 角色资料及早期前端版本同步到公开 GitHub 项目，保留原目录层级。当前代码、固件、交付文档和素材仍位于仓库根目录对应文件夹。

## 当前版本入口

| 内容 | 路径 |
|---|---|
| 项目启动、当前能力和限制 | [项目 README](../README.md) |
| 后端与协作契约 | [后端 Agent 说明](../docs/BACKEND_AGENT.md) |
| 前端、共享内容与校验 | h5/、data/、schemas/、tests/（仓库根目录） |
| ESP32 固件、Logo、构建脚本 | firmware/、scripts/firmware.py（仓库根目录）；[设备说明](../docs/ESP32_BRINGUP.md) |
| 实机验收与打印链路 | [设备验收](../docs/ESP32_ACCEPTANCE.md)、[打印中转](../docs/PRINT_BRIDGE.md) |
| AI 设置与扫码服务 | [AI 配置](../docs/AI_LOCAL_SETUP.md)、[扫码服务](../docs/WEB_LOCAL_SETUP.md) |
| 反馈模块与后续联调 | [震动与灯带](../docs/FEEDBACK_HARDWARE.md)、[后续集成](../docs/INTEGRATION_NEXT.md) |
| 商业方案与展示 | [成本与三分钟展示](../docs/COST_AND_3MIN_PITCH.md) |

## 原始项目资料

- [产品定位、PRD 与三人分工 v3.1](project-documents/赛博龟壳_产品定位_PRD_三人分工_v3.1.md)
- [A 角色任务与交付总表](project-documents/A-前端与内容/00-A角色任务与交付总表.md)
- [A 角色内容、提示词、H5 与交接资料](project-documents/A-前端与内容/)
- [早期整体框架 v0.1](project-documents/A-前端与内容/整体框架-v0.1/README.md)：包含阶段代码、研究原文、测试与截图。
- [首次 GitHub 协作交接](project-documents/GitHub协作交接-2026-10-31.md)
- [37 个原文件的大小与 SHA-256 清单](project-documents/manifest.json)

以上原件按字节复制，未改写历史内容；manifest 路径相对 project-documents/。旧文档中的当时状态、未实现功能、价格假设及“尚未公开项目资料”等描述仅表示历史情况，不覆盖当前实现。本次按新指令公开归档，并不将旧 PRD 所有条目视为已完成。后续开发以根目录代码及 docs/ 最新验收为准，历史区不做双向自动同步。

## 备份范围与恢复边界

本仓库保存源代码、固件源码与 Logo、前端素材、内容数据、提示词、接口约束、文档、测试、第三方来源和许可。未打包本地依赖、下载缓存、构建产物或固件二进制。

AI Key、设备秘密配置、真实签文/问答数据库、会话凭据及运行日志不进入公开 Git；已有忽略规则继续生效。克隆仓库后需要按启动说明重新准备依赖和配置自己的 AI Key，真实用户记录不会从本次 Git 归档恢复。

当前原型依赖 Mac USB 打印中转及临时 HTTPS 隧道；独立打印和灯带尚未完成。临时域名只保留调试记录，恢复环境时应重新启动服务并以当次可用地址为准。纸签渲染使用 macOS 本机字体，字体不随仓库分发。

构建脚本已记录下载校验值；其中 U8g2 的上游地址仍指向 master，若上游更新，校验会拒绝不同快照，后续应固定对应版本地址。本次未改动依赖方案，也未声称全新机器的离线恢复已验收。

第三方许可见 [来源说明](../THIRD_PARTY_NOTICES.md)。原创代码与项目素材的额外再许可仍由团队决定；本次归档不擅自新增许可证。
