export FORMSHARE_RUN_FROM_CELERY=true
celery -A formshare.config.celery_app worker -D --loglevel=info -Q FormShare -f ./celery.log --pidfile ./celerypid.log
export FORMSHARE_RUN_FROM_CELERY=false
