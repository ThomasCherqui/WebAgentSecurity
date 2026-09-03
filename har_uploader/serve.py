#!/usr/bin/env python3
import uvicorn


if __name__ == "__main__":
    print("HAR Privacy Uploader: http://127.0.0.1:8787")
    uvicorn.run("app:app", host="127.0.0.1", port=8787, app_dir=__file__.rsplit("/", 1)[0])
