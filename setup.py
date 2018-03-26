from setuptools import setup

with open("README.rst", "r") as f:
    long_description = f.read()

setup(
    name="pytest-docker-compose",
    description="Manages Docker containers during your integration tests",
    long_description=long_description,
    version="1.0.1",
    author="Phoenix Zerin",
    author_email="phoenix.zerin@centrality.ai",
    url="https://github.com/Centraliyai/pytest-docker-compose",
    packages=["pytest_docker_compose"],
    install_requires=["docker-compose", "pytest >= 3.4"],

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
