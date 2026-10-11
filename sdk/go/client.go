// File: facesdk/sdk/go/client.go
// Copyright (c) 2024 FaceSDK Contributors
// MIT License
//
// FaceSDK Go Client

package facesdk

import (
	"bytes"
	"context"
	"encoding/base64"
	"encoding/binary"
	"encoding/json"
	"fmt"
	"io"
	"math"
	"mime/multipart"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"time"
)

// Client FaceSDK 客户端
type Client struct {
	apiURL              string
	apiKey              string
	httpClient          *http.Client
	maxRetries          int
	retryDelay          time.Duration
	apiKeys             map[string]string
	comparisonThreshold float64
}

// WithAPIKeys selects the key for each CompreFace service (detection, recognition, verification).
func WithAPIKeys(keys map[string]string) ClientOption {
	return func(c *Client) {
		c.apiKeys = make(map[string]string, len(keys))
		for service, key := range keys {
			c.apiKeys[service] = key
		}
	}
}

// WithComparisonThreshold sets the client-side 1:1 similarity threshold.
func WithComparisonThreshold(threshold float64) ClientOption {
	return func(c *Client) { c.comparisonThreshold = threshold }
}

// ClientOption 客户端配置选项
type ClientOption func(*Client)

// WithHTTPClient 设置自定义 HTTP 客户端
func WithHTTPClient(httpClient *http.Client) ClientOption {
	return func(c *Client) {
		c.httpClient = httpClient
	}
}

// WithMaxRetries 设置最大重试次数
func WithMaxRetries(maxRetries int) ClientOption {
	return func(c *Client) {
		c.maxRetries = maxRetries
	}
}

// WithRetryDelay 设置重试延迟
func WithRetryDelay(retryDelay time.Duration) ClientOption {
	return func(c *Client) {
		c.retryDelay = retryDelay
	}
}

// NewClient 创建新的 FaceSDK 客户端
func NewClient(apiURL, apiKey string, opts ...ClientOption) *Client {
	client := &Client{
		apiURL:              strings.TrimRight(apiURL, "/"),
		apiKey:              apiKey,
		httpClient:          &http.Client{Timeout: 30 * time.Second},
		maxRetries:          3,
		retryDelay:          500 * time.Millisecond,
		comparisonThreshold: 0.8,
	}

	for _, opt := range opts {
		opt(client)
	}

	return client
}

// request 发送 HTTP 请求
func (c *Client) request(ctx context.Context, method, endpoint string, body io.Reader, contentType string) ([]byte, error) {
	requestURL := c.apiURL + endpoint
	if c.maxRetries < 0 || c.retryDelay < 0 {
		return nil, fmt.Errorf("invalid retry configuration")
	}
	var payload []byte
	var err error
	if body != nil {
		payload, err = io.ReadAll(body)
		if err != nil {
			return nil, fmt.Errorf("failed to buffer request: %w", err)
		}
	}
	parts := strings.Split(strings.SplitN(endpoint, "?", 2)[0], "/")
	key := c.apiKey
	if serviceKey, ok := c.apiKeys[parts[3]]; ok {
		key = serviceKey
	}
	if key == "" {
		return nil, fmt.Errorf("missing API key for %s", parts[3])
	}
	safe := method == http.MethodGet || method == http.MethodDelete ||
		parts[len(parts)-1] == "detect" || parts[len(parts)-1] == "verify" || parts[len(parts)-1] == "recognize"
	retries := 0
	if safe {
		retries = c.maxRetries
	}

	var lastErr error
	for attempt := 0; attempt <= retries; attempt++ {
		if err := ctx.Err(); err != nil {
			return nil, err
		}
		req, err := http.NewRequestWithContext(ctx, method, requestURL, bytes.NewReader(payload))
		if err != nil {
			return nil, fmt.Errorf("failed to create request: %w", err)
		}

		req.Header.Set("x-api-key", key)
		if contentType != "" {
			req.Header.Set("Content-Type", contentType)
		}

		resp, err := c.httpClient.Do(req)
		if err != nil {
			lastErr = err
			if attempt < retries {
				if err := c.waitRetry(ctx, attempt); err != nil {
					return nil, err
				}
				continue
			}
			return nil, fmt.Errorf("request failed after %d attempts: %w", retries+1, lastErr)
		}

		respBody, err := io.ReadAll(resp.Body)
		resp.Body.Close()
		if err != nil {
			return nil, fmt.Errorf("failed to read response body: %w", err)
		}

		if attempt < retries && (resp.StatusCode == 429 || resp.StatusCode == 500 || resp.StatusCode == 502 || resp.StatusCode == 503 || resp.StatusCode == 504) {
			if err := c.waitRetry(ctx, attempt); err != nil {
				return nil, err
			}
			continue
		}
		if resp.StatusCode < 200 || resp.StatusCode >= 300 {
			return nil, c.handleErrorResponse(resp.StatusCode, respBody)
		}

		return respBody, nil
	}

	return nil, fmt.Errorf("request failed after %d attempts: %w", retries+1, lastErr)
}

func (c *Client) waitRetry(ctx context.Context, attempt int) error {
	timer := time.NewTimer(c.retryDelay * time.Duration(1<<uint(attempt)))
	defer timer.Stop()
	select {
	case <-ctx.Done():
		return ctx.Err()
	case <-timer.C:
		return nil
	}
}

// handleErrorResponse 处理错误响应
func (c *Client) handleErrorResponse(statusCode int, body []byte) error {
	var errResp struct {
		Message string `json:"message"`
		Error   string `json:"error"`
	}
	json.Unmarshal(body, &errResp)

	message := errResp.Message
	if message == "" {
		message = errResp.Error
	}
	if message == "" {
		message = "unknown error"
	}

	return &APIError{
		Message:        message,
		HTTPStatusCode: statusCode,
	}
}

// Detect 人脸检测
func (c *Client) Detect(ctx context.Context, imagePath string, options map[string]string) (*DetectionResult, error) {
	file, err := os.Open(imagePath)
	if err != nil {
		return nil, fmt.Errorf("failed to open image: %w", err)
	}
	defer file.Close()

	return c.DetectFromReader(ctx, file, filepath.Base(imagePath), options)
}

// DetectFromBytes 从字节数组检测人脸
func (c *Client) DetectFromBytes(ctx context.Context, imageData []byte, options map[string]string) (*DetectionResult, error) {
	return c.DetectFromReader(ctx, bytes.NewReader(imageData), "image.jpg", options)
}

// DetectFromReader 从 Reader 检测人脸
func (c *Client) DetectFromReader(ctx context.Context, reader io.Reader, filename string, options map[string]string) (*DetectionResult, error) {
	var buf bytes.Buffer
	writer := multipart.NewWriter(&buf)

	part, err := writer.CreateFormFile("file", filename)
	if err != nil {
		return nil, fmt.Errorf("failed to create form file: %w", err)
	}

	if _, err := io.Copy(part, reader); err != nil {
		return nil, fmt.Errorf("failed to copy image data: %w", err)
	}

	if err := writer.Close(); err != nil {
		return nil, fmt.Errorf("failed to close writer: %w", err)
	}

	params := url.Values{}
	for key, value := range options {
		params.Set(key, value)
	}
	endpoint := "/api/v1/detection/detect"
	if len(params) > 0 {
		endpoint += "?" + params.Encode()
	}
	body, err := c.request(ctx, http.MethodPost, endpoint, &buf, writer.FormDataContentType())
	if err != nil {
		return nil, err
	}

	var result DetectionResult
	if err := json.Unmarshal(body, &result); err != nil {
		return nil, fmt.Errorf("failed to unmarshal response: %w", err)
	}

	return &result, nil
}

// Compare 人脸比对
func (c *Client) Compare(ctx context.Context, imagePath1, imagePath2 string) (*CompareResult, error) {
	file1, err := os.Open(imagePath1)
	if err != nil {
		return nil, fmt.Errorf("failed to open image1: %w", err)
	}
	defer file1.Close()

	file2, err := os.Open(imagePath2)
	if err != nil {
		return nil, fmt.Errorf("failed to open image2: %w", err)
	}
	defer file2.Close()

	return c.CompareFromReaders(ctx, file1, filepath.Base(imagePath1), file2, filepath.Base(imagePath2))
}

// CompareFromBytes 从字节数组比对人脸
func (c *Client) CompareFromBytes(ctx context.Context, imageData1, imageData2 []byte) (*CompareResult, error) {
	return c.CompareFromReaders(ctx, bytes.NewReader(imageData1), "image1.jpg", bytes.NewReader(imageData2), "image2.jpg")
}

// CompareFromReaders 从 Reader 比对人脸
func (c *Client) CompareFromReaders(ctx context.Context, reader1 io.Reader, filename1 string, reader2 io.Reader, filename2 string) (*CompareResult, error) {
	var buf bytes.Buffer
	writer := multipart.NewWriter(&buf)

	part1, err := writer.CreateFormFile("source_image", filename1)
	if err != nil {
		return nil, fmt.Errorf("failed to create form file1: %w", err)
	}
	if _, err := io.Copy(part1, reader1); err != nil {
		return nil, fmt.Errorf("failed to copy image1 data: %w", err)
	}

	part2, err := writer.CreateFormFile("target_image", filename2)
	if err != nil {
		return nil, fmt.Errorf("failed to create form file2: %w", err)
	}
	if _, err := io.Copy(part2, reader2); err != nil {
		return nil, fmt.Errorf("failed to copy image2 data: %w", err)
	}

	if err := writer.Close(); err != nil {
		return nil, fmt.Errorf("failed to close writer: %w", err)
	}

	body, err := c.request(ctx, http.MethodPost, "/api/v1/verification/verify", &buf, writer.FormDataContentType())
	if err != nil {
		return nil, err
	}

	var raw struct {
		Result []struct {
			Source  Face `json:"source_image_face"`
			Matches []struct {
				Face
				Similarity float64 `json:"similarity"`
			} `json:"face_matches"`
		} `json:"result"`
	}
	if err := json.Unmarshal(body, &raw); err != nil {
		return nil, fmt.Errorf("failed to unmarshal response: %w", err)
	}
	if len(raw.Result) != 1 || len(raw.Result[0].Matches) != 1 {
		return nil, fmt.Errorf("comparison requires exactly one face in each image")
	}
	if math.IsNaN(c.comparisonThreshold) || c.comparisonThreshold < 0 || c.comparisonThreshold > 1 {
		return nil, fmt.Errorf("invalid comparison threshold")
	}
	target := raw.Result[0].Matches[0]
	target.Face = normalizeFace(target.Face)
	raw.Result[0].Source = normalizeFace(raw.Result[0].Source)
	return &CompareResult{Similarity: target.Similarity, Threshold: c.comparisonThreshold, Match: target.Similarity >= c.comparisonThreshold, Face1: &raw.Result[0].Source, Face2: &target.Face}, nil
}

// Search 人脸识别（1:N）
func (c *Client) Search(ctx context.Context, imagePath string, limit int, threshold float64) (*SearchResult, error) {
	file, err := os.Open(imagePath)
	if err != nil {
		return nil, fmt.Errorf("failed to open image: %w", err)
	}
	defer file.Close()

	return c.SearchFromReader(ctx, file, filepath.Base(imagePath), limit, threshold)
}

// SearchFromBytes 从字节数组搜索人脸
func (c *Client) SearchFromBytes(ctx context.Context, imageData []byte, limit int, threshold float64) (*SearchResult, error) {
	return c.SearchFromReader(ctx, bytes.NewReader(imageData), "image.jpg", limit, threshold)
}

// SearchFromReader 从 Reader 搜索人脸
func (c *Client) SearchFromReader(ctx context.Context, reader io.Reader, filename string, limit int, threshold float64) (*SearchResult, error) {
	if limit < 1 || math.IsNaN(threshold) || threshold < 0 || threshold > 1 {
		return nil, fmt.Errorf("invalid search limit or threshold")
	}
	var buf bytes.Buffer
	writer := multipart.NewWriter(&buf)

	part, err := writer.CreateFormFile("file", filename)
	if err != nil {
		return nil, fmt.Errorf("failed to create form file: %w", err)
	}

	if _, err := io.Copy(part, reader); err != nil {
		return nil, fmt.Errorf("failed to copy image data: %w", err)
	}

	if err := writer.Close(); err != nil {
		return nil, fmt.Errorf("failed to close writer: %w", err)
	}

	body, err := c.request(ctx, http.MethodPost, "/api/v1/recognition/recognize?prediction_count="+strconv.Itoa(limit), &buf, writer.FormDataContentType())
	if err != nil {
		return nil, err
	}

	var result SearchResult
	if err := json.Unmarshal(body, &result); err != nil {
		return nil, fmt.Errorf("failed to unmarshal response: %w", err)
	}
	filtered := make([]MatchResult, 0, len(result.Results))
	for _, match := range result.Results {
		if match.Similarity >= threshold {
			match.Match = true
			filtered = append(filtered, match)
		}
	}
	sort.SliceStable(filtered, func(i, j int) bool { return filtered[i].Similarity > filtered[j].Similarity })
	result.Results = filtered

	return &result, nil
}

// ExtractFeature 提取人脸特征向量
func (c *Client) ExtractFeature(ctx context.Context, imagePath string) (string, error) {
	file, err := os.Open(imagePath)
	if err != nil {
		return "", fmt.Errorf("failed to open image: %w", err)
	}
	defer file.Close()

	return c.ExtractFeatureFromReader(ctx, file, filepath.Base(imagePath))
}

// ExtractFeatureFromBytes 从字节数组提取人脸特征向量
func (c *Client) ExtractFeatureFromBytes(ctx context.Context, imageData []byte) (string, error) {
	return c.ExtractFeatureFromReader(ctx, bytes.NewReader(imageData), "image.jpg")
}

// ExtractFeatureFromReader 从 Reader 提取人脸特征向量
func (c *Client) ExtractFeatureFromReader(ctx context.Context, reader io.Reader, filename string) (string, error) {
	var buf bytes.Buffer
	writer := multipart.NewWriter(&buf)

	part, err := writer.CreateFormFile("file", filename)
	if err != nil {
		return "", fmt.Errorf("failed to create form file: %w", err)
	}

	if _, err := io.Copy(part, reader); err != nil {
		return "", fmt.Errorf("failed to copy image data: %w", err)
	}

	if err := writer.Close(); err != nil {
		return "", fmt.Errorf("failed to close writer: %w", err)
	}

	body, err := c.request(ctx, http.MethodPost, "/api/v1/detection/detect?face_plugins=calculator", &buf, writer.FormDataContentType())
	if err != nil {
		return "", err
	}

	var result DetectionResult
	if err := json.Unmarshal(body, &result); err != nil {
		return "", fmt.Errorf("failed to unmarshal response: %w", err)
	}

	if len(result.Faces) != 1 {
		return "", fmt.Errorf("feature extraction requires exactly one face")
	}
	embedding := result.Faces[0].Embedding
	if len(embedding) == 0 {
		return "", fmt.Errorf("calculator plugin did not return an embedding")
	}
	encoded := make([]byte, len(embedding)*4)
	for i, value := range embedding {
		binary.LittleEndian.PutUint32(encoded[i*4:], math.Float32bits(value))
	}
	return base64.StdEncoding.EncodeToString(encoded), nil
}

// CreateSubject 创建人脸库
func (c *Client) CreateSubject(ctx context.Context, subjectID, name string) (*Subject, error) {
	payload := map[string]string{
		"subject": subjectID,
	}

	jsonData, err := json.Marshal(payload)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal payload: %w", err)
	}

	body, err := c.request(ctx, http.MethodPost, "/api/v1/recognition/subjects", bytes.NewReader(jsonData), "application/json")
	if err != nil {
		return nil, err
	}

	var result Subject
	if err := json.Unmarshal(body, &result); err != nil {
		return nil, fmt.Errorf("failed to unmarshal response: %w", err)
	}

	return &result, nil
}

// DeleteSubject 删除人脸库
func (c *Client) DeleteSubject(ctx context.Context, subjectID string) error {
	if subjectID == "" || subjectID == "." || subjectID == ".." {
		return fmt.Errorf("invalid subject identifier")
	}
	_, err := c.request(ctx, http.MethodDelete, "/api/v1/recognition/subjects/"+url.PathEscape(subjectID), nil, "")
	return err
}

// ListSubjects 列出所有人脸库
func (c *Client) ListSubjects(ctx context.Context) ([]Subject, error) {
	body, err := c.request(ctx, http.MethodGet, "/api/v1/recognition/subjects", nil, "")
	if err != nil {
		return nil, err
	}

	var result struct {
		Subjects []string `json:"subjects"`
	}
	if err := json.Unmarshal(body, &result); err != nil {
		return nil, fmt.Errorf("failed to unmarshal response: %w", err)
	}

	if result.Subjects == nil {
		return nil, fmt.Errorf("missing subjects array")
	}
	subjects := make([]Subject, 0, len(result.Subjects))
	for _, name := range result.Subjects {
		subjects = append(subjects, Subject{SubjectID: name})
	}
	return subjects, nil
}

// AddFace 添加人脸到人脸库
func (c *Client) AddFace(ctx context.Context, subjectID, imagePath string, metadata map[string]interface{}) (*FaceRecord, error) {
	file, err := os.Open(imagePath)
	if err != nil {
		return nil, fmt.Errorf("failed to open image: %w", err)
	}
	defer file.Close()

	return c.AddFaceFromReader(ctx, subjectID, file, filepath.Base(imagePath), metadata)
}

// AddFaceFromBytes 从字节数组添加人脸
func (c *Client) AddFaceFromBytes(ctx context.Context, subjectID string, imageData []byte, metadata map[string]interface{}) (*FaceRecord, error) {
	return c.AddFaceFromReader(ctx, subjectID, bytes.NewReader(imageData), "image.jpg", metadata)
}

// AddFaceFromReader 从 Reader 添加人脸
func (c *Client) AddFaceFromReader(ctx context.Context, subjectID string, reader io.Reader, filename string, metadata map[string]interface{}) (*FaceRecord, error) {
	if len(metadata) > 0 {
		return nil, fmt.Errorf("CompreFace 1.2 does not persist metadata; store it in your application")
	}
	var buf bytes.Buffer
	writer := multipart.NewWriter(&buf)

	part, err := writer.CreateFormFile("file", filename)
	if err != nil {
		return nil, fmt.Errorf("failed to create form file: %w", err)
	}

	if _, err := io.Copy(part, reader); err != nil {
		return nil, fmt.Errorf("failed to copy image data: %w", err)
	}

	if err := writer.Close(); err != nil {
		return nil, fmt.Errorf("failed to close writer: %w", err)
	}

	params := url.Values{}
	params.Set("subject", subjectID)

	body, err := c.request(ctx, http.MethodPost, "/api/v1/recognition/faces?"+params.Encode(), &buf, writer.FormDataContentType())
	if err != nil {
		return nil, err
	}

	var result FaceRecord
	if err := json.Unmarshal(body, &result); err != nil {
		return nil, fmt.Errorf("failed to unmarshal response: %w", err)
	}

	return &result, nil
}

// DeleteFace 删除人脸
func (c *Client) DeleteFace(ctx context.Context, faceID string) error {
	if faceID == "" || faceID == "." || faceID == ".." {
		return fmt.Errorf("invalid face identifier")
	}
	_, err := c.request(ctx, http.MethodDelete, "/api/v1/recognition/faces/"+url.PathEscape(faceID), nil, "")
	return err
}
