# FaceSDK Java SDK

FaceSDK Java 客户端库，提供人脸识别、人脸检测、人脸比对等功能。

## 安装

### Maven

```xml
<dependency>
    <groupId>com.facesdk</groupId>
    <artifactId>facesdk-java</artifactId>
    <version>1.0.0</version>
</dependency>
```

### Gradle

```groovy
implementation 'com.facesdk:facesdk-java:1.0.0'
```

## 快速开始

### 1. 初始化客户端

```java
import com.facesdk.FaceSDK;
import com.facesdk.client.FaceSDKClient;

FaceSDK sdk = FaceSDK.builder()
    .apiUrl("http://localhost:8000")
    .apiKey("your-api-key")
    .connectTimeout(Duration.ofSeconds(5))
    .readTimeout(Duration.ofSeconds(30))
    .maxRetries(3)
    .build();

FaceSDKClient client = sdk.getClient();
```

### 2. 人脸检测

```java
import com.facesdk.model.DetectionResult;
import com.facesdk.model.Face;

// 从文件检测
File imageFile = new File("/path/to/image.jpg");
DetectionResult result = client.detect(imageFile);

// 从字节数组检测
byte[] imageData = Files.readAllBytes(imageFile.toPath());
DetectionResult result = client.detect(imageData);

// 处理结果
System.out.println("检测到 " + result.getFaceCount() + " 张人脸");
for (Face face : result.getFaces()) {
    System.out.println("置信度: " + face.getConfidence());
    System.out.println("位置: " + face.getBoundingBox());
}
```

### 3. 人脸比对

```java
import com.facesdk.model.CompareResult;

byte[] image1 = Files.readAllBytes(new File("/path/to/face1.jpg").toPath());
byte[] image2 = Files.readAllBytes(new File("/path/to/face2.jpg").toPath());

CompareResult result = client.compare(image1, image2);

System.out.println("相似度: " + result.getSimilarity());
System.out.println("是否匹配: " + result.isMatch());
```

### 4. 人脸识别（1:N）

```java
import com.facesdk.model.SearchResult;

byte[] imageData = Files.readAllBytes(new File("/path/to/query.jpg").toPath());
SearchResult result = client.search(imageData, 5); // 返回前5个结果

for (SearchResult.MatchResult match : result.getResults()) {
    System.out.println("Subject: " + match.getSubjectId());
    System.out.println("相似度: " + match.getSimilarity());
}
```

### 5. 人脸库管理

```java
import com.facesdk.model.Subject;
import com.facesdk.model.FaceRecord;

// 创建人脸库
Subject subject = client.createSubject("user_001", "张三");

// 添加人脸
byte[] faceImage = Files.readAllBytes(new File("/path/to/face.jpg").toPath());
Map<String, Object> metadata = new HashMap<>();
metadata.put("source", "camera_01");
FaceRecord record = client.addFace("user_001", faceImage, metadata);

// 列出所有人脸库
List<Subject> subjects = client.listSubjects();

// 删除人脸库
client.deleteSubject("user_001");
```

## 配置选项

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| apiUrl | - | API 基础 URL |
| apiKey | - | API 密钥 |
| connectTimeout | 5s | 连接超时时间 |
| readTimeout | 30s | 读取超时时间 |
| writeTimeout | 30s | 写入超时时间 |
| maxRetries | 3 | 最大重试次数 |
| retryDelay | 500ms | 重试延迟 |
| verifySsl | true | 是否验证 SSL 证书 |

## 异常处理

```java
try {
    DetectionResult result = client.detect(imageData);
} catch (NoFaceException e) {
    // 未检测到人脸
    System.err.println("未检测到人脸: " + e.getMessage());
} catch (ApiException e) {
    // API 调用失败
    System.err.println("API 错误: " + e.getMessage());
    System.err.println("HTTP 状态码: " + e.getHttpStatusCode());
} catch (FaceSDKException e) {
    // 其他 SDK 错误
    System.err.println("SDK 错误: " + e.getMessage());
}
```

## Spring Boot 集成

```java
@Configuration
public class FaceSDKConfig {

    @Bean
    public FaceSDKClient faceSDKClient(
            @Value("${facesdk.api-url}") String apiUrl,
            @Value("${facesdk.api-key}") String apiKey) {
        
        FaceSDK sdk = FaceSDK.builder()
            .apiUrl(apiUrl)
            .apiKey(apiKey)
            .build();
        
        return sdk.getClient();
    }
}
```

## 许可证

MIT License
