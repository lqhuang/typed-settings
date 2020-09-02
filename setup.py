from setuptools import setup


if __name__ == '__main__':
    setup(
        name='typed-settings',
        version='0.2',
        description='Typed settings based on attrs classes',
        license='MIT',
        url='https://gitlab.com/sscherfke/typed-settings',
        project_urls={
            'Documentation': 'https://gitlab.com/sscherfke/typed-settings',
            'Bug Tracker': 'https://gitlab.com/sscherfke/typed-settings/-/issues',
            'Source Code': 'https://gitlab.com/sscherfke/typed-settings',
        },
        author='Stefan Scherfke',
        author_email='stefan@sofa-rockers.org',
        maintainer='Stefan Scherfke',
        maintainer_email='stefan@sofa-rockers.org',
        keywords=['settings', 'types', 'configuration', 'options'],
        long_description=open('README.md').read(),
        long_description_content_type='text/markdown',
        # packages=find_packages(where='src'),
        py_modules=['typed_settings'],
        package_dir={'': 'src'},
        include_package_data=True,
        zip_safe=False,
        python_requires='>=3.7',
        install_requires=[
            'attrs',
            'toml',
        ],
        extras_require={
            'click': ['click'],
            'dev': [
                'click',
                'coverage[toml]>=5.0.2',
                'pytest-cov',
                'pytest>=6',
            ],
        },
        classifiers=[
            'Development Status :: 1 - Planning',
            'Environment :: Console',
            'Intended Audience :: Developers',
            'Natural Language :: English',
            'License :: OSI Approved :: MIT License',
            'Operating System :: OS Independent',
            'Programming Language :: Python',
            'Programming Language :: Python :: 3.7',
            'Programming Language :: Python :: 3.8',
            'Programming Language :: Python :: 3.9',
            'Programming Language :: Python :: Implementation :: CPython',
            'Programming Language :: Python :: Implementation :: PyPy',
            'Topic :: Software Development :: Libraries :: Python Modules',
        ],
    )
