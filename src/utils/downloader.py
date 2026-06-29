"""
更新程序下载线程 — 支持进度回调和中止
"""
import os
import threading
from urllib.request import urlopen, Request


class DownloadWorker:
    """后台下载线程，支持进度回调和中止"""

    def __init__(self, url, dest_path, on_progress=None, on_done=None):
        self.url = url
        self.dest_path = dest_path
        self.on_progress = on_progress
        self.on_done = on_done
        self._cancel = False
        self._thread = None

    def start(self, timeout=120):
        self._thread = threading.Thread(target=self._run, args=(timeout,), daemon=True)
        self._thread.start()

    def cancel(self):
        self._cancel = True

    def _run(self, timeout):
        try:
            req = Request(self.url, headers={"User-Agent": "RandomCallTool-Update"})
            with urlopen(req, timeout=timeout) as resp:
                total = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                chunk_size = 8192
                os.makedirs(os.path.dirname(self.dest_path), exist_ok=True)
                with open(self.dest_path, "wb") as f:
                    while not self._cancel:
                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total > 0 and self.on_progress:
                            pct = downloaded * 100 // total
                            self.on_progress(downloaded, total, pct)
                        elif self.on_progress:
                            self.on_progress(downloaded, total, 0)
            if self._cancel:
                if self.on_done:
                    self.on_done(False, 0, "\u5df2\u53d6\u6d88")
            else:
                if self.on_done:
                    self.on_done(True, os.path.getsize(self.dest_path), None)
        except Exception as e:
            if self.on_done:
                self.on_done(False, 0, str(e))
