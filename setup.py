try:
    from setuptools import setup, find_packages
except ImportError:
    from distribute_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

setup(
    name='rug',
    version="0.0",
    description='manage repositories of repositories',
    url='https://github.com/abstrakraft/rug',
    license='GPLv3',
    install_requires=[],
    packages=find_packages(exclude=['ez_setup']),
    include_package_data=True,
    package_data={'rug': ['i18n/*/LC_MESSAGES/*.mo']},
    entry_points="""
[console_scripts]
rug = rug.rug:main
""",
)
