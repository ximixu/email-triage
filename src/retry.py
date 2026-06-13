import time
from typing import Callable, TypeVar

T = TypeVar("T")


def with_retries(
    fn: Callable[[], T],
    *,
    attempts: int = 3,
    base_delay: float = 1.0,
    retry_on: tuple[type[BaseException], ...] = (Exception,),
) -> T:
    """Call fn(), retrying on the given exception types with exponential backoff.

    Sleeps base_delay * 2**i between attempts (1s, 2s, 4s by default). Exceptions
    not in retry_on propagate immediately; the last exception is re-raised after
    the final attempt is exhausted.
    """
    last_exc: BaseException | None = None
    for i in range(attempts):
        try:
            return fn()
        except retry_on as exc:
            last_exc = exc
            if i < attempts - 1:
                time.sleep(base_delay * (2 ** i))

    assert last_exc is not None  # attempts >= 1, so we always have an exception
    raise last_exc
