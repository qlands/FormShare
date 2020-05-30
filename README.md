FormShare 2
=========
The future of FormHub

Centralize data – Decentralize knowledge<sup>TM</sup>

About
-----
FormShare 2 is inspired by the excellent [FormHub](<http://github.com/SEL-Columbia/formhub>) platform developed by the Sustainable Engineering Lab at Columbia University. After I forked [OnaData](https://github.com/onaio/onadata) (a fork of FormHub) back in 2016 it was clear that the code needed a lot to bring it to the main ideas that I had: 1) Integrate it with [ODK Tools](https://github.com/qlands/odktools), 2) provide a proper MySQL repository to centralize the data and, 3) use latest software technologies to decentralize the management.

FormShare was created because:

* I want to provide an open-source and **free** platform to private and public organizations to help them manage their data when using ODK.
* ODK Aggregate, in my personal opinion, is badly designed, buggy, and not interoperable. ODK Central is just not there yet.
* Forks based on FormHub suffer from the same ills of their father: Django (sorry if I hurt your feelings), no proper repository, rudimentary data cleaning, no auditing, little interoperability, poor or none extensibility... among many others.

FormShare 2 has been written from scratch (not a single line of code comes from Formhub, just ideas, and principles) using Python 3, [Pyramid](https://trypyramid.com/), MySQL, [ElasticSearch](https://www.elastic.co/elasticsearch/), and [PyUtilib](https://github.com/PyUtilib/pyutilib) to deliver a complete and extensible data management solution for ODK Data collection. It took us three years but is finally here :-) and it is Django free!

FormShare **is for organizations** to install it in their server or cloud service to serve ODK XForms and collect and manage the submissions. FormShare is also available as a service at [https://formshare.org](https://formshare.org) for those organizations that lacks the capacity or resources to run their installation.

ScreenShot
----------

![Image](./Screenshot.png "FormShare home screen")

Releases
------------
The current stable release is 2.6.2 and it is available [here](https://github.com/qlands/FormShare/tree/stable-2.6.2) 

The database signature for stable 2.6.2 is be94ab1faa43

The Docker image for stable 2.6.2 is 20200515

Installation
------------
Please read the [installation guide](install_steps.txt) if you want to install FormShare manually. However, we encourage you to use the Docker Compose file available in the docker_compose directory. This will help you later on in backing FormShare or move it to another server.

The below is a common recipe for running FormShare using docker:

```shell
# From a fresh installation of Ubuntu 18.04.03 from https://ubuntu.com/download/server
# Update the repositories and packages
sudo add-apt-repository multiverse
sudo apt-get update
sudo apt-get -y upgrade

# Install docker-compose
sudo apt-get install -y docker-compose

# Collect the FormShare source code
cd /opt
sudo git clone https://github.com/qlands/FormShare.git -b stable-2.6.2 formshare_source

# Copy the docker compose file from the source to a new directory
sudo mkdir formshare_docker_compose_20200515
sudo cp ./formshare_source/docker_compose/docker-compose.yml ./formshare_docker_compose_20200515/

# Make the directory structure for FormShare
sudo mkdir /opt/formshare
whoami=$(whoami)
sudo chown $whoami /opt/formshare
mkdir /opt/formshare/celery
mkdir /opt/formshare/log
mkdir /opt/formshare/repository
mkdir /opt/formshare/config
mkdir /opt/formshare/mysql
mkdir /opt/formshare/plugins
mkdir /opt/formshare/elasticsearch
mkdir /opt/formshare/elasticsearch/esdata
mkdir /opt/formshare/elasticsearch/esdata2
mkdir /opt/formshare/elasticsearch/esdata3

# Set enough memory for ElasticSearch
sudo sysctl -w vm.max_map_count=262144
echo 'vm.max_map_count=262144' | sudo tee -a /etc/sysctl.d/60-vm-max_map_count.conf

# Download all the required Docker Images
cd /opt/formshare_docker_compose_20200515
sudo docker-compose pull

# Edit the docker-compose.yml file to set the mysql root and FormShare admin passwords
sudo nano /opt/formshare_docker_compose_20200515/docker-compose.yml
# Press Alt+Shit+3 to show the line numbers in Nano

Edit line 7: Change the root password from "my_secure_password" to your password
Edit line 74: Change the root password from "my_secure_password" to the same password of line 7
Edit line 75: Change the admin user name (optional)
Edit line 76: Change the admin email address
Edit line 77: Change the admin user password from "my_secure_password" to your password

# Save the file with Ctlr+o Enter . Exit with Ctrl+x

# Install Apache Server
sudo apt-get install -y apache2

# Enable proxy for Apache
sudo ln -s /etc/apache2/mods-available/proxy.conf /etc/apache2/mods-enabled/
sudo ln -s /etc/apache2/mods-available/proxy.load /etc/apache2/mods-enabled/
sudo ln -s /etc/apache2/mods-available/proxy_http.load /etc/apache2/mods-enabled/

# Edit the apache configuration to proxy pass FormShare 
sudo nano /etc/apache2/sites-enabled/000-default.conf
# Add the following lines after line 28
        ProxyRequests Off
        ProxyPreserveHost On
   
        ProxyPass           /formshare    http://127.0.0.1:5900/formshare
        ProxyPassReverse    /formshare    http://127.0.0.1:5900/formshare
  
        <Proxy *>
           allow from all
        </Proxy>
        ProxyTimeout 120
           
# Save the file with Ctlr+o Enter . Exit with Ctrl+x
# Stop the Apache server
sudo service apache2 stop
# Start the Apache server
sudo service apache2 start

# Start the FormShare containers. The fist time you start the container FormShare will construct the database and apply all updates. This will take about 5 minutes.
# Subsequent start will take about 2 minutes. You can check the status with "sudo docker stats". 
# FormShare will be ready for usage when the container reaches more than 500 kB of MEM USAGE
# This is the only two commands you need to start FormShare after a server restart
cd /opt/formshare_docker_compose_20200515
sudo docker-compose up -d

# Browse to FormShare
http://[this server IP address]/formshare
```

## Install plug-ins while using Docker (images > 20200306)

All plug-ins must be deployed in the directory /opt/formshare/plugins which is a volume in all the provided docker compose files.

```sh
# Grab the container ID running FormShare
sudo docker stats
# Get into the container
sudo docker exec -it [formshare_container_id] /bin/bash
# Activate the environment
source /opt/formshare_env/bin/activate
# Go to the plugins directory
cd /opt/formshare_plugins
# For each plugin run develop
python setup.py develop
# For each plugin compile the language catalogs
python setup.py compile_catalog
#Exit the container
exit
# Stop the FormShare docker container
sudo docker stop [formshare_container_id]
# Edit the file /opt/formshare/config/development.ini and enable the plug-ins
sudo nano /opt/formshare/config/development.ini
# Start the FormShare docker container
sudo docker start formshare_container_id
```

**Important Note:** You may need to repeat these steps if the FormShare container gets updated or if you update FormShare. Use the information in "Upgrading information" if this is the case.

## Upgrading information

Please read the [upgrade guide](upgrade_steps.txt) if you have FormShare installed from the source code. If you use Docker then things are easier:

```sh
# Make a backup of your installation. See the section "Backup FormShare"

# Create the plug-ins directory if it does not exist
mkdir /opt/formshare/plugins

# Edit the file /opt/formshare/config/development.ini and disable all plug-ins
sudo nano /opt/formshare/config/development.ini

# Download the new version of formShare. Replace X for the version you want to use
cd /opt
sudo git clone https://github.com/qlands/FormShare.git -b stable-2.X formshare_2.X_source

# Copy the docker compose file from the source to a new directory. Replace XXXXXXXX to the Docker image that you want to use
sudo mkdir formshare_docker_compose_XXXXXXXX
sudo cp ./formshare_2.X_source/docker_compose/docker-compose.yml /opt/formshare_docker_compose_XXXXXXXX/

#Edit the new docker-compose.yml so it has the same parameters as the previous one (MySQL server, ElasticSearch server, MySQL user and password, FormShare admin, etc)
sudo nano /opt/formshare_docker_compose_XXXXXXXX/docker-compose.yml

# Remove the old Docker Network. Replace XXXXXXX for the previous Docker image
sudo docker network rm formsharedockercomposeXXXXXXXX_fsnet

# Start the new version of FormShare. All required updates in the database will be done automatically.
cd /opt/formshare_docker_compose_XXXXXXXX
sudo docker-compose up -d

# If you have plug-ins then you need to build them and enable them again. See the section "Install plug-ins while using Docker"

```



## How to make your FormShare installation inaccessible, inconsistent, and/or broken.

FormShare uses MySQL, ElasticSearch, and a file repository. **All of them are synchronized**, thus the following list of things may make your FormShare installation inaccessible, inconsistent and/or broken:

- Altering the database manually, for example, removing/adding users or forms
- Removing files manually from the repository 
- Changing the encryption key (aes.key) in the development.ini file.
- Deleting or changing the ElasticSearch index data
- Deleting the repository

## Backup FormShare

FormShare uses MySQL, ElasticSearch, and a file repository. **All of them are synchronized**. To backup FormShare do:

- Stop the FormShare service
- Use mysqldump to backup the schema called "formshare" 
- Use mysqldump to backup all schemata starting with "FS" (optional: Only if you are migrating FormShare to a new server)
- If you used any of the provided Docker compose files then backup the directory /opt/formshare
- If you did not use Docker then:
  - Backup the development.ini file
  - Backup the ElasticSearch data directory or create a [snapshot](https://www.elastic.co/guide/en/elasticsearch/reference/6.1/modules-snapshots.html#_snapshot)  of the following indexes:
    - formshare_*
    - [user]_[project]_*
  - Backup the file repository directory

Contributing
------------

The best way to contribute to FormShare is by testing it and posting issues. If you can fix things do the following:

1. Fork FormShare
2. Clone your fork in your local computer
3. Create a branch for your fix **based on the master branch**
4. Create the fix, commit the code, and push the branch to your forked repository
5. Create a pull request

We also appreciate and need translation files. See the Localization section.

Customization and Extension
------------
FormShare uses [PyUtilib Component Architecture](http://citeseerx.ist.psu.edu/viewdoc/download?doi=10.1.1.616.8737&rep=rep1&type=pdf) to allow customization and extension. The best way to do it is by using the [FormShare Plugin CookieCutter](https://github.com/qlands/formshare-cookiecutter-plugin) and explore the different Interfaces.

What can you do through extension plug-ins? Some ideas:

- Integrate the FormShare login with your company Windows Authentication.
- Change the colors, logos and all aspects of the user interface.
- Integrate messaging services like WhatsApp to inform field agents when a new version of a form is up.
- Collect data using USSD or IVR services with the same ODK form and store the data in the same repository no matter the source.
- Implement longitudinal surveys where the data of a form is pulled to populate the options of another form.

You basically can extend FormShare to fit your need. We are working on proper documentation for this.


Localization
------------

FormShare comes out of the box in English, Spanish, French, and Portuguese (Google generated). It uses Babel for translation and you can help us by creating new translations or by correcting an existing one.

To generate a new translation:


    $ cd formshare
    $ python setup.py init_catalog -l [new_language_ISO_639-1_code]
    $ python setup.py extract_messages
    $ python setup.py update_catalog

The translation files (.po) are available at formshare/locale/[language-code]/LC_MESSAGES. You can edit a .po file with tools like [PoEdit](https://poedit.net/download), [Lokalize](https://userbase.kde.org/Lokalize), [GTranslator](https://gitlab.gnome.org/GNOME/gtranslator), or a simple text editor. Once the translation is done you can send us the updated or new .po file as an issue and we will add it to FormShare.

## License

FormShare is released under the terms of the GNU Affero General Public License. 

The plug-in mechanism since it is based on PyUtilib is covered by a [BSD type of license](https://github.com/PyUtilib/pyutilib/blob/master/LICENSE.txt).