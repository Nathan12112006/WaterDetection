# Vision Monitoring Service

本文档面向调用视觉服务的后端开发者。视觉服务是独立 HTTP 服务，负责视频接入、视觉推理、事件确认、事件历史和按需画面；调用方负责业务告警、用户、权限、通知和审计。

## 文档导航

- [运行环境与部署](docs/vision-package/setup.md)
- [摄像头与运行配置](docs/vision-package/configuration.md)
- [HTTP API](docs/vision-package/api.md)
- [事件与补偿约定](docs/vision-package/events.md)
- [画面访问](docs/vision-package/frames.md)
- [Java 联调测试桩](docs/vision-package/java-harness.md)
- [测试与故障演练](docs/vision-package/testing.md)
- [数据库与迁移](docs/vision-package/database.md)
- [项目架构](docs/vision-package/architecture.md)

## 服务边界

视觉服务输出“视觉事件”，不是最终用户告警。事件状态为 `confirmed`、`updated` 或 `recovered`。调用方应按 `event_id + event_revision` 幂等处理，不根据单帧置信度自行重建事件。

视觉服务不规定调用方的操作系统、部署路径、Java 项目结构或通知供应商。服务地址、认证方式和事件接收地址由部署环境配置。

## 支持能力

- 多路文件、设备摄像头和 RTSP 输入；
- 每路独立监测状态和事件状态；
- 全图检测、变化区域检测、风险区域分割；
- 原始/标注快照；
- 事件历史、outbox 和补偿读取；
- 启动、停止、重启和健康查询。

## 部署与验收

部署、联调和验收按照架构、配置、API、事件、画面和测试文档执行。模型权重、现场视频源、硬件资源和验收阈值由项目部署配置及验收方案确定。
