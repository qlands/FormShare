export FORMSHARE_RUN_FROM_CELERY=true
celery -A formshare.config.celery_app worker --loglevel=info -Q FormShare
export FORMSHARE_RUN_FROM_CELERY=false
