FormShare 2
=========
The future of FormHub

Centralize data – Decentralize knowledge<sup>TM</sup>

About
-----
FormShare 2 is inspired from the excellent [FormHub](<http://github.com/SEL-Columbia/formhub>) platform developed by the Sustainable Engineering Lab at Columbia University. After I forked [OnaData](https://github.com/onaio/onadata) (a fork of FormHub) back in 2016 it was clear that the code needed at lot to bring it to the main ideas that I had: 1) Integrate it with [ODK Tools](https://github.com/qlands/odktools), 2) provide a proper MySQL repository to centralize the data and, 3) use latest software technologies to decentralize the management.

FormShare was created because:

* I want to provide a open source **free** platform to private and public organizations to help them manage their data when using ODK.
* ODK Aggregate, in my personal opinion, is badly designed, buggy and not interoperable. ODK Central is just not there yet.
* Forks based on FormHub suffer from the same ills of their father: Django (sorry if I hurt your feelings), no proper repository, rudimentary data cleaning, no auditing, little interoperability, poor or none extensibility... among many others.

FormShare 2 has been written from scratch (not a single line of code comes from Formhub, just ideas and principles) using Python 3, [Pyramid](https://trypyramid.com/) and [PyUtilib](https://github.com/PyUtilib/pyutilib) to deliver a complete and extensible data management solution for ODK Data collection. It took us three years but is finally here :-) and it is Django free!

FormShare **is for organizations** to install it in their own server or cloud service to serve ODK XForms and collect and manage the submissions. FormShare is also available as as service at https://formshare.qlands.com for those organizations that lacks the capacity or resources to run their own installation.

Screen Shot
----------

![Image](./Screenshot.png?raw=true "FormShare home screen")

Releases
------------
The current stable release is 2.5.1 and it is available [here](https://github.com/qlands/FormShare/tree/stable-2.5.1) 

Installation
------------
Please read the [Installation guide](install_steps.txt) if you want to install FormShare manually. However, we encourage you to use the Docker Compose file available in the docker_compose directory.

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
sudo git clone https://github.com/qlands/FormShare.git -b stable-2.0 formshare_source

# Copy the docker compose file from the source to a new directory
sudo mkdir formshare_docker_compose
sudo cp ./formshare_source/docker_compose/docker-compose.yml ./formshare_docker_compose/

# Make the directory structure for FormShare
sudo mkdir /opt/formshare
whoami=$(whoami)
sudo chown $whoami /opt/formshare
mkdir /opt/formshare/celery
mkdir /opt/formshare/log
mkdir /opt/formshare/repository
mkdir /opt/formshare/config
mkdir /opt/formshare/mysql
mkdir /opt/formshare/elasticsearch
mkdir /opt/formshare/elasticsearch/esdata
mkdir /opt/formshare/elasticsearch/esdata2
mkdir /opt/formshare/elasticsearch/esdata3

# Set enough memory for ElasticSearch
sudo sysctl -w vm.max_map_count=262144
echo 'vm.max_map_count=262144' | sudo tee -a /etc/sysctl.d/60-vm-max_map_count.conf

# Download all the required Docker Images
cd /opt/formshare_docker_compose
sudo docker-compose pull

# Edit the docker-compose.yml file to set the mysql root and FormShare admin passwords
nano /opt/formshare_docker_compose/docker-compose.yml
# Press Alt+Shit+3 to show the line numbers in Nano

Edit line 7: Change the root password from "my_secure_password" to your password
Edit line 76: Change the root password from "my_secure_password" to the same password of line 8
Edit line 77: Change the admin user name (optional)
Edit line 78: Change the admin user password from "my_secure_password" to your password
Edit line 79: Change the admin email address
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

# Start the FormShare containers. It will take about 3 minutes for all the containers to be ready.
# You can check the status with "sudo docker stats". FormShare will be ready for usage when the container reach about 1 GiB of MEM USAGE
# This is the only two commands you need to start FormShare after a server restart
cd /opt/formshare_docker_compose
sudo docker-compose up -d

# Browse to FormShare
http://[this server IP address]/formshare
```

## Upgrading information

Please read the upgrade guide if you have FormShare installed from source. If you use Docker then things are easier:

```sh
# Download the new version of formShare
sudo git clone https://github.com/qlands/FormShare.git -b stable-2.1 formshare_2.1_source

# Copy the docker compose file from the source to a new directory
sudo mkdir formshare_2.1_docker_compose
sudo cp ./formshare_2.1_source/docker_compose/docker-compose.yml ./formshare_2.1_docker_compose/

# Clean the docker networks and containters. WARNING! If you have other dockers besides FormShare you will need to remove the "fsnet" network and the FormShare container manually.
sudo docker network prune
sudo docker container prune

# Start the new version of FormShare. All required updates in the database and ini files will be done automatically.
cd /opt/formshare_2.1_docker_compose
sudo docker-compose up -d

```



Contributing
------------

The best way to contribute to FormShare is by testing it and posting issues. If you can fix things do the following:

1. Fork FormShare
2. Clone your fork in your local computer
3. Create a branch for your fix **based on the master branch**
4. Create the fix, commit and code an push that branch to your forked repository
5. Crate a pull request

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

FormShare comes out of the box in English, Spanish, French (Google generated) and Portuguese (Google generated). It uses Babel for translation and you can help us by creating new translations or by correcting an existing one.

To generate a new translation:


    $ cd formshare
    $ python setup.py init_catalog -l [new_language_ISO_639-1_code]
    $ python setup.py extract_messages
    $ python setup.py update_catalog

The translation files (.po) are available at formshare/locale/[language-code]/LC_MESSAGES. You can edit a .po file with tools like [PoEdit](https://poedit.net/download), [Lokalize](https://userbase.kde.org/Lokalize), [GTranslator](https://gitlab.gnome.org/GNOME/gtranslator) or a simple text editor. Once the translation is done you can send us the updated or new .po file as an issue and we will add it to FormShare.

## License

FormShare is released under the terms of the GNU Affero General Public License. 

The plug-in mechanism since it is based on PyUtilib is covered by a [BSD like license](https://github.com/PyUtilib/pyutilib/blob/master/LICENSE.txt).