rm -f ./formshare.log
FORMSHARE_INI=./development.ini uvicorn formshare.app:create_app --factory --host 192.168.0.13 --port 5900 --workers 4 >> ./formshare.log 2>&1 &
echo $! > ./formshare.pid
formshare-submission-worker --worker-id 0 --num-workers 2 > ./worker-0.log 2>&1 &
formshare-submission-worker --worker-id 1 --num-workers 2 > ./worker-1.log 2>&1 &
