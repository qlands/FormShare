FormShare
=================
The continuation of FormHub

Collect, Analyze and Share **YOUR** Data!

About
-----
FormShare is derived from the excellent [Formhub](<http://github.com/SEL-Columbia/formhub>) platform developed by the Sustainable Engineering Lab at Columbia University. Later version of FormHub were developed by [Ona IO](https://ona.io/home/) as a software as service under the name of [OnaData](https://github.com/onaio/onadata) but then the code was left broken and unmaintained in favor of an "API" based platform. Formshare is the continuation of Formhub.

FormShare was created because:

* I want to provide a open source **free** platform to private and public organizations for them to collect their own data.
* ODK Aggregate, in my personal opinion, is badly designed, buggy and not interoperable.
* Ona.io will not maintain the user interface. I will maintain it.
* There are some things that does not work. I will dedicate time to fix them.
* Most of its dependencies might change over time and break the code. I will check them
* The Formhub project is to good to lose it!

FormShare **is not a software as service application** thus is nowhere for you to sign up and pay for a subscription. FormShare **is for organizations** to install it in their own server or cloud service to serve ODK XForms and collect the submissions.

ScreenShot
----------

![Image](/Screenshot.png?raw=true "FormShare home screen")

Installation
------------
Please read the [Installation and Deployment Guide](install.md).

Contributing
------------

The best way to contribute to FormShare is by posting issues. Also if you can create a fix do:

1. Fork FormShare
2. Clone your fork in your local computer
3. Create a branch for your fix
4. Create the fix, commit and code an push the branch
5. Crate a pull request

Code Structure
--------------

* **logger** - This app serves XForms to and receives submissions from
  ODK Collect and Enketo.

* **viewer** - This app provides a csv and xls export of the data stored in
  logger. This app uses a data dictionary as produced by pyxform. It also
  provides a map and single survey view.

* **main** - This app is the glue that brings logger and viewer
  together.

Customization
------------
At the moment there is no simple way to customize or extend the interface of FormShare. However you can edit some of the template files:
  - The footer can be found at formshare/formshare/libs/templates/footer.html . You can add any extra information here to appear in all the pages.
  - The homepage can be found at formshare/apps/main/templates/home.html . There is a section for logos there.


Localization
------------

To generate a locale from scratch (ex. Spanish)

.. code-block:: sh

    $ django-admin.py makemessages -l es -e py,html,email,txt ;
    $ for app in {main,viewer} ; do cd formshare/apps/${app} && django-admin.py makemessages -d djangojs -l es && cd - ; done

To update PO files

.. code-block:: sh

    $ django-admin.py makemessages -a ;
    $ for app in {main,viewer} ; do cd formshare/apps/${app} && django-admin.py makemessages -d djangojs -a && cd - ; done

To compile MO files and update live translations

.. code-block:: sh

    $ django-admin.py compilemessages ;
    $ for app in {main,viewer} ; do cd formshare/apps/${app} && django-admin.py compilemessages && cd - ; done

Api Documentation
-----------------

.. code-block:: sh

    $ cd docs
    $ make html
    $ python manage.py collectstatic
