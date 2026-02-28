import json
import logging
import sys
import datetime


class JSONFormatter(logging.Formatter):
    EXTRA_KEYS = ("request_id", "method", "path", "status", "duration_ms", "event", "error")

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "ts": datetime.datetime.utcnow().isoformat(timespec="milliseconds") + "Z",
            "level": record.levelname,
            "msg": record.getMessage(),
        }
        for k in self.EXTRA_KEYS:
            v = getattr(record, k, None)
            if v is not None:
                entry[k] = v
        return json.dumps(entry, default=str)


def get_logger(name: str = "supportlens") -> logging.Logger:
    log = logging.getLogger(name)
    if log.handlers:
        return log
    log.setLevel(logging.INFO)
    log.propagate = False
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    log.addHandler(handler)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    return log


logger = get_logger()
