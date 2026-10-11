# Go SDK

使用本仓库模块 `github.com/facesdk/facesdk-go`，本地集成可在应用 go.mod 添加：

```go
replace github.com/facesdk/facesdk-go => ../faceSdk/sdk/go
```

```go
package main
import (
    "context"
    "fmt"
    "os"
    facesdk "github.com/facesdk/facesdk-go"
)
func main() {
    client := facesdk.NewClient("http://localhost:8000", "", facesdk.WithAPIKeys(map[string]string{
        "detection": os.Getenv("FACESDK_DETECTION_API_KEY"),
        "recognition": os.Getenv("FACESDK_RECOGNITION_API_KEY"),
        "verification": os.Getenv("FACESDK_VERIFICATION_API_KEY"),
    }))
    result, err := client.Detect(context.Background(), "face.jpg", nil)
    if err != nil { panic(err) }
    fmt.Println(result.FaceCount)
}
```

提供 Detect/Compare/Search/ExtractFeature 的文件、FromBytes、FromReader(s) 方法。Subject 方法为 CreateSubject、ListSubjects、DeleteSubject；人脸方法为 AddFace/FromBytes/FromReader、DeleteFace。每个方法接收 context，可取消请求和重试等待。

选项包含 WithHTTPClient、WithMaxRetries、WithRetryDelay、WithAPIKeys、WithComparisonThreshold；默认请求超时 30 秒，重试 3 次，初始延迟 500ms，比对阈值 0.8。`APIError.HTTPStatusCode` 可用于错误分类。

详见 [协议](../../docs/protocol.md)。在本目录运行 `go test ./... && go vet ./...`；有 C 编译器时可运行 `go test -race ./...`。
