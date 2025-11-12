```bash

docker run -d --name redis-stack -p 6379:6379 -p 8001:8001 redis/redis-stack:latest

$ celery -A celery_worker.celery_app worker --pool=solo --loglevel=info

uvicorn main:app --reload

```