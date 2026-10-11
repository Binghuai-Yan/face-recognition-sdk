package facesdk

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
	"testing"
	"time"
)

func fixtures(t *testing.T) map[string]json.RawMessage {
	t.Helper()
	data, err := os.ReadFile("../../tests/fixtures/compreface-1.2.json")
	if err != nil {
		t.Fatal(err)
	}
	var f map[string]json.RawMessage
	if err := json.Unmarshal(data, &f); err != nil {
		t.Fatal(err)
	}
	return f
}

func TestProtocol(t *testing.T) {
	f := fixtures(t)
	image := []byte("image\x00\xff")
	subject := "张三 /?&"
	calls := 0
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		calls++
		service := strings.Split(r.URL.Path, "/")[3]
		key := map[string]string{"detection": "D", "recognition": "R", "verification": "V"}[service]
		if r.Header.Get("x-api-key") != key {
			t.Errorf("wrong service key: %s", r.Header.Get("x-api-key"))
		}
		response := ""
		if strings.Contains(r.Header.Get("Content-Type"), "multipart/") {
			if err := r.ParseMultipartForm(1 << 20); err != nil {
				t.Error(err)
				return
			}
			defer r.MultipartForm.RemoveAll()
			fields := []string{"file"}
			if service == "verification" {
				fields = []string{"source_image", "target_image"}
			}
			if len(r.MultipartForm.File) != len(fields) {
				t.Error("wrong multipart fields")
			}
			for _, name := range fields {
				part, _, err := r.FormFile(name)
				if err != nil {
					t.Error(err)
					continue
				}
				data, _ := io.ReadAll(part)
				part.Close()
				if !bytes.Equal(data, image) {
					t.Errorf("incomplete image in %s", name)
				}
			}
		}
		switch calls {
		case 1:
			if r.URL.Query().Get("status") != "true" {
				t.Error("options missing")
			}
			response = "detection"
		case 2:
			if r.URL.Path != "/api/v1/verification/verify" {
				t.Error("wrong verification route")
			}
			response = "verification"
		case 3:
			if r.URL.RawQuery != "prediction_count=3" {
				t.Errorf("wrong search query: %s", r.URL.RawQuery)
			}
			response = "recognition"
		case 4:
			if r.URL.Query().Get("face_plugins") != "calculator" {
				t.Error("plugin missing")
			}
			response = "detection"
		case 5:
			response = "subjects"
		case 6:
			var payload map[string]string
			if err := json.NewDecoder(r.Body).Decode(&payload); err != nil || payload["subject"] != subject || len(payload) != 1 {
				t.Error("subject JSON mismatch")
			}
			response = "created"
			w.WriteHeader(201)
		case 7:
			if r.URL.Query().Get("subject") != subject {
				t.Error("subject query lost")
			}
			response = "added"
			w.WriteHeader(201)
		case 8, 9:
			if r.Method != "DELETE" {
				t.Error("expected deletion")
			}
			if calls == 9 && (r.URL.Path != "/api/v1/recognition/subjects/"+subject || r.URL.RawQuery != "") {
				t.Error("identifier not encoded")
			}
			w.WriteHeader(204)
			return
		default:
			t.Error("unexpected request")
			w.WriteHeader(500)
			return
		}
		w.Write(f[response])
	}))
	defer server.Close()
	client := NewClient(server.URL+"/", "", WithAPIKeys(map[string]string{"detection": "D", "recognition": "R", "verification": "V"}), WithRetryDelay(0))
	ctx := context.Background()
	detection, err := client.DetectFromBytes(ctx, image, map[string]string{"status": "true"})
	if err != nil || detection.FaceCount != 1 || detection.Faces[0].Confidence != .99 {
		t.Fatalf("detection: %v %v", detection, err)
	}
	comparison, err := client.CompareFromBytes(ctx, image, image)
	if err != nil || !comparison.Match || comparison.Similarity != .8 {
		t.Fatalf("comparison: %v %v", comparison, err)
	}
	search, err := client.SearchFromBytes(ctx, image, 3, .8)
	if err != nil || search.FaceCount != 1 || len(search.Results) != 2 || search.Results[0].SubjectID != "best" || search.Results[1].SubjectID != "boundary" {
		t.Fatalf("search: %v %v", search, err)
	}
	encoded, err := client.ExtractFeatureFromBytes(ctx, image)
	if err != nil || encoded != "AACAPwAAAMAAAAA/" {
		t.Fatalf("embedding: %s %v", encoded, err)
	}
	subjects, err := client.ListSubjects(ctx)
	if err != nil || len(subjects) != 2 || subjects[1].SubjectID != subject {
		t.Fatalf("subjects: %v %v", subjects, err)
	}
	if _, err := client.CreateSubject(ctx, subject, "ignored"); err != nil {
		t.Fatal(err)
	}
	record, err := client.AddFaceFromBytes(ctx, subject, image, nil)
	if err != nil || record.ImageID == "" {
		t.Fatalf("add: %v", err)
	}
	if err := client.DeleteFace(ctx, record.ImageID); err != nil {
		t.Fatal(err)
	}
	if err := client.DeleteSubject(ctx, subject); err != nil {
		t.Fatal(err)
	}
	if calls != 9 {
		t.Errorf("calls: %d", calls)
	}
}

