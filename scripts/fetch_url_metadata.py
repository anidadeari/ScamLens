"""Fetch only URL audit columns from revision-pinned PhreshPhish Parquet shards.

This preparation utility uses HTTP byte ranges. It never requests or reads the HTML
column and aborts if a server ignores a range request.
"""
from __future__ import annotations

import argparse
import io
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
import requests


REVISION = "eabec4b7a66324b79cc8a0ad856d1731dc26fe1a"
BASE = f"https://huggingface.co/datasets/phreshphish/phreshphish/resolve/{REVISION}/data"
COLUMNS = ["sha256", "url", "label", "date"]
SHARDS = {"train": 56, "test": 21}


class RangeReader(io.RawIOBase):
    def __init__(self, session: requests.Session, url: str) -> None:
        self.session, self.url, self.position, self.transferred = session, url, 0, 0
        response = session.head(url, allow_redirects=True, timeout=60)
        response.raise_for_status()
        self.size = int(response.headers["Content-Length"])

    def readable(self) -> bool: return True
    def seekable(self) -> bool: return True
    def tell(self) -> int: return self.position
    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        if whence == io.SEEK_SET: position = offset
        elif whence == io.SEEK_CUR: position = self.position + offset
        elif whence == io.SEEK_END: position = self.size + offset
        else: raise ValueError("invalid whence")
        if position < 0: raise ValueError("negative seek")
        self.position = min(position, self.size)
        return self.position
    def read(self, size: int = -1) -> bytes:
        if self.position >= self.size: return b""
        end = self.size - 1 if size < 0 else min(self.size - 1, self.position + size - 1)
        response = self.session.get(
            self.url, headers={"Range": f"bytes={self.position}-{end}"},
            allow_redirects=True, timeout=120,
        )
        if response.status_code != 206:
            raise RuntimeError("Server ignored byte-range request; refusing full-shard download")
        data = response.content
        expected = end - self.position + 1
        if len(data) != expected:
            raise RuntimeError("Incomplete byte-range response")
        self.position += len(data)
        self.transferred += len(data)
        return data


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--probe-only", action="store_true")
    args = parser.parse_args()
    frames, total_bytes = [], 0
    with requests.Session() as session:
        for split, count in SHARDS.items():
            for number in range(count):
                reader = RangeReader(session, f"{BASE}/{split}-{number:03d}.parquet")
                parquet = pq.ParquetFile(reader)
                missing = set(COLUMNS) - set(parquet.schema_arrow.names)
                if missing: raise RuntimeError(f"Missing required columns: {sorted(missing)}")
                if args.probe_only:
                    print(parquet.schema_arrow)
                    print(f"rows={parquet.metadata.num_rows} transferred={reader.transferred}")
                    return
                frame = parquet.read(columns=COLUMNS).to_pandas()
                frame.insert(0, "official_split", split)
                frame.insert(1, "source_shard", f"{split}-{number:03d}.parquet")
                frames.append(frame)
                total_bytes += reader.transferred
                print(f"{split}-{number:03d}: {len(frame)} rows; transferred={reader.transferred}")
    result = pd.concat(frames, ignore_index=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_parquet(args.output, index=False)
    print(f"rows={len(result)} transferred={total_bytes} stored={args.output.stat().st_size}")


if __name__ == "__main__":
    main()
