package function

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"time"

	"github.com/minio/minio-go/v7"
	"github.com/minio/minio-go/v7/pkg/credentials"
)

// Request event format
type Event struct {
	InputBucket  string `json:"input-bucket"`
	OutputBucket string `json:"output-bucket"`
	ObjectKey    string `json:"objectKey"`
	Upload       bool   `json:"upload"`
}

// Response payload
type Response struct {
	Result struct {
		Bucket string `json:"bucket"`
		Key    string `json:"key"`
	} `json:"result"`
	Measurement map[string]float64 `json:"measurement"`
}

var minioClient *minio.Client

func init() {
	endpoint := getenv("MINIO_ENDPOINT", "localhost:9000")
	accessKey := getenv("MINIO_ACCESS_KEY", "minioadmin")
	secretKey := getenv("MINIO_SECRET_KEY", "minioadmin")

	var err error
	minioClient, err = minio.New(endpoint, &minio.Options{
		Creds:  credentials.NewStaticV4(accessKey, secretKey, ""),
		Secure: false,
	})
	if err != nil {
		log.Fatalf("Failed to initialize MinIO client: %v", err)
	}
}

// Handle an HTTP request.
func Handle(w http.ResponseWriter, r *http.Request) {
	var event Event
	if err := json.NewDecoder(r.Body).Decode(&event); err != nil {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	if event.InputBucket == "" || event.OutputBucket == "" || event.ObjectKey == "" {
		http.Error(w, "Missing required fields", http.StatusBadRequest)
		return
	}

	ctx := context.Background()
	downloadPath := filepath.Join("/tmp", event.ObjectKey)
	os.MkdirAll(filepath.Dir(downloadPath), 0755)

	// Download
	startDownload := time.Now()
	stat, err := minioClient.StatObject(ctx, event.InputBucket, event.ObjectKey, minio.StatObjectOptions{})
	if err != nil {
		http.Error(w, fmt.Sprintf("Download stat error: %v", err), http.StatusInternalServerError)
		return
	}
	log.Printf("Download size: %d bytes\n", stat.Size)

	err = minioClient.FGetObject(ctx, event.InputBucket, event.ObjectKey, downloadPath, minio.GetObjectOptions{})
	if err != nil {
		http.Error(w, fmt.Sprintf("Download error: %v", err), http.StatusInternalServerError)
		return
	}
	downloadDuration := time.Since(startDownload).Microseconds()

	// Process
	content, err := os.ReadFile(downloadPath)
	if err != nil {
		http.Error(w, fmt.Sprintf("Read error: %v", err), http.StatusInternalServerError)
		return
	}

	startProcess := time.Now()
	processed := transform(string(content)) // Placeholder
	processDuration := time.Since(startProcess).Microseconds()

	var uploadDuration int64
	keyName := "upload-skipped"

	if event.Upload {
		startUpload := time.Now()

		buf := new(bytes.Buffer)
		if err := json.NewEncoder(buf).Encode(processed); err != nil {
			http.Error(w, fmt.Sprintf("Encode error: %v", err), http.StatusInternalServerError)
			return
		}

		uploadSize := int64(buf.Len())
		_, err = minioClient.PutObject(ctx, event.OutputBucket, event.ObjectKey, buf, uploadSize, minio.PutObjectOptions{ContentType: "application/json"})
		if err != nil {
			http.Error(w, fmt.Sprintf("Upload error: %v", err), http.StatusInternalServerError)
			return
		}
		uploadDuration = time.Since(startUpload).Microseconds()
		keyName = event.ObjectKey
	}

	// Construct response
	resp := Response{
		Measurement: map[string]float64{
			"download_time": float64(downloadDuration),
			"compute_time":  float64(processDuration),
		},
	}
	if event.Upload {
		resp.Measurement["upload_time"] = float64(uploadDuration)
	}
	resp.Result.Bucket = event.OutputBucket
	resp.Result.Key = keyName

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(resp)
}

func getenv(key, defaultVal string) string {
	val := os.Getenv(key)
	if val == "" {
		return defaultVal
	}
	return val
}

// transform is a stub representing the squiggle.transform
func transform(input string) any {
	// Replace this with your actual transformation logic
	return map[string]string{"echo": input}
}
