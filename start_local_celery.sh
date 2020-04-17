celery -A formshare.config.celery_app worker --loglevel=info --broker=redis://localhost:6379/0 --result-backend=redis://localhost:6379/0
