from rq import Connection, Worker

from mindflow_backend.infra.cache.redis_client import get_sync_redis


def run() -> None:
    redis = get_sync_redis()
    with Connection(redis):
        worker = Worker(["default"])
        worker.work(with_scheduler=True)


if __name__ == "__main__":
    run()
