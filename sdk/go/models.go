// File: facesdk/sdk/go/models.go
// Copyright (c) 2024 FaceSDK Contributors
// MIT License
//
// FaceSDK Go Models

package facesdk

import "time"

// BoundingBox 边界框
type BoundingBox struct {
	XMin int `json:"x_min"`
	YMin int `json:"y_min"`
	XMax int `json:"x_max"`
	YMax int `json:"y_max"`
}

// Quality 质量评分
type Quality struct {
	Score      float64 `json:"score"`
	Brightness float64 `json:"brightness"`
	Sharpness  float64 `json:"sharpness"`
}

// Face 人脸检测结果
type Face struct {
	BoundingBox BoundingBox `json:"box"`
	Landmarks   [][]int     `json:"landmarks"`
	Confidence  float64     `json:"confidence"`
	Quality     *Quality    `json:"quality,omitempty"`
}

// DetectionResult 人脸检测结果
type DetectionResult struct {
	Faces     []Face `json:"faces"`
	ImageID   string `json:"image_id"`
	FaceCount int    `json:"face_count"`
}

// CompareResult 人脸比对结果
type CompareResult struct {
	Similarity float64 `json:"similarity"`
	Distance   float64 `json:"distance"`
	Threshold  float64 `json:"threshold"`
	Match      bool    `json:"is_match"`
	Face1      *Face   `json:"face1,omitempty"`
	Face2      *Face   `json:"face2,omitempty"`
}

// MatchResult 搜索匹配结果
type MatchResult struct {
	SubjectID  string  `json:"subject"`
	Similarity float64 `json:"similarity"`
	Distance   float64 `json:"distance"`
	Match      bool    `json:"is_match"`
	Face       *Face   `json:"face,omitempty"`
}

// SearchResult 人脸识别（1:N 搜索）结果
type SearchResult struct {
	Results   []MatchResult `json:"results"`
	FaceCount int           `json:"face_count"`
	ImageID   string        `json:"image_id"`
}

// FaceRecord 人脸记录
type FaceRecord struct {
	ImageID   string                 `json:"image_id"`
	SubjectID string                 `json:"subject"`
	CreatedAt *time.Time             `json:"created_at,omitempty"`
	UpdatedAt *time.Time             `json:"updated_at,omitempty"`
	Metadata  map[string]interface{} `json:"metadata,omitempty"`
}

// Subject 人脸库
type Subject struct {
	SubjectID string       `json:"subject"`
	Name      string       `json:"name"`
	CreatedAt *time.Time   `json:"created_at,omitempty"`
	UpdatedAt *time.Time   `json:"updated_at,omitempty"`
	Faces     []FaceRecord `json:"faces,omitempty"`
}

// APIError API 错误
type APIError struct {
	Message        string
	HTTPStatusCode int
}

func (e *APIError) Error() string {
	return e.Message
}
