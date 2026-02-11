import os
import sys
import time
import requests
import boto3
from datetime import datetime

# ANSI Colors
GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"


def check_step(name, func):
    print(f"Checking {name}...", end=" ")
    try:
        start = time.time()
        result = func()
        duration = (time.time() - start) * 1000
        print(f"{GREEN}OK{RESET} ({duration:.0f}ms)")
        if result:
            print(f"  -> {result}")
        return True
    except Exception as e:
        print(f"{RED}FAIL{RESET}")
        print(f"  -> Error: {e}")
        return False


def check_s3():
    try:
        s3 = boto3.client(
            "s3", config=boto3.session.Config(signature_version=boto3.UNSIGNED)
        )
    except AttributeError:
        import botocore.config

        s3 = boto3.client(
            "s3", config=botocore.config.Config(signature_version=botocore.UNSIGNED)
        )
    resp = s3.list_objects_v2(Bucket="noaa-gfs-bdp-pds", MaxKeys=1)
    if "Contents" in resp:
        return f"Access confirmed. Found {resp['Contents'][0]['Key']}"
    raise Exception("Bucket accessible but empty?")


def check_attom():
    key = os.getenv("ATTOM_API_KEY")
    if not key:
        raise Exception("ATTOM_API_KEY missing from env")

    url = "https://api.gateway.attomdata.com/propertyapi/v1.0.0/property/detail"
    headers = {"apikey": key, "Accept": "application/json"}
    # Intentionally bad request to check Auth only (400 is better than 401)
    resp = requests.get(url, headers=headers, params={"postalcode": "00000"})

    if resp.status_code == 401:
        raise Exception("401 Unauthorized - Key Invalid")
    if resp.status_code == 403:
        raise Exception("403 Forbidden - Check Plan limits")

    return f"API Responding (Status: {resp.status_code})"


def check_jobnimbus():
    key = os.getenv("JOBNIMBUS_API_KEY")
    if not key:
        raise Exception("JOBNIMBUS_API_KEY missing form env")

    url = "https://api.jobnimbus.com/api/v1/contacts"
    headers = {"Authorization": f"Bearer {key}"}
    # Just check if we can reach the endpoint (Method Not Allowed 405 or 200)
    # We use GET to list (safe)
    resp = requests.get(url, headers=headers)

    if resp.status_code == 401:
        raise Exception("401 Unauthorized - Key Invalid")

    return f"API Responding (Status: {resp.status_code})"


def check_cache():
    import sqlite3

    db_path = "stormops_cache.db"
    if not os.path.exists(db_path):
        return "Cache DB not created yet (Run smoke_test.py first)"

    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT count(*) FROM properties")
    count = c.fetchone()[0]
    conn.close()
    return f"Database Active. Cached Records: {count}"


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    print("--- STORM OPS DIAGNOSTICS ---\n")
    check_step("AWS S3 (Open NWP)", check_s3)
    check_step("ATTOM Property API", check_attom)
    check_step("JobNimbus CRM API", check_jobnimbus)
    check_step("Local SQLite Cache", check_cache)
    print("\n-----------------------------")
