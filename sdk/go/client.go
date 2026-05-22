// File: facesdk/sdk/go/client.go
// Copyright (c) 2024 FaceSDK Contributors
// MIT License
//
// FaceSDK Go Client

package facesdk

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"mime/multipart"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"strconv"
	"time"
)

// Client FaceSDK 客户端
type Client struct {
	apiURL     string
	apiKey     string
	httpClient *http.Client
	maxRetries int
	retryDelay time.Duration
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
		apiURL:     apiURL,
		apiKey:     apiKey,
		httpClient: &http.Client{Timeout: 30 * time.Second},
		maxRetries: 3,
		retryDelay: 500 * time.Millisecond,
	}

	for _, opt := range opts {
		opt(client)
	}

	return client
}

// request 发送 HTTP 请求
func (c *Client) request(ctx context.Context, method, endpoint string, body io.Reader, contentType string) ([]byte, error) {
	url := c.apiURL + endpoint

	var lastErr error
	for attempt := 0; attempt <= c.maxRetries; attempt++ {
		req, err := http.NewRequestWithContext(ctx, method, url, body)
		if err != nil {
			return nil, fmt.Errorf("failed to create request: %w", err)
		}

		req.Header.Set("x-api-key", c.apiKey)
		if contentType != "" {
			req.Header.Set("Content-Type", contentType)
		}

		resp, err := c.httpClient.Do(req)
		if err != nil {
			lastErr = err
			if attempt < c.maxRetries {
				time.Sleep(c.retryDelay * time.Duration(attempt+1))
				continue
			}
			return nil, fmt.Errorf("request failed after %d attempts: %w", c.maxRetries+1, lastErr)
		}
		defer resp.Body.Close()

		respBody, err := io.ReadAll(resp.Body)
		if err != nil {
			return nil, fmt.Errorf("failed to read response body: %w", err)
		}

		if resp.StatusCode != http.StatusOK {
			return nil, c.handleErrorResponse(resp.StatusCode, respBody)
		}

		return respBody, nil
	}

	return nil, fmt.Errorf("request failed after %d attempts: %w", c.maxRetries+1, lastErr)
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

	for key, value := range options {
		writer.WriteField(key, value)
	}

	if err := writer.Close(); err != nil {
		return nil, fmt.Errorf("failed to close writer: %w", err)
	}

	body, err := c.request(ctx, http.MethodPost, "/api/v1/detection/detect", &buf, writer.FormDataContentType())
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

	part1, err := writer.CreateFormFile("file1", filename1)
	if err != nil {
		return nil, fmt.Errorf("failed to create form file1: %w", err)
	}
	if _, err := io.Copy(part1, reader1); err != nil {
		return nil, fmt.Errorf("failed to copy image1 data: %w", err)
	}

	part2, err := writer.CreateFormFile("file2", filename2)
	if err != nil {
		return nil, fmt.Errorf("failed to create form file2: %w", err)
	}
	if _, err := io.Copy(part2, reader2); err != nil {
		return nil, fmt.Errorf("failed to copy image2 data: %w", err)
	}

	if err := writer.Close(); err != nil {
		return nil, fmt.Errorf("failed to close writer: %w", err)
	}

	body, err := c.request(ctx, http.MethodPost, "/api/v1/recognition/compare", &buf, writer.FormDataContentType())
	if err != nil {
		return nil, err
	}

	var result CompareResult
	if err := json.Unmarshal(body, &result); err != nil {
		return nil, fmt.Errorf("failed to unmarshal response: %w", err)
	}

	return &result, nil
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
	var buf bytes.Buffer
	writer := multipart.NewWriter(&buf)

	part, err := writer.CreateFormFile("file", filename)
	if err != nil {
		return nil, fmt.Errorf("failed to create form file: %w", err)
	}

	if _, err := io.Copy(part, reader); err != nil {
		return nil, fmt.Errorf("failed to copy image data: %w", err)
	}

	writer.WriteField("limit", strconv.Itoa(limit))
	if threshold > 0 {
		writer.WriteField("threshold", strconv.FormatFloat(threshold, 'f', -1, 64))
	}

	if err := writer.Close(); err != nil {
		return nil, fmt.Errorf("failed to close writer: %w", err)
	}

	body, err := c.request(ctx, http.MethodPost, "/api/v1/recognition/recognize", &buf, writer.FormDataContentType())
	if err != nil {
		return nil, err
	}

	var result SearchResult
	if err := json.Unmarshal(body, &result); err != nil {
		return nil, fmt.Errorf("failed to unmarshal response: %w", err)
	}

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

	body, err := c.request(ctx, http.MethodPost, "/api/v1/recognition/face", &buf, writer.FormDataContentType())
	if err != nil {
		return "", err
	}

	var result struct {
		Embedding string `json:"embedding"`
	}
	if err := json.Unmarshal(body, &result); err != nil {
		return "", fmt.Errorf("failed to unmarshal response: %w", err)
	}

	return result.Embedding, nil
}

// CreateSubject 创建人脸库
func (c *Client) CreateSubject(ctx context.Context, subjectID, name string) (*Subject, error) {
	payload := map[string]string{
		"subject": subjectID,
		"name":    name,
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
	_, err := c.request(ctx, http.MethodDelete, "/api/v1/recognition/subjects/"+subjectID, nil, "")
	return err
}

// ListSubjects 列出所有人脸库
func (c *Client) ListSubjects(ctx context.Context) ([]Subject, error) {
	body, err := c.request(ctx, http.MethodGet, "/api/v1/recognition/subjects", nil, "")
	if err != nil {
		return nil, err
	}

	var result struct {
		Subjects []Subject `json:"subjects"`
	}
	if err := json.Unmarshal(body, &result); err != nil {
		return nil, fmt.Errorf("failed to unmarshal response: %w", err)
	}

	return result.Subjects, nil
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
	var buf bytes.Buffer
	writer := multipart.NewWriter(&buf)

	part, err := writer.CreateFormFile("file", filename)
	if err != nil {
		return nil, fmt.Errorf("failed to create form file: %w", err)
	}

	if _, err := io.Copy(part, reader); err != nil {
		return nil, fmt.Errorf("failed to copy image data: %w", err)
	}

	if metadata != nil {
		metadataJSON, _ := json.Marshal(metadata)
		writer.WriteField("metadata", string(metadataJSON))
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
	_, err := c.request(ctx, http.MethodDelete, "/api/v1/recognition/faces/"+faceID, nil, "")
	return err
}
