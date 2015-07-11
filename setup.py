import os, sys
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


def main():
    setup(
        name='sysutils',
        version= '1.0.0',
        author='Andrew Gillis',
        author_email='gillis.andrewj@gmail.com',
        url='https://github.com/gammazero/py-sysutils',
        description='sysutils: System utility modules',
        long_description = 'See https://github.com/gammazero/py-sysutils',
        license='http://www.opensource.org/licenses/mit-license.php',
        platforms=['unix', 'linux', 'cygwin', 'win32'],
        keywords='system CLI utility',
        classifiers=['Development Status :: 5 - Production/Stable',
                     'Intended Audience :: Developers',
                     'License :: OSI Approved :: MIT License',
                     'Operating System :: POSIX',
                     'Operating System :: Microsoft :: Windows',
                     'Topic :: Software Development :: Libraries',
                     'Topic :: Utilities',
                     'Programming Language :: Python',
                     'Programming Language :: Python :: 2.7',
                     'Programming Language :: Python :: 3'],
        packages=['sysutils'],
        zip_safe=True,
        )


if __name__ == '__main__':
    main()