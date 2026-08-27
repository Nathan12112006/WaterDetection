# 画面访问

原始画面接口：`GET {VISION_SERVICE_BASE_URL}/api/v1/cameras/{camera_id}/snapshot`。

标注画面接口：`GET {VISION_SERVICE_BASE_URL}/api/v1/cameras/{camera_id}/annotated-snapshot`。

成功响应为 `200 image/jpeg`。没有处理过的帧返回 `503`，摄像头不存在返回 `404`。接口读取最近一次处理结果，不阻塞监测 Worker。

标注画面是否包含检测框或分割轮廓由视觉服务配置决定；调用方只选择原始或标注视图，不改变后台监测逻辑。
