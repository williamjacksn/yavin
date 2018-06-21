from setuptools import setup

setup(
    name='yavin',
    version='1.0.0',
    description='Some personal web-based tools',
    url='https://github.com/williamjacksn/yavin',
    author='William Jackson',
    author_email='william@subtlecoolness.com',
    install_requires=['APScheduler', 'Flask', 'Flask-OAuth2-Login', 'Flask-SSLify', 'psycopg2', 'requests', 'waitress'],
    packages=['yavin'],
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'notify_due = yavin.notify:main',
            'yavin = yavin.yavin:main'
        ]
    }
)
