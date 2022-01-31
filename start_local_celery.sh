celery -A formshare.config.celery_app worker --without-gossip --loglevel=info -Q FormShare
