import json
import logging
import os
import sys
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, Optional

LOG_DIR = Path(os.getenv("LOG_DIR", "/app/logs"))
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FORMAT = "%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    if not logger.handlers:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
        logger.addHandler(console_handler)

        log_file = LOG_DIR / f"{name}.log"
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
        logger.addHandler(file_handler)

    return logger


class PipelineLogger:
    def __init__(self, pipeline_name: str):
        self.pipeline_name = pipeline_name
        self.logger = setup_logger(pipeline_name)
        self.audit_file = LOG_DIR / "audit.jsonl"
        self.run_id = f"{pipeline_name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        self._start_time = None

    def start(self, metadata: Optional[Dict] = None):
        self._start_time = datetime.utcnow()
        self.logger.info(f"Pipeline started: {self.pipeline_name} [run_id={self.run_id}]")
        self._write_audit(event="START", metadata=metadata or {})

    def finish(self, records_in: int = 0, records_out: int = 0, metadata: Optional[Dict] = None):
        elapsed = (datetime.utcnow() - self._start_time).total_seconds() if self._start_time else 0
        self.logger.info(
            f"Pipeline finished: {self.pipeline_name} | records_in={records_in} | "
            f"records_out={records_out} | elapsed={elapsed:.1f}s"
        )
        self._write_audit(
            event="FINISH",
            metadata={
                **(metadata or {}),
                "records_in": records_in,
                "records_out": records_out,
                "elapsed_seconds": round(elapsed, 2),
            },
        )

    def error(self, message: str, exc: Optional[Exception] = None):
        self.logger.error(f"Pipeline error: {message}", exc_info=exc is not None)
        self._write_audit(event="ERROR", metadata={"error": message})

    def info(self, message: str):
        self.logger.info(message)

    def _write_audit(self, event: str, metadata: Dict):
        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "run_id": self.run_id,
            "pipeline": self.pipeline_name,
            "event": event,
            **metadata,
        }
        with open(self.audit_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def log_pipeline(pipeline_name: str):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            pl = PipelineLogger(pipeline_name)
            pl.start()
            try:
                result = func(*args, **kwargs)
                pl.finish()
                return result
            except Exception as e:
                pl.error(str(e), exc=e)
                raise
        return wrapper
    return decorator
