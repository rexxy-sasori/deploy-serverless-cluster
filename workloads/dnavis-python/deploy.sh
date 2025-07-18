func deploy --push=false -v \                                    
  -e MINIO_ENDPOINT=minio.minio.svc.cluster.local:9000 \
  -e MINIO_ACCESS_KEY=minioadmin \
  -e MINIO_SECRET_KEY=minioadmin \  
  -e MINIO_SECURE=false  