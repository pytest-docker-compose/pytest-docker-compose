from setuptools import setup

setup(
    name="pytest-docker-compose",
    version="1.0.0",
    author="Phoenix Zerin",
    author_email="phoenix.zerin@centrality.ai",
    url="https://github.com/Centraliyai/pytest-docker-compose",
    packages=["pytest_docker_compose"],
    install_requires=["docker-compose", "pytest"],

    entry_points={
        "pytest11": [
            "docker_compose=pytest_docker_compose:plugin",
        ],
    }
)
