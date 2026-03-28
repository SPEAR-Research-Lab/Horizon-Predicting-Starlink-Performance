from datetime import datetime, timezone
import functools
import logging
from logging import Logger
import os
from pathlib import Path
import time
from typing import Any, Callable, Optional


class LogUtils:
    _logger: Optional[Logger] = None
    _parent_dir: Path = (Path(__file__).parent / '..').resolve()

    @staticmethod
    def init_logger(log_dir: str = 'logs') -> Logger:
        if LogUtils._logger:
            return LogUtils._logger

        logs_dir_path = LogUtils._parent_dir / log_dir
        os.makedirs(logs_dir_path, exist_ok=True)
        utc_now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H-%M-%SZ')
        log_path = logs_dir_path / f'{utc_now}.log'

        logging.Formatter.converter = time.gmtime

        LogUtils._logger = logging.getLogger("daily_logger")
        LogUtils._logger.setLevel(logging.INFO)

        handler = logging.FileHandler(log_path)
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        handler.setFormatter(formatter)

        LogUtils._logger.addHandler(handler)
        LogUtils._logger.addHandler(logging.StreamHandler())

        return LogUtils._logger

    @staticmethod
    def log_function(func: Callable[..., Any]) -> Callable[..., Any]:
        logger = LogUtils.init_logger()

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            logger.info(f'Starting: {func.__name__}')
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                logger.info(f'Finished: {func.__name__} (Duration: {duration:.2f}s)')
                return result
            except Exception as e:
                logger.error(f'Exception in {func.__name__}: {e.__class__.__name__} - {e}')
                raise e

        return wrapper
