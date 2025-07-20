package function

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"mime"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	"github.com/minio/minio-go/v7"
	"github.com/minio/minio-go/v7/pkg/credentials"
)

var minioClient *minio.Client

func init() {
	endpoint := os.Getenv("MINIO_ENDPOINT")
	accessKeyID := os.Getenv("MINIO_ACCESS_KEY")
	secretAccessKey := os.Getenv("MINIO_SECRET_KEY")
	useSSL := os.Getenv("MINIO_USE_SSL") == "true"

	client, err := minio.New(endpoint, &minio.Options{
		Creds:  credentials.NewStaticV4(accessKeyID, secretAccessKey, ""),
		Secure: useSSL,
	})
	if err != nil {
		log.Fatalf("Failed to initialize MinIO client: %v", err)
	}

	minioClient = client
}

// Event input format
type Event struct {
	Bucket struct {
		Input  string `json:"input"`
		Output string `json:"output"`
	} `json:"bucket"`
	Object struct {
		Key      string `json:"key"`
		Duration string `json:"duration"`
		Op       string `json:"op"`
	} `json:"object"`
}

// Result output format
type Result struct {
	Result struct {
		Bucket string `json:"bucket"`
		Key    string `json:"key"`
	} `json:"result"`
	Measurement struct {
		DownloadTime  float64 `json:"download_time_us"`
		DownloadSize  int64   `json:"download_size"`
		UploadTime    float64 `json:"upload_time_us"`
		UploadSize    int64   `json:"upload_size"`
		ComputeTime   float64 `json:"compute_time_us"`
	} `json:"measurement"`
}

func Handle(w http.ResponseWriter, r *http.Request) {
	var event Event
	if err := json.NewDecoder(r.Body).Decode(&event); err != nil {
		http.Error(w, "Invalid input", http.StatusBadRequest)
		return
	}

	if strings.Contains(event.Bucket.Input, "..") || strings.Contains(event.Object.Key, "..") {
		http.Error(w, "Invalid path components", http.StatusBadRequest)
		return
	}

	// Use event.Bucket.Input for the input bucket and event.Bucket.Output for the output bucket
	inputBucket := event.Bucket.Input
	inputKey := filepath.Join(event.Bucket.Input, event.Object.Key)
	tmpInput := filepath.Join("/tmp", event.Object.Key)
	tmpOutput := filepath.Join("/tmp", "processed-"+filepath.Base(event.Object.Key))
	outputKey := filepath.Join(event.Bucket.Output, filepath.Base(tmpOutput))

	startDL := time.Now()
	err := downloadFromMinio(inputBucket, inputKey, tmpInput)
	if err != nil {
		http.Error(w, fmt.Sprintf("Download failed: %v", err), http.StatusInternalServerError)
		return
	}
	endDL := time.Now()
	dlSize, _ := fileSize(tmpInput)

	startProc := time.Now()
	err = processFile(event.Object.Op, tmpInput, tmpOutput, event.Object.Duration)
	if err != nil {
		http.Error(w, fmt.Sprintf("Processing failed: %v", err), http.StatusInternalServerError)
		return
	}
	endProc := time.Now()

	startUL := time.Now()
	err = uploadToMinio(event.Bucket.Output, outputKey, tmpOutput)
	if err != nil {
		http.Error(w, fmt.Sprintf("Upload failed: %v", err), http.StatusInternalServerError)
		return
	}
	endUL := time.Now()
	ulSize, _ := fileSize(tmpOutput)

	resp := Result{}
	resp.Result.Bucket = event.Bucket.Output
	resp.Result.Key = outputKey
	resp.Measurement.DownloadTime = float64(endDL.Sub(startDL).Microseconds())
	resp.Measurement.DownloadSize = dlSize
	resp.Measurement.UploadTime = float64(endUL.Sub(startUL).Microseconds())
	resp.Measurement.UploadSize = ulSize
	resp.Measurement.ComputeTime = float64(endProc.Sub(startProc).Microseconds())

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(resp)
}

func downloadFromMinio(bucket, key, dest string) error {
	ctx := context.Background()
	reader, err := minioClient.GetObject(ctx, bucket, key, minio.GetObjectOptions{})
	if err != nil {
		return err
	}
	defer reader.Close()

	outFile, err := os.Create(dest)
	if err != nil {
		return err
	}
	defer outFile.Close()

	_, err = io.Copy(outFile, reader)
	return err
}

func uploadToMinio(bucket, key, path string) error {
	ctx := context.Background()
	contentType := mime.TypeByExtension(filepath.Ext(path))
	file, err := os.Open(path)
	if err != nil {
		return err
	}
	defer file.Close()
	stat, err := file.Stat()
	if err != nil {
		return err
	}
	_, err = minioClient.PutObject(ctx, bucket, key, file, stat.Size(), minio.PutObjectOptions{ContentType: contentType})
	return err
}

func processFile(op, input, output, duration string) error {
	if op != "extract-gif" {
		return fmt.Errorf("unsupported operation: %s", op)
	}
	// Use the correct path for ffmpeg in jrottenberg/ffmpeg:7-scratch image
	cmd := exec.Command("/usr/local/bin/ffmpeg", "-y", "-i", input, "-t", duration, "-vf", "fps=10,scale=320:-1:flags=lanczos", output)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	return cmd.Run()
}

func fileSize(path string) (int64, error) {
	info, err := os.Stat(path)
	if err != nil {
		return 0, err
	}
	return info.Size(), nil
}
