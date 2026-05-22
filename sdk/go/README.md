# FaceSDK Go SDK

FaceSDK Go 客户端库，提供人脸识别、人脸检测、人脸比对等功能。

## 安装

```bash
go get github.com/facesdk/facesdk-go
```

## 快速开始

```go
package main

import (
    "context"
    "fmt"
    "log"
    
    "github.com/facesdk/facesdk-go"
)

func main() {
    // 创建客户端
    client := facesdk.NewClient(
        "http://localhost:8000",
        "your-api-key",
        facesdk.WithMaxRetries(3),
        facesdk.WithRetryDelay(500*time.Millisecond),
    )

    ctx := context.Background()

    // 人脸检测
    result, err := client.Detect(ctx, "/path/to/image.jpg", nil)
    if err != nil {
        log.Fatal(err)
    }
    fmt.Printf("检测到 %d 张人脸\n", result.FaceCount)

    // 人脸比对
    compareResult, err := client.Compare(ctx, "/path/to/face1.jpg", "/path/to/face2.jpg")
    if err != nil {
        log.Fatal(err)
    }
    fmt.Printf("相似度: %.2f, 是否匹配: %v\n", compareResult.Similarity, compareResult.Match)

    // 人脸识别（1:N）
    searchResult, err := client.Search(ctx, "/path/to/query.jpg", 5, 0.0)
    if err != nil {
        log.Fatal(err)
    }
    for _, match := range searchResult.Results {
        fmt.Printf("Subject: %s, 相似度: %.2f\n", match.SubjectID, match.Similarity)
    }

    // 创建人脸库
    subject, err := client.CreateSubject(ctx, "user_001", "张三")
    if err != nil {
        log.Fatal(err)
    }
    fmt.Printf("创建人脸库: %s\n", subject.SubjectID)

    // 添加人脸
    record, err := client.AddFace(ctx, "user_001", "/path/to/face.jpg", nil)
    if err != nil {
        log.Fatal(err)
    }
    fmt.Printf("添加人脸: %s\n", record.ImageID)
}
```

## 错误处理

```go
result, err := client.Detect(ctx, "/path/to/image.jpg", nil)
if err != nil {
    if apiErr, ok := err.(*facesdk.APIError); ok {
        fmt.Printf("API 错误: %s (HTTP %d)\n", apiErr.Message, apiErr.HTTPStatusCode)
    } else {
        fmt.Printf("其他错误: %v\n", err)
    }
    return
}
```

## 许可证

MIT License
