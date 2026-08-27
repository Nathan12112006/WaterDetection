# 运行环境与部署

## 运行时要求

- Python `>=3.11,<3.12`；
- 64 位操作系统；
- OpenCV 可访问摄像头或 RTSP；
- 使用 YOLO 时需要兼容的 PyTorch/CUDA 驱动；
- MySQL 5.7 仅在启用视觉事件持久化时需要。

依赖文件：`requirements.txt` 是基础运行依赖，`requirements-yolo.txt` 是真实 YOLO/YOLO-Seg 的可选依赖。部署系统可使用任意虚拟环境，不要求 Conda。

## 启动服务

安装依赖后，将环境变量 `VISION_CONFIG` 设置为部署环境中的 YAML 配置文件，再启动：

`python -m uvicorn water_workflow.api.app:app --host 0.0.0.0 --port 8000`

监听地址、端口和进程守护方式由部署系统或反向代理配置。调用方只使用约定的 `VISION_SERVICE_BASE_URL`。

## 健康检查

调用 `GET {VISION_SERVICE_BASE_URL}/api/v1/health`，并结合 `GET /api/v1/monitoring/status` 判断服务和各摄像头是否可用。
