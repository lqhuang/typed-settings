from setuptools import find_packages, setup


DEPS = ["attrs>=20.3", "cattrs>=1.7", "toml>=0.10"]
DEPS_CLICK = ["click>=7,<9"]
DEPS_TEST = DEPS_CLICK + [
    "coverage[toml]>=5.3",
    "docutils",
    "pygments",
    "pytest-cov",
    "pytest>=6",
]
DEPS_LINT = DEPS_CLICK + [
    "flake8",
    "flake8-bandit",
    "flake8-black",
    "flake8-bugbear",
    "flake8-isort",
    "mypy",
    "types-docutils",
    "types-toml",
]
DEPS_DOCS = DEPS_CLICK + ["furo", "sphinx", "sphinx-autodoc-typehints"]
DEPS_DEV = DEPS_TEST + DEPS_LINT + DEPS_DOCS + ["nox", "safety"]


if __name__ == "__main__":
    setup(
        name="typed-settings",
        version="0.11.1",
        description="Typed settings based on attrs classes",
        license="MIT",
        url="https://gitlab.com/sscherfke/typed-settings",
        project_urls={
            "Documentation": "https://typed-settings.readthedocs.io",
            "Bug Tracker": "https://gitlab.com/sscherfke/typed-settings/-/issues",
            "Source Code": "https://gitlab.com/sscherfke/typed-settings",
        },
        author="Stefan Scherfke",
        author_email="stefan@sofa-rockers.org",
        maintainer="Stefan Scherfke",
        maintainer_email="stefan@sofa-rockers.org",
        keywords=["settings", "types", "configuration", "options"],
        long_description=open("README.rst").read(),
        long_description_content_type="text/x-rst",
        packages=find_packages(where="src"),
        package_dir={"": "src"},
        include_package_data=True,
        zip_safe=False,
        python_requires=">=3.7",
        install_requires=DEPS,
        extras_require={
            "click": DEPS_CLICK,
            "test": DEPS_TEST,
            "lint": DEPS_LINT,
            "docs": DEPS_DOCS,
            "dev": DEPS_DEV,
        },
        classifiers=[
            "Development Status :: 4 - Beta",
            "Environment :: Console",
            "Intended Audience :: Developers",
            "Natural Language :: English",
            "License :: OSI Approved :: MIT License",
            "Operating System :: OS Independent",
            "Programming Language :: Python",
            "Programming Language :: Python :: 3.7",
            "Programming Language :: Python :: 3.8",
            "Programming Language :: Python :: 3.9",
            "Programming Language :: Python :: 3.10",
            "Programming Language :: Python :: Implementation :: CPython",
            "Programming Language :: Python :: Implementation :: PyPy",
            "Topic :: Software Development :: Libraries :: Python Modules",
        ],
    )
