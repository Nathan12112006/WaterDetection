# Spring Boot 视觉模块联调测试桩

这个目录只用于验证 Python 视觉服务的接口，不实现正式后端告警业务、用户权限或手机推送。

## 启动

在安装 Maven 和 JDK 17 的环境中：

```powershell
mvn test
mvn spring-boot:run
```

默认监听 `http://127.0.0.1:18080`，Python 视觉服务默认地址为 `http://127.0.0.1:8000`，可通过 `VISION_BASE_URL` 或 `--vision.base-url=...` 调整。

## 联调接口

- `POST /mock/vision-events`：接收一条视觉事件；按 `event_id:event_revision` 幂等去重。
- `GET /mock/vision-events`：查看已接收事件。
- `GET /mock/cameras/{cameraId}/raw`：代理 Python 原始快照。
- `GET /mock/cameras/{cameraId}/annotated`：代理 Python 标注快照。

Java 测试桩使用内存存储，重启后数据清空；这符合“只测试视觉模块框架”的目标，不代表正式后端数据库设计。
