export FORMSHARE_RUN_FROM_CELERY=true
celery -A formshare.config.celery_app worker -D --loglevel=info -Q FormShare,meld_default -f /home/cquiros/data/projects2017/personal/software/FormShare/celery.log --pidfile /home/cquiros/data/projects2017/personal/software/FormShare/celerypid.log
export FORMSHARE_RUN_FROM_CELERY=false
