from minio import Minio
from minio.error import S3Error

# MinIO Client Class
class MinioClient:
    def __init__(self, endpoint, access_key, secret_key):
        """Initialize the MinIO client."""
        self.client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=False  # Assuming HTTP, change to True for HTTPS
        )

    def download(self, bucket_name, object_name, file_path):
        """Download a file from MinIO."""
        try:
            # Ensure that the bucket exists
            if not self.client.bucket_exists(bucket_name):
                raise ValueError(f"Bucket '{bucket_name}' does not exist.")
            
            # **Get the file size and log it** (New Code)
            object_stat = self.client.stat_object(bucket_name, object_name)
            download_size = object_stat.size  # In bytes
            logging.info(f"Download file '{object_name}' size: {download_size} bytes")  # Log download size
            
            # Download the file
            self.client.fget_object(bucket_name, object_name, file_path)
            logging.info(f"File '{object_name}' downloaded to '{file_path}'")
        except S3Error as e:
            logging.error(f"Error downloading file: {e}")
            raise e

    def upload_file(self, bucket_name: str, object_name: str, file_stream: io.BytesIO, part_size: int = 10 * 1024 * 1024, num_parallel_uploads: int = 3):
        try:
            # Ensure the bucket exists
            if not self.client.bucket_exists(bucket_name):
                self.client.make_bucket(bucket_name)

            # **Log the file size being uploaded** (New Code)
            upload_size = len(file_stream.getvalue())  # In bytes
            logging.info(f"Uploading file '{object_name}' size: {upload_size} bytes")  # Log upload size

            # Multipart upload with parallel uploads for large files
            # The part_size is adjustable. Here it is set to 10 MB per part
            file_stream.seek(0)  # Ensure we're reading from the beginning of the file

            # Perform the multipart upload
            self.client.put_object(
                bucket_name,
                object_name,
                file_stream,
                upload_size,
                part_size=part_size,
                num_parallel_uploads=num_parallel_uploads
            )

            logging.info(f"File '{object_name}' uploaded to bucket '{bucket_name}'")
            return object_name  # Return the key (object name)
        except S3Error as e:
            logging.error(f"Error uploading file: {e}")
            raise e

def get_instance():
    """Create and return an instance of MinioClient using environment variables."""
    MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    
    return MinioClient(MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY)


