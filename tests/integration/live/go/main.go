package main

import (
	"context"
	"crypto/sha256"
	"encoding/base64"
	"fmt"
	facesdk "github.com/facesdk/facesdk-go"
	"net/http"
	"os"
	"time"
)

func require(ok bool, message string) {
	if !ok {
		panic(message)
	}
}
func main() {
	image, err := os.ReadFile(os.Getenv("FACESDK_TEST_IMAGE"))
	if err != nil {
		panic(err)
	}
	client := facesdk.NewClient(os.Getenv("FACESDK_API_URL"), "", facesdk.WithAPIKeys(map[string]string{
		"detection": os.Getenv("FACESDK_DETECTION_API_KEY"), "recognition": os.Getenv("FACESDK_RECOGNITION_API_KEY"), "verification": os.Getenv("FACESDK_VERIFICATION_API_KEY"),
	}), facesdk.WithMaxRetries(0), facesdk.WithHTTPClient(&http.Client{Timeout: 120 * time.Second}))
	ctx := context.Background()
	subject := fmt.Sprintf("facesdk-go-%d", time.Now().UnixNano())
	cleanup := false
	defer func() {
		if cleanup {
			if err := client.DeleteSubject(ctx, subject); err != nil {
				panic(err)
			}
		}
	}()
	detection, err := client.DetectFromBytes(ctx, image, nil)
	if err != nil {
		panic(err)
	}
	require(detection.FaceCount == 1, "single face detection")
	created, err := client.CreateSubject(ctx, subject, "")
	if err != nil {
		panic(err)
	}
	require(created.SubjectID == subject, "create subject")
	cleanup = true
	subjects, err := client.ListSubjects(ctx)
	if err != nil {
		panic(err)
	}
	found := false
	for _, s := range subjects {
		found = found || s.SubjectID == subject
	}
	require(found, "list subjects")
	record, err := client.AddFaceFromBytes(ctx, subject, image, nil)
	if err != nil {
		panic(err)
	}
	require(record.SubjectID == subject && record.ImageID != "", "add face")
	result, err := client.SearchFromBytes(ctx, image, 100, 0.8)
	if err != nil {
		panic(err)
	}
	found = false
	for _, r := range result.Results {
		found = found || (r.SubjectID == subject && r.Match)
	}
	require(result.FaceCount == 1 && found, "recognize subject")
	comparison, err := client.CompareFromBytes(ctx, image, image)
	if err != nil {
		panic(err)
	}
	require(comparison.Match && comparison.Similarity >= 0.8, "self comparison")
	encoded, err := client.ExtractFeatureFromBytes(ctx, image)
	if err != nil {
		panic(err)
	}
	feature, err := base64.StdEncoding.DecodeString(encoded)
	if err != nil {
		panic(err)
	}
	require(len(feature) > 0 && len(feature)%4 == 0, "float32 feature")
	if expected := os.Getenv("FACESDK_FEATURE_SHA256"); expected != "" {
		require(fmt.Sprintf("%x", sha256.Sum256(feature)) == expected, "cross-language embedding")
	}
	if err = client.DeleteFace(ctx, record.ImageID); err != nil {
		panic(err)
	}
	subjects, err = client.ListSubjects(ctx)
	if err != nil {
		panic(err)
	}
	found = false
	for _, s := range subjects {
		found = found || s.SubjectID == subject
	}
	if !found {
		if _, err = client.CreateSubject(ctx, subject, ""); err != nil {
			panic(err)
		}
	}
	if err = client.DeleteSubject(ctx, subject); err != nil {
		panic(err)
	}
	cleanup = false
	subjects, err = client.ListSubjects(ctx)
	if err != nil {
		panic(err)
	}
	for _, s := range subjects {
		require(s.SubjectID != subject, "delete subject")
	}
	fmt.Println("Go real-model lifecycle passed")
}
