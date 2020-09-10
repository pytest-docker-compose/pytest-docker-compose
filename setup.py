from setuptools import setup, find_packages

with open("README.rst", "r") as f:
    long_description = f.read()

setup(
    name="pytest-docker-compose",
    description="Manages Docker containers during your integration tests",
    long_description=long_description,
    version="3.2.0",
    author="Roald Storm",
    author_email="roaldstorm@gmail.com",
    url="https://github.com/pytest-docker-compose/pytest-docker-compose",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=["docker-compose", "pytest >= 3.3"],

    entry_points={
        "pytest11": [
            "docker_compose=pytest_docker_compose:plugin",
        ],
    },

    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Framework :: Pytest",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Software Development :: Testing",
    ],
)
