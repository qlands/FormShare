import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, "README.md")) as f:
    README = f.read()
with open(os.path.join(here, "CHANGES.txt")) as f:
    CHANGES = f.read()

requires = [
    "alabaster",
    "alembic",
    "amqp",
    "appdirs",
    "arrow",
    "attrs",
    "Babel",
    "backports.csv",
    "beautifulsoup4",
    "billiard",
    "binaryornot",
    "black",
    "boto",
    "celery",
    "certifi",
    "cffi",
    "chardet",
    "charset-normalizer",
    "cheroot",
    "CherryPy",
    "click",
    "click-didyoumean",
    "click-plugins",
    "click-repl",
    "cookiecutter",
    "coverage",
    "cryptography",
    "decorator",
    "docutils",
    "elasticsearch",
    "emoji",
    "feedparser",
    "FormEncode",
    "future",
    "gevent",
    "greenlet",
    "gunicorn",
    "hupper",
    "idna",
    "imagesize",
    "importlib-resources",
    "iniconfig",
    "jaraco.classes",
    "jaraco.collections",
    "jaraco.functools",
    "jaraco.text",
    "Jinja2",
    "jinja2-time",
    "joblib",
    "kombu",
    "linecache2",
    "lxml",
    "Mako",
    "MarkupSafe",
    "more-itertools",
    "mypy-extensions",
    "mysql-connector-python",
    "mysqlclient",
    "nltk",
    "nose",
    "numpy",
    "ofs",
    "packaging",
    "paginate",
    "paho-mqtt",
    "Pairtree",
    "pandas",
    "PasteDeploy",
    "pathspec",
    "Pattern",
    "pdfminer.six",
    "Pillow",
    "plaster",
    "plaster-pastedeploy",
    "platformdirs",
    "pluggy",
    "portend",
    "poyo",
    "prompt-toolkit",
    "protobuf",
    "py",
    "pycparser",
    "pycrypto",
    "pycryptodome",
    "Pygments",
    "pyparsing",
    "pyramid",
    "pyramid-authstack",
    "pyramid-debugtoolbar",
    "pyramid-jinja2",
    "pyramid-mako",
    "pyramid-retry",
    "pyramid-session-multi",
    "pyramid-session-redis",
    "pyramid-tm",
    "pytest",
    "pytest-cov",
    "python-dateutil",
    "python-docx",
    "python-editor",
    "python-slugify",
    "pytz",
    "PyUtilib",
    "pyxform",
    "qrcode",
    "redis",
    "regex",
    "repoze.lru",
    "requests",
    "rutter",
    "scipy",
    "sgmllib3k",
    "simplekml",
    "six",
    "snowballstemmer",
    "sortedcontainers",
    "soupsieve",
    "Sphinx",
    "sphinxcontrib-applehelp",
    "sphinxcontrib-devhelp",
    "sphinxcontrib-htmlhelp",
    "sphinxcontrib-jsmath",
    "sphinxcontrib-qthelp",
    "sphinxcontrib-serializinghtml",
    "SQLAlchemy",
    "tempora",
    "text-unidecode",
    "timeago",
    "toml",
    "tomli",
    "tqdm",
    "traceback2",
    "transaction",
    "translationstring",
    "typed-ast",
    "typing-extensions",
    "unicodecsv",
    "unittest2",
    "urllib3",
    "validators",
    "venusian",
    "vine",
    "waitress",
    "wcwidth",
    "WebHelpers2",
    "WebOb",
    "WebTest",
    "xlrd",
    "zc.lockfile",
    "zipp",
    "zope.deprecation",
    "zope.event",
    "zope.interface",
    "zope.sqlalchemy",
]

postgresql_requires = ["psycopg2"]

sqlserver_requires = ["pyodbc"]

tests_require = ["WebTest >= 1.3.1", "pytest", "pytest-cov"]  # py3 compat

setup(
    name="formshare",
    version="2.11.1",
    description="FormShare",
    long_description=README + "\n\n" + CHANGES,
    classifiers=[
        "Programming Language :: Python",
        "Framework :: Pyramid",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
    ],
    author="",
    author_email="",
    url="",
    keywords="web pyramid pylons",
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    extras_require={"testing": tests_require},
    install_requires=requires,
    entry_points={
        "paste.app_factory": ["main = formshare:main"],
        "console_scripts": [
            "create_superuser = formshare.scripts.createsuperuser:main",
            "configure_mysql = formshare.scripts.configuremysql:main",
            "configure_alembic = formshare.scripts.configurealembic:main",
            "configure_fluent = formshare.scripts.configurefluent:main",
            "modify_config = formshare.scripts.modifyconfig:main",
            "configure_tests = formshare.scripts.configuretests:main",
            "disable_ssl = formshare.scripts.disablessl:main",
            "update_aes_key = formshare.scripts.updateaeskey:main",
        ],
    },
)
