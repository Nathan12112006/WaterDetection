# Java 联调测试桩

`integration/springboot-harness` 是可选的视觉模块联调工具，不是正式后端实现。它提供事件接收、revision 幂等验证和原始/标注画面代理。

默认接口：`POST /mock/vision-events`、`GET /mock/vision-events`、`GET /mock/cameras/{cameraId}/raw`、`GET /mock/cameras/{cameraId}/annotated`。

Python 服务停止时，画面代理返回 `502 Bad Gateway` 属于预期故障行为；Python 恢复且 Worker 健康后应恢复 `200 image/jpeg`。
