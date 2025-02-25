from distutils.core import setup

setup(
    name='carpoolparty',
    version='1.0.0',
    packages=['carpoolparty'],
    include_package_data=True,
    license='MIT',
    description="Project that creates a carpool driving plan based on teachers' timetables",
    long_description="Project that creates a carpool driving plan based on teachers' timetables",
    author='Thabo Krick',
    author_email='thabokrick@gmail.com',
    url='https://github.com/thabok/scholars-hitch',
    install_requires=[ 'requests', 'pyyaml' ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Education',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],
)