func TestRetries(t *testing.T) {
	f := fixtures(t)
	var bodies [][]byte
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		data, _ := io.ReadAll(r.Body)
		bodies = append(bodies, data)
		if len(bodies) == 1 {
			w.WriteHeader(503)
			w.Write(f["error"])
		} else {
			w.Write(f["detection"])
		}
	}))
	defer server.Close()
	client := NewClient(server.URL, "key", WithMaxRetries(1), WithRetryDelay(0))
	_, err := client.DetectFromReader(context.Background(), strings.NewReader("complete-image"), "face.jpg", nil)
	if err != nil || len(bodies) != 2 || !bytes.Equal(bodies[0], bodies[1]) || !bytes.Contains(bodies[1], []byte("complete-image")) {
		t.Fatalf("retry lost body: %v", err)
	}
}

func TestNoRetry(t *testing.T) {
	for _, operation := range []string{"auth", "create", "add", "zero", "invalid"} {
		t.Run(operation, func(t *testing.T) {
			calls := 0
			server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				calls++
				switch operation {
				case "auth":
					w.WriteHeader(401)
				case "invalid":
					w.WriteHeader(200)
					w.Write([]byte("{}"))
					return
				default:
					w.WriteHeader(503)
				}
				w.Write([]byte(`{"message":"failure"}`))
			}))
			defer server.Close()
			client := NewClient(server.URL, "key", WithMaxRetries(2), WithRetryDelay(0))
			var err error
			switch operation {
			case "create":
				_, err = client.CreateSubject(context.Background(), "new", "")
			case "add":
				_, err = client.AddFaceFromBytes(context.Background(), "new", []byte("image"), nil)
			default:
				if operation == "zero" {
					client.maxRetries = 0
				}
				_, err = client.DetectFromBytes(context.Background(), []byte("image"), nil)
			}
			if err == nil || calls != 1 {
				t.Fatalf("expected one failing call, calls=%d err=%v", calls, err)
			}
		})
	}
}

func TestCancellationAndValidation(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { w.WriteHeader(503) }))
	defer server.Close()
	client := NewClient(server.URL, "key", WithRetryDelay(time.Second))
	ctx, cancel := context.WithTimeout(context.Background(), 50*time.Millisecond)
	defer cancel()
	_, err := client.DetectFromBytes(ctx, []byte("image"), nil)
	if !errors.Is(err, context.DeadlineExceeded) {
		t.Fatalf("cancellation: %v", err)
	}
	if _, err := client.SearchFromBytes(context.Background(), nil, 0, .8); err == nil {
		t.Error("accepted zero limit")
	}
	if err := client.DeleteSubject(context.Background(), ".."); err == nil {
		t.Error("accepted dot segment")
	}
	if _, err := client.AddFaceFromBytes(context.Background(), "new", nil, map[string]interface{}{"source": "camera"}); err == nil {
		t.Error("accepted metadata")
	}
}

func TestAmbiguousFaces(t *testing.T) {
	for _, operation := range []string{"feature", "compare"} {
		t.Run(operation, func(t *testing.T) {
			f := fixtures(t)
			payload := []byte(`{"result":[]}`)
			if operation == "feature" {
				var d map[string][]json.RawMessage
				json.Unmarshal(f["detection"], &d)
				d["result"] = append(d["result"], d["result"][0])
				payload, _ = json.Marshal(d)
			}
			server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { w.Write(payload) }))
			defer server.Close()
			client := NewClient(server.URL, "key")
			var err error
			if operation == "feature" {
				_, err = client.ExtractFeatureFromBytes(context.Background(), nil)
			} else {
				_, err = client.CompareFromBytes(context.Background(), nil, nil)
			}
			if err == nil {
				t.Error("accepted ambiguous or empty face result")
			}
		})
	}
}
