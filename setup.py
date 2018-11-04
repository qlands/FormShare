import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.md')) as f:
    README = f.read()
with open(os.path.join(here, 'CHANGES.txt')) as f:
    CHANGES = f.read()

requires = [
    'plaster_pastedeploy',
    'pyramid >= 1.9a',
    'pyramid_debugtoolbar',
    'pyramid_jinja2',
    'pyramid_retry',
    'pyramid_tm',
    'SQLAlchemy',
    'transaction',
    'zope.sqlalchemy',
    'waitress',
    'webhelpers2',
    'pyutilib == 5.4.1',
    'mysql-connector-python',
    'PyCrypto',
    'Babel',
    'lingua',
    'arrow',
    'cookiecutter',
    'formencode',
    'alembic',
    'gunicorn',
    'gevent',
    'ago',
    'lxml',
    'celery',
    'inflect',
    'validate_email'
]

postgresql_requires = ['psycopg2']

sqlserver_requires = ['pyodbc']

tests_require = [
    'WebTest >= 1.3.1',  # py3 compat
    'pytest',
    'pytest-cov',
]

setup(
    name='formshare',
    version='0.1',
    description='FormShare',
    long_description=README + '\n\n' + CHANGES,
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Pyramid',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Application',
    ],
    author='',
    author_email='',
    url='',
    keywords='web pyramid pylons',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    extras_require={
        'testing': tests_require,
    },
    install_requires=requires,
    entry_points={
        'paste.app_factory': [
            'main = formshare:main',
        ],
        'console_scripts': [
            'create_superuser = formshare.scripts.createsuperuser:main',
            'configure_celery = formshare.scripts.configurecelery:main'
        ],
    },
)
