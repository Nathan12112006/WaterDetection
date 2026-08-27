# HTTP API

以下路径相对于调用方配置的 `VISION_SERVICE_BASE_URL`。

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/health` | 服务和数据库健康检查 |
| GET | `/api/v1/monitoring/status` | 服务汇总和各 Worker 状态 |
| POST | `/api/v1/monitoring/start` | 启动全部监测；可选 `camera_id` |
| POST | `/api/v1/monitoring/stop` | 停止全部监测；可选 `camera_id` |
| POST | `/api/v1/monitoring/{camera_id}/restart` | 重启单路监测 |
| GET | `/api/v1/cameras/{camera_id}/snapshot` | 最近原始 JPEG 帧 |
| GET | `/api/v1/cameras/{camera_id}/annotated-snapshot` | 最近标注 JPEG 帧 |
| GET | `/api/v1/vision-events?after_id=0&limit=100` | 按游标读取事件 |
| GET | `/api/v1/vision-events/compensation?after_id=0&limit=100` | 补偿读取 |
| GET | `/api/v1/vision-events/{event_id}` | 读取事件全部 revision |

状态码：`200` 成功，`400` 参数错误，`404` 资源不存在，`503` 服务/数据库/画面暂不可用。调用方应按 `event_id + event_revision` 幂等处理。
