import os
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "ai-data-scientist")


def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=f"http://{MINIO_ENDPOINT}",
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


def ensure_bucket_exists():
    """
    Check if the bucket exists. If it doesn't, create it.
    """
    s3 = get_s3_client()

    try:
        s3.head_bucket(Bucket=BUCKET_NAME)
        print(f"Bucket '{BUCKET_NAME}' already exists.")
    except ClientError as e:
        error_code = e.response["Error"]["Code"]

        if error_code in ["404", "NoSuchBucket"]:
            print(f"Bucket '{BUCKET_NAME}' does not exist. Creating...")
            s3.create_bucket(Bucket=BUCKET_NAME)
            print(f"Bucket '{BUCKET_NAME}' created successfully.")
        else:
            raise


def upload_file_to_minio(file_content: bytes, filename: str):
    s3 = get_s3_client()

    # Ensure the bucket exists before uploading
    ensure_bucket_exists()

    try:
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=filename,
            Body=file_content,
        )

        return f"s3://{BUCKET_NAME}/{filename}"

    except Exception as e:
        raise Exception(f"Failed to upload to MinIO: {str(e)}")