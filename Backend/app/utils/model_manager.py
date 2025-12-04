# app/utils/model_manager.py
# Lazy GPU loader with idle-unload + concurrency control for DGL-KE ScoreInfer.
# Works with a single process that "owns" the GPU (recommended: gunicorn -w 1).
#
# Usage in routes:
#   with MODEL.session() as infer:
#       raw = infer.topK(...)
#
# Build the singleton:
#   MODEL = LazyKGEManager(
#       score_infer_cls=ScoreInfer,
#       device=DEVICE,
#       config=config,
#       model_path=MODEL_PATH,
#       sfunc=SFUNC,
#       idle_seconds=900,     # 15 minutes
#       max_inflight=1        # number of simultaneous inferences allowed
#   )

import os
import time
import gc
import logging
import threading
from contextlib import contextmanager
from typing import Optional, Any

logger = logging.getLogger("main_server_kge")

class LazyKGEManager:
    """
    Lazily loads DGL-KE ScoreInfer onto GPU on demand, and auto-unloads
    after an idle timeout. Guards GPU with a semaphore so that only a
    bounded number of requests run concurrently. Prevents unload while
    any request is in-flight.

    Parameters
    ----------
    score_infer_cls : type
        The ScoreInfer class (from dglke.models.infer import ScoreInfer).
    device : int
        CUDA device id (e.g., 0) or -1 for CPU.
    config : dict
        Model config (result of load_model_config).
    model_path : str / os.PathLike
        Folder containing the saved embeddings and config.json.
    sfunc : str
        'none' or 'logsigmoid'. Passed to ScoreInfer.
    idle_seconds : int
        Unload after this many seconds of inactivity. Set 0 to disable.
    max_inflight : int
        Max number of concurrent inferences. Extra requests will block
        on a semaphore until a slot is available.

    Notes
    -----
    - Designed for a *single* process per GPU. If you run multiple workers,
      each process will have its own copy of the model in GPU memory.
    """

    def __init__(
        self,
        *,
        score_infer_cls: type,
        device: int,
        config: dict,
        model_path: Any,
        sfunc: str = "none",
        idle_seconds: int = 900,
        max_inflight: int = 1,
        name: str = "kge"
    ):
        self._ScoreInfer = score_infer_cls
        self.device = device
        self.config = config
        self.model_path = str(model_path)
        self.sfunc = sfunc
        self.idle_seconds = max(0, int(idle_seconds))
        self._name = name

        self._infer: Optional[Any] = None
        self._last_used: float = 0.0
        self._active: int = 0                 # number of in-flight sessions
        self._lock = threading.RLock()        # protects _infer/_active/_last_used
        self._sem = threading.Semaphore(max(1, int(max_inflight)))
        self._reaper_started = False

    # ------------- Public API -------------

    def is_loaded(self) -> bool:
        with self._lock:
            return self._infer is not None

    def active_count(self) -> int:
        with self._lock:
            return self._active

    def last_used_ts(self) -> float:
        with self._lock:
            return self._last_used

    def stats(self) -> dict:
        with self._lock:
            return {
                "loaded": self._infer is not None,
                "active": self._active,
                "last_used": self._last_used,
                "idle_seconds": self.idle_seconds,
            }

    def ensure_loaded(self):
        """
        Returns a ready ScoreInfer handle, loading it if needed.
        Safe to call often. Updates last-used timestamp.
        """
        # Fast path
        if self._infer is not None:
            with self._lock:
                self._last_used = time.time()
                return self._infer

        # Slow path: double-checked with locking
        with self._lock:
            if self._infer is None:
                t0 = time.time()
                logger.info("[%s] Loading DGL-KE model onto device %s …", self._name, self.device)
                inf = self._ScoreInfer(
                    device=self.device,
                    config=self.config,
                    model_path=self.model_path,
                    sfunc=self.sfunc
                )
                inf.load_model()
                self._infer = inf
                dt = time.time() - t0
                logger.info("[%s] DGL-KE model loaded (%.2fs).", self._name, dt)
                if not self._reaper_started and self.idle_seconds > 0:
                    self._start_reaper()
            self._last_used = time.time()
            return self._infer

    def unload_now(self, *, force: bool = False) -> bool:
        """
        Attempt to unload immediately.
        Returns True if unloaded, False if skipped because active>0 and force=False.
        """
        with self._lock:
            if self._infer is None:
                return True
            if self._active > 0 and not force:
                logger.info("[%s] unload_now skipped; %d request(s) in flight.", self._name, self._active)
                return False
            self._unload_locked()
            return True

    @contextmanager
    def session(self):
        """
        Context manager that:
        - acquires an inference slot (bounded concurrency),
        - ensures the model is loaded,
        - increments/decrements the active counter,
        - protects against unloading mid-request.

        Usage:
            with MODEL.session() as infer:
                infer.topK(...)
        """
        self._sem.acquire()
        try:
            with self._lock:
                self._active += 1
            infer = self.ensure_loaded()   # updates last_used
            try:
                yield infer
            finally:
                with self._lock:
                    self._active -= 1
                    self._last_used = time.time()
        finally:
            self._sem.release()

    # ------------- Internals -------------

    def _start_reaper(self):
        self._reaper_started = True
        t = threading.Thread(target=self._reaper_loop, name=f"{self._name}-reaper", daemon=True)
        t.start()

    def _reaper_loop(self):
        # Check a few times per window but keep it calm.
        check_every = max(5, min(60, self.idle_seconds // 3 or 10))
        while True:
            time.sleep(check_every)
            with self._lock:
                if self._infer is None:
                    continue
                idle_for = time.time() - self._last_used
                if self._active == 0 and idle_for >= self.idle_seconds:
                    logger.info("[%s] Idle %.1fs ≥ %ss; unloading GPU model.", self._name, idle_for, self.idle_seconds)
                    self._unload_locked()

    def _unload_locked(self):
        # Assumes _lock is held.
        inf = self._infer
        self._infer = None
        try:
            # Heavy tensors live on inf.model
            if hasattr(inf, "model"):
                del inf.model
        except Exception:
            pass
        try:
            del inf
        except Exception:
            pass

        # GC + CUDA cache cleanup
        gc.collect()
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.ipc_collect()
        except Exception:
            # CUDA may not be available in some test environments
            pass
        logger.info("[%s] Model successfully unloaded; GPU memory should be freed.", self._name)
