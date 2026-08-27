# 测试与故障演练

运行 Python 测试：`python -m unittest discover -s tests -p "test*.py" -v`。

建议验证：多路 Worker 均健康；单路停止不影响其他路；原始/标注画面返回 `200 image/jpeg`；Python 停止时 Java 代理返回 `502`；摄像头断流后可恢复；长时间运行期间无持续错误。

真实模型运行时记录每路 `frames_processed`、`frames_dropped`、`last_inference_latency_ms`、`inference_timeout_count` 以及 GPU 显存和利用率。
