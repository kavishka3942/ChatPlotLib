import os
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
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
    # Always save a local copy in uploads directory for offline/local development
    uploads_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "uploads"))
    os.makedirs(uploads_dir, exist_ok=True)
    local_path = os.path.join(uploads_dir, filename)
    with open(local_path, "wb") as f:
        f.write(file_content)

    try:
        s3 = get_s3_client()
        ensure_bucket_exists()
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=filename,
            Body=file_content,
        )
        return f"s3://{BUCKET_NAME}/{filename}"
    except Exception as e:
        print(f"⚠️ MinIO server offline ({e}). File saved locally at: {local_path}")
        return local_path


def get_dataset_schema(file_content: bytes, filename: str) -> str:
    import io
    import pandas as pd

    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(file_content))
        elif filename.endswith((".xls", ".xlsx")):
            df = pd.read_excel(io.BytesIO(file_content))
        else:
            return f"File Name: {filename} (Schema extraction not supported for this file format)"

        schema_lines = [
            f"File Name: {filename}",
            f"Shape: {df.shape[0]} rows, {df.shape[1]} columns",
            "Columns and Data Types:"
        ]
        for col, dtype in df.dtypes.items():
            schema_lines.append(f" - {col}: {dtype}")

        schema_lines.append("\nSample Head Data (First 3 rows):")
        schema_lines.append(df.head(3).to_string())

        return "\n".join(schema_lines)
    except Exception as e:
        return f"File Name: {filename} (Failed to parse schema: {str(e)})"