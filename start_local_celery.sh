celery -A formshare.config.celery_app worker --loglevel=warn --broker=amqp://formshare:formshare@localhost:5672/formshare --result-backend=rpc://formshare:formshare@localhost:5672/formshare
