# 检测负载测试

需要 wrk、运行中的 CompreFace、Detection 服务密钥和真实单脸 JPEG。Linux/macOS：

```sh
export FACESDK_DETECTION_API_KEY='<Detection 密钥>'
export TEST_IMAGE_PATH='/path/to/face.jpg'
wrk -t4 -c10 -d30s -s tests/performance/wrk/face_detect.lua http://localhost:8000/api/v1/detection/detect
```

按实际业务容量逐步增加并发，核对非 2xx 数量及延迟；吞吐量不能替代识别精度验证。脚本汇总每个线程的 HTTP 状态，连接/读写/超时错误、零请求或非 2xx 会返回非零退出码。本次 WSL 的真实检测结果见 [测试报告](../../../docs/repair-report-2026-10-11.md)。

JMeter 方案位于相邻 jmeter 目录，使用 api_url、detection_api_key、verification_api_key、test_image_path properties。密钥建议放在忽略目录的私密 properties 文件中，通过 -q 加载。小规模验证可使用 `-Jdetection_threads=2 -Jverification_threads=1 -Jloops=2 -Jramp_seconds=1`。输出使用新 JTL 文件，不要把结果解释为生产容量承诺。
