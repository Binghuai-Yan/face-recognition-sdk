// File: facesdk/sdk/go/models.go
// Copyright (c) 2024 FaceSDK Contributors
// MIT License
//
// FaceSDK Go Models

package facesdk

import (
	"encoding/json"
	"fmt"
	"time"
)

// BoundingBox 边界框
type BoundingBox struct {
	Probability float64 `json:"probability"`
	XMin        int     `json:"x_min"`
	YMin        int     `json:"y_min"`
	XMax        int     `json:"x_max"`
	YMax        int     `json:"y_max"`
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
	Embedding   []float32   `json:"embedding,omitempty"`
}

func normalizeFace(face Face) Face {
	if face.Confidence == 0 {
		face.Confidence = face.BoundingBox.Probability
	}
	return face
}

// DetectionResult 人脸检测结果
type DetectionResult struct {
	Faces     []Face `json:"faces"`
	ImageID   string `json:"image_id"`
	FaceCount int    `json:"face_count"`
}

func (d *DetectionResult) UnmarshalJSON(data []byte) error {
	var raw struct {
		Result  []Face `json:"result"`
		Faces   []Face `json:"faces"`
		ImageID string `json:"image_id"`
	}
	if err := json.Unmarshal(data, &raw); err != nil {
		return err
	}
	d.Faces = raw.Result
	if d.Faces == nil {
		d.Faces = raw.Faces
	}
	if d.Faces == nil {
		return fmt.Errorf("missing detection result array")
	}
	for i, face := range d.Faces {
		d.Faces[i] = normalizeFace(face)
	}
	d.FaceCount = len(d.Faces)
	d.ImageID = raw.ImageID
	return nil
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

func (s *SearchResult) UnmarshalJSON(data []byte) error {
	var raw struct {
		Result    []json.RawMessage `json:"result"`
		Results   []MatchResult     `json:"results"`
		FaceCount int               `json:"face_count"`
		ImageID   string            `json:"image_id"`
	}
	if err := json.Unmarshal(data, &raw); err != nil {
		return err
	}
	s.ImageID = raw.ImageID
	s.Results = make([]MatchResult, 0)
	if raw.Result == nil {
		if raw.Results == nil {
			return fmt.Errorf("missing recognition result array")
		}
		s.Results = raw.Results
		s.FaceCount = raw.FaceCount
		return nil
	}
	s.FaceCount = len(raw.Result)
	for _, data := range raw.Result {
		var face Face
		var candidates struct {
			Subjects []MatchResult `json:"subjects"`
		}
		if err := json.Unmarshal(data, &face); err != nil {
			return err
		}
		if err := json.Unmarshal(data, &candidates); err != nil {
			return err
		}
		face = normalizeFace(face)
		for _, match := range candidates.Subjects {
			match.Face = &face
			s.Results = append(s.Results, match)
		}
	}
	return nil
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
