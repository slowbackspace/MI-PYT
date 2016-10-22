from setuptools import setup, find_packages
 
with open('README') as f:
    long_description = ''.join(f.readlines())

setup(
    name='pygithublabeler',
    version='0.2.0',
    description='Magically (and with the power of regular expressions) attach labels to your github repository issues.',
    long_description=long_description,
    author='Maros Spak',
    author_email='slowbackspace@gmail.com',
    keywords='github labels issues',
    license='MIT',
    url='https://github.com/slowbackspace/pygithub-labeler',
    packages=find_packages(),
    #include_package_data=False,
    package_data={'pygithublabeler': ['rules.yml', "templates/*.html"]},
    install_requires=['Flask', 'click>=6', 'PyYAML', 'requests'],
    entry_points={
          'console_scripts': [
              'pygithublabeler = pygithublabeler.run:cli'
          ]
      },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX :: Linux',
        'Operating System :: MacOS',
        'Programming Language :: Python',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Topic :: Software Development :: Bug Tracking',
        'Framework :: Flask',
        ],
)
