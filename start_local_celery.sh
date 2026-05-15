export FORMSHARE_RUN_FROM_CELERY=true
celery -A formshare.config.celery_app worker --loglevel=info -Q FormShare,meld_default
export FORMSHARE_RUN_FROM_CELERY=false
