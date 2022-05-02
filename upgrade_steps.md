# Upgrade steps for FormShare (built from source)

**Tested in Ubuntu Server 21.10**

This guide assumes that you installed FormShare from source following [the installation guide](install_steps.md)

## Stop FormShare (if its running)

```bash
pkill -F /opt/formshare_gunicorn/formshare.pid
```

## Disable all plug ins in development.ini (if applicable)

```ini
#formshare.plugins = plugin1 plugin2 plugin3
```

## Upgrade the FormShare source code

```sh
cd /opt/formshare
sudo git branch [new_stable_branch_name]
sudo git checkout [new_stable_branch_name]
sudo git pull origin [new_stable_branch_name]

cd /opt
sudo rm -R -f formshare_env
sudo python3 -m venv formshare_env

whoami=$(whoami)
sudo chown -R $whoami formshare
sudo chown -R $whoami formshare_env

source ./formshare_env/bin/activate
pip install wheel
pip install -r /opt/formshare/requirements.txt
cd /opt/formshare
python setup.py develop
python setup.py compile_catalog

alembic upgrade head
```

## Rebuild and enable plug ins (if applicable)

### For each plug in, run develop

```sh
python setup.py develop
```

### For each plug in, compile the language catalog (if applicable)
```sh
python setup.py compile_catalog
```

### Enable all plug ins in development.ini

```ini
formshare.plugins = plugin1 plugin2 plugin3
```

## Run FormShare again

```sh
cd /opt/formshare
pserve ./development.ini
# The process ID of FormShare will be in /opt/formshare_gunicorn/formshare.pid
```