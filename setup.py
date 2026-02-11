
from setuptools import setup, find_packages

# Call the setup function with the minium named arguments
setup(
    # the name of the library (will be listed with pip list)
    name="mirrsearch",
    # the find_packages function will return a list of packages in src
    packages=find_packages('src'),
    # The empty key stands for the root package
    # See https://docs.python.org/3/distutils/setupscript.html#listing-whole-packages
    package_dir={'': 'src'}
)
