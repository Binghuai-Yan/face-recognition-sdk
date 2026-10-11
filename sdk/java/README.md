# Java SDK

Java 11+、Maven。仓库根目录运行 `mvn -f sdk/java/pom.xml install`，应用添加依赖 `com.facesdk:facesdk-java:1.0.0`。

```java
import com.facesdk.FaceSDK;
import com.facesdk.client.FaceSDKClient;
import java.nio.file.Files;
import java.nio.file.Path;

try (FaceSDK sdk = FaceSDK.builder()
        .apiUrl("http://localhost:8000")
        .detectionApiKey(System.getenv("FACESDK_DETECTION_API_KEY"))
        .recognitionApiKey(System.getenv("FACESDK_RECOGNITION_API_KEY"))
        .verificationApiKey(System.getenv("FACESDK_VERIFICATION_API_KEY"))
        .comparisonThreshold(0.8).build()) {
    FaceSDKClient client = sdk.getClient();
    byte[] image = Files.readAllBytes(Path.of("face.jpg"));
    System.out.println(client.detect(image).getFaceCount());
    System.out.println(client.compare(image, image).isMatch());
    System.out.println(client.search(image, 5, 0.8).getResults());
    System.out.println(client.extractFeature(image));
    client.createSubject("alice", "");
    client.addFace("alice", image, null);
    client.deleteSubject("alice");
}
```

builder 支持 Duration 类型的 connectTimeout、readTimeout、writeTimeout、retryDelay，默认 5/30/30 秒、500 毫秒，maxRetries 默认 3，verifySsl 默认 true。仅在显式开发测试配置下关闭 TLS 校验。服务方法抛出 `FaceSDKException`、`ApiException` 或 `NoFaceException`；调用者应处理失败，不要吞掉异常。

详见 [协议与兼容性](../../docs/protocol.md)。测试和源码/Javadoc 打包：`mvn -f sdk/java/pom.xml verify`。
