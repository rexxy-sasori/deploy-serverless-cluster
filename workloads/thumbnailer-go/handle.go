package function

import (
	"bytes"
	"context"
	"encoding/json"
	"image"
	"image/jpeg"
	"io"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"time"

	"github.com/disintegration/imaging"
	"github.com/minio/minio-go/v7"
	"github.com/minio/minio-go/v7/pkg/credentials"
)

type Event struct {
	InputBucket  string `json:"input-bucket"`
	OutputBucket string `json:"output-bucket"`
	ObjectKey    string `json:"objectKey"`
	Width        int    `json:"width"`
	Height       int    `json:"height"`
	Upload       bool   `json:"upload"`
}

type Response struct {
	Result struct {
		Bucket string `json:"bucket"`
		Key    string `json:"key"`
	} `json:"result"`
	Measurement map[string]interface{} `json:"measurement"`
}

type MinioClient struct {
	Client *minio.Client
}

func NewMinioClient() *MinioClient {
	endpoint := getenv("MINIO_ENDPOINT", "localhost:9000")
	accessKey := getenv("MINIO_ACCESS_KEY", "minioadmin")
	secretKey := getenv("MINIO_SECRET_KEY", "minioadmin")

	client, err := minio.New(endpoint, &minio.Options{
		Creds:  credentials.NewStaticV4(accessKey, secretKey, ""),
		Secure: false,
	})
	if err != nil {
		log.Fatalf("Failed to create Minio client: %v", err)
	}
	return &MinioClient{Client: client}
}

func Handle(w http.ResponseWriter, r *http.Request) {
	log.Println("OK: Request Received")

	ctx := context.Background()
	minioClient := NewMinioClient()

	body, err := io.ReadAll(r.Body)
	if err != nil {
		http.Error(w, "Error reading body", http.StatusBadRequest)
		return
	}
	defer r.Body.Close()

	var event Event
	if err := json.Unmarshal(body, &event); err != nil {
		http.Error(w, "Invalid JSON", http.StatusBadRequest)
		return
	}

	if event.Width == 0 {
		event.Width = 256
	}
	if event.Height == 0 {
		event.Height = 256
	}

	if event.InputBucket == "" || event.OutputBucket == "" || event.ObjectKey == "" {
		http.Error(w, "Missing required fields", http.StatusBadRequest)
		return
	}

	downloadPath := filepath.Join("/tmp", event.ObjectKey)
	resizedPath := filepath.Join("/tmp", "resized-"+event.ObjectKey)
	_ = os.MkdirAll(filepath.Dir(downloadPath), 0755)

	// 1. Download
	downloadBegin := time.Now()
	err = minioClient.download(ctx, event.InputBucket, event.ObjectKey, downloadPath)
	if err != nil {
		http.Error(w, "Download failed: "+err.Error(), http.StatusInternalServerError)
		return
	}
	downloadEnd := time.Now()

	// 2. Process (resize)
	processBegin := time.Now()
	img, err := imaging.Open(downloadPath)
	if err != nil {
		http.Error(w, "Image open failed: "+err.Error(), http.StatusInternalServerError)
		return
	}
	img = imaging.Thumbnail(img, event.Width, event.Height, imaging.Lanczos)
	err = imaging.Save(img, resizedPath, imaging.JPEGQuality(90))
	if err != nil {
		http.Error(w, "Image save failed: "+err.Error(), http.StatusInternalServerError)
		return
	}
	processEnd := time.Now()

	// 3. Optional Upload
	keyName := "upload-skipped"
	var uploadTime time.Duration
	var uploadSize int64
	if event.Upload {
		uploadBegin := time.Now()
		file, err := os.Open(resizedPath)
		if err != nil {
			http.Error(w, "Failed to open resized file: "+err.Error(), http.StatusInternalServerError)
			return
		}
		defer file.Close()

		info, _ := file.Stat()
		uploadSize = info.Size()

		// Ensure bucket exists
		exists, err := minioClient.Client.BucketExists(ctx, event.OutputBucket)
		if err != nil {
			http.Error(w, "Bucket check failed: "+err.Error(), http.StatusInternalServerError)
			return
		}
		if !exists {
			if err := minioClient.Client.MakeBucket(ctx, event.OutputBucket, minio.MakeBucketOptions{}); err != nil {
				http.Error(w, "Bucket creation failed: "+err.Error(), http.StatusInternalServerError)
				return
			}
		}

		_, err = minioClient.Client.PutObject(ctx, event.OutputBucket, event.ObjectKey, file, uploadSize, minio.PutObjectOptions{})
		if err != nil {
			http.Error(w, "Upload failed: "+err.Error(), http.StatusInternalServerError)
			return
		}
		keyName = event.ObjectKey
		uploadTime = time.Since(uploadBegin)
	}

	// 4. Respond
	resp := Response{
		Measurement: map[string]interface{}{
			"download_time": downloadEnd.Sub(downloadBegin).Microseconds(),
			"compute_time":  processEnd.Sub(processBegin).Microseconds(),
		},
	}
	if event.Upload {
		resp.Measurement["upload_time"] = uploadTime.Microseconds()
		resp.Measurement["upload_size"] = uploadSize
	}
	resp.Result.Bucket = event.OutputBucket
	resp.Result.Key = keyName

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(resp)
}

// ------------------- Helpers ------------------------

func (c *MinioClient) download(ctx context.Context, bucket, key, path string) error {
	obj, err := c.Client.GetObject(ctx, bucket, key, minio.GetObjectOptions{})
	if err != nil {
		return err
	}
	defer obj.Close()

	out, err := os.Create(path)
	if err != nil {
		return err
	}
	defer out.Close()

	_, err = io.Copy(out, obj)
	return err
}

func getenv(key, fallback string) string {
	val := os.Getenv(key)
	if val == "" {
		return fallback
	}
	return val
}
