from setuptools import setup

setup(
    name="pytest-docker-compose",
    version="1.0.0",
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
