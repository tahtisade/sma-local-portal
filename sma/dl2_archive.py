#!/usr/bin/env python3

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import requests


DL2_URL = "http://192.168.2.113"
DL2_USERNAME = "admin"

ARCHIVE_DIR = Path(__file__).resolve().parent.parent / "data" / "resol"


def download_day(date_str: str) -> Path:

    try:
        day = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise RuntimeError("Date must be in YYYY-MM-DD format")

    dl2_date = day.strftime("%m/%d/%Y")

    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    final_path = ARCHIVE_DIR / f"{date_str}.csv"

    if final_path.exists() and final_path.stat().st_size > 0:
        return final_path

    temp_path = ARCHIVE_DIR / f".{date_str}.csv.tmp"

    password = os.environ.get("DL2_PASSWORD")
    if not password:
        raise RuntimeError("DL2_PASSWORD environment variable is not set")


    with requests.Session() as session:
        # Login
        response = session.post(
            f"{DL2_URL}/dlx/session/login",
            data={
                "username": DL2_USERNAME,
                "password": password,
            },
            timeout=15,
        )
        response.raise_for_status()

        if "/dlx/session/logout" not in response.text:
            raise RuntimeError("DL2 login failed")

        # Download historical data
        response = session.get(
            f"{DL2_URL}/dlx/download/download",
            params={
                "outputType": "text-csv-lf",
                "sieveInterval": "1",
                "startDate": dl2_date,
                "endDate": dl2_date,
                "dataLanguage": "en",
                "useWasm": "",
            },
            timeout=120,
        )
        response.raise_for_status()

        content = response.content

        if not content:
            raise RuntimeError("DL2 returned an empty response")

        # A failed session or other error may return an HTML page.
        first_bytes = content[:500].lower()
        if b"<html" in first_bytes or b"<!doctype" in first_bytes:
            raise RuntimeError("DL2 returned HTML instead of CSV")

        # Basic validation of the RESOL CSV.
        text_start = content[:10000].decode("ascii", errors="replace")
        if "Date / Time;" not in text_start:
            raise RuntimeError("Downloaded file does not look like a RESOL CSV")

        temp_path.write_bytes(content)
        temp_path.replace(final_path)

    return final_path


def main():
    if len(sys.argv) > 2:
        print(f"Usage: {sys.argv[0]} [YYYY-MM-DD]")
        sys.exit(2)

    if len(sys.argv) == 2:
        date_str = sys.argv[1]
    else:
        date_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    archive_path = ARCHIVE_DIR / f"{date_str}.csv"
    existed_before = archive_path.exists() and archive_path.stat().st_size > 0

    try:
        path = download_day(date_str)

        if existed_before:
            print(f"Archive OK: {path}")
        else:
            print(f"Downloaded: {path}")

        print(f"Size: {path.stat().st_size} bytes")

    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
