# 事件与补偿约定

事件类型包括 `water_drop`、`pipe_burst`、`water_accumulation`。事件状态包括 `confirmed`、`updated`、`recovered`。

实时通知可能因网络抖动丢失。调用方应保存 `after_id` 游标，定期请求 `/api/v1/vision-events/compensation`，并按 `event_id + event_revision` 去重。

视觉服务不要求调用方直接访问视觉数据库表。正式事件接收 URL、认证、超时和重试上限需要部署双方另行确定。
