from setuptools import setup


setup(
    name='typed-settings',
    version='0.1',
    install_requires=[
        'attrs',
        'toml',
    ],
    # packages=find_packages(where='src'),
    py_modules=['typed_settings'],
    package_dir={'': 'src'},
)
