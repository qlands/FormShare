export FORMSHARE_RUN_FROM_CELERY=true
celery -A formshare.config.celery_app worker --loglevel=info -Q FormShare -f ./celery.log
export FORMSHARE_RUN_FROM_CELERY=false
