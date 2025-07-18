package function

import (
	"context"
	"fmt"
	"io/ioutil"
	"log"
	"os"

	"github.com/cloudevents/sdk-go/v2/event"
	"github.com/minio/minio-go/v7"
	"github.com/minio/minio-go/v7/pkg/credentials"
	"github.com/cloudevents/sdk-go/v2"
)

// MinioClient struct to wrap the Minio client
type MinioClient struct {
	client *minio.Client
}

// NewMinioClient initializes the MinIO client
func NewMinioClient() (*MinioClient, error) {
	// Read MinIO credentials from environment variables
	endpoint := os.Getenv("MINIO_ENDPOINT")
	if endpoint == "" {
		endpoint = "localhost:9000" // Default to localhost if not specified
	}

	accessKey := os.Getenv("MINIO_ACCESS_KEY")
	if accessKey == "" {
		return nil, fmt.Errorf("MINIO_ACCESS_KEY is not set")
	}

	secretKey := os.Getenv("MINIO_SECRET_KEY")
	if secretKey == "" {
		return nil, fmt.Errorf("MINIO_SECRET_KEY is not set")
	}

	// Initialize MinIO client
	client, err := minio.New(endpoint, &minio.Options{
		Creds:  credentials.NewStaticV4(accessKey, secretKey, ""),
		Secure: false, // Set to true for HTTPS
	})
	if err != nil {
		return nil, err
	}
	return &MinioClient{client: client}, nil
}

// UploadFile uploads file to MinIO
func (m *MinioClient) UploadFile(bucketName, objectName, filePath string) error {
	// Open the file
	file, err := os.Open(filePath)
	if err != nil {
		return fmt.Errorf("failed to open file: %v", err)
	}
	defer file.Close()

	// Ensure the bucket exists or create it
	err = m.client.MakeBucket(context.Background(), bucketName, minio.MakeBucketOptions{})
	if err != nil {
		return fmt.Errorf("failed to create bucket: %v", err)
	}

	// Upload the file
	_, err = m.client.PutObject(context.Background(), bucketName, objectName, file, -1, minio.PutObjectOptions{})
	if err != nil {
		return fmt.Errorf("failed to upload file: %v", err)
	}

	log.Printf("Successfully uploaded %s to bucket %s", objectName, bucketName)
	return nil
}

// HandleCloudEvent processes CloudEvent and uploads to MinIO
func HandleCloudEvent(ctx context.Context, event event.Event) (*event.Event, error) {
	// Parse the CloudEvent
	log.Printf("Received CloudEvent: %v", event)

	// Extract event data (file details)
	var eventData map[string]interface{}
	err := event.DataAs(&eventData)
	if err != nil {
		return nil, fmt.Errorf("failed to parse event data: %v", err)
	}

	inputBucket := eventData["input-bucket"].(string)
	outputBucket := eventData["output-bucket"].(string)
	key := eventData["objectKey"].(string)
	uploadEnabled := eventData["upload"].(bool) // default to false if not specified

	// Initialize the MinIO client
	minioClient, err := NewMinioClient()
	if err != nil {
		return nil, fmt.Errorf("failed to initialize MinIO client: %v", err)
	}

	// Download file from input bucket
	downloadPath := "/tmp/" + key
	err = minioClient.client.FGetObject(ctx, inputBucket, key, downloadPath, minio.GetObjectOptions{})
	if err != nil {
		return nil, fmt.Errorf("failed to download file: %v", err)
	}

	log.Printf("Downloaded file from bucket %s with key %s", inputBucket, key)

	// Process file (dummy transformation for example)
	// Here, we are simply reading the file content and writing it back, but you could apply a transformation
	content, err := ioutil.ReadFile(downloadPath)
	if err != nil {
		return nil, fmt.Errorf("failed to read file: %v", err)
	}

	// Here you can apply any transformation to the content if needed
	transformedContent := string(content) // Example transformation

	// If upload is enabled, upload the transformed file to the output bucket
	if uploadEnabled {
		uploadKey := "transformed-" + key
		err = minioClient.UploadFile(outputBucket, uploadKey, downloadPath)
		if err != nil {
			return nil, fmt.Errorf("failed to upload file: %v", err)
		}

		log.Printf("File uploaded to bucket %s with key %s", outputBucket, uploadKey)
	}

	// Prepare response
	response := event.New()
	response.SetID(event.ID())
	response.SetSource("upload-fn")
	response.SetType("dev.upload")
	response.SetData(cloudevents.ApplicationJSON, map[string]interface{}{
		"bucket": outputBucket,
		"key":    "transformed-" + key,
		"status": "success",
	})

	return &response, nil
}
