# 摄像头与运行配置

配置是部署环境提供的 YAML 文件。每个摄像头写在 `monitoring.cameras` 下，并且必须有唯一 `camera_id`。

输入类型：

- `file`：字段 `path`、`loop`、`fps_limit`；
- `camera`：字段 `camera_index`、`fps_limit`；
- `rtsp`：字段 `uri`、`reconnect`、`reconnect_delay_seconds`。

示例：`camera_id: plant-zone-01`，`source: {type: rtsp, uri: rtsp://user:password@host/live, reconnect: true}`。

运行时参数位于 `monitoring.runtime`；分支参数位于 `monitoring.branches`；检测和分割模型位于 `models.detector` 与 `models.water_surface_seg`。

`backend: noop` 仅用于框架联调。生产识别使用 `yolo` 或 `yolo-seg`，并由部署环境提供权重路径和 GPU 设备。

风险区域使用 `risk_regions` 和 `exclude_polygons` 配置。`water_surface` 是分割证据，不等于已经确认的积水事件。
