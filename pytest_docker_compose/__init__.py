import typing
from pathlib import Path

import pytest
from compose.cli.command import project_from_options
from compose.container import Container
from compose.project import Project
from compose.service import ImageType


__all__ = [
    "DockerComposePlugin",
    "NetworkInfo",
    "plugin",
]


class NetworkInfo:
    """
    Container for info about how to connect to a service exposed by a
    Docker container.
    """
    container_port: typing.Text
    """
    Port (and usually also protocol name) exposed internally on the
    container.
    """

    hostname: typing.Text
    """
    Hostname to use when accessing this service.
    """

    host_port: int
    """
    Port number to use when accessing this service.
    """

    def __init__(
            self,
            container_port: typing.Text,
            hostname: typing.Text,
            host_port: int,
    ):
        super().__init__()

        self.container_port = container_port
        self.hostname = hostname
        self.host_port = host_port


class DockerComposePlugin:
    """
    Integrates docker-compose into pytest integration tests.
    """

    # noinspection SpellCheckingInspection
    @staticmethod
    def pytest_addoption(parser):
        """
        Adds custom options to the ``pytest`` command.

        https://docs.pytest.org/en/latest/writing_plugins.html#_pytest.hookspec.pytest_addoption
        """
        group = parser.getgroup("docker_compose", "integration tests")

        group.addoption(
            "--docker-compose",
            dest="docker_compose",
            default=".",
            help="Path to docker-compose.yml file, or directory containing same.",
        )

    @pytest.fixture
    def docker_containers(self, docker_project: Project):
        """
        Spins up a the containers for the Docker project and returns
        them.

        Note that this fixture's scope is a single test; the containers
        will be stopped after the test is finished.

        This is intentional; stopping the containers destroys local
        storage, so that the next test can start with fresh containers.
        """
        containers: typing.List[Container] = docker_project.up()

        if not containers:
            raise ValueError("`docker-compose` didn't launch any containers!")

        yield containers

        # Send container logs to stdout, so that they get included in
        # the test report.
        # https://docs.pytest.org/en/latest/capture.html
        for container in sorted(containers, key=lambda c: c.name):
            header = f"Logs from {container.name}:"
            print(header)
            print("=" * len(header))
            print(
                container.logs().decode("utf-8", errors="replace") or
                "(no logs)"
            )
            print()

        docker_project.down(ImageType.none, False)

    @pytest.fixture
    def docker_network_info(self, docker_containers: typing.List[Container]):
        """
        Returns hostnames and exposed port numbers for each container,
        so that tests can interact with them.
        """
        return {
            container.name: [
                NetworkInfo(
                    container_port=container_port,
                    hostname=port_config["HostIp"] or "localhost",
                    host_port=port_config["HostPort"],
                )

                # Example::
                #
                #   {'8181/tcp': [{'HostIp': '', 'HostPort': '8182'}]}
                for container_port, port_configs
                in container.get("HostConfig.PortBindings").items()

                for port_config in port_configs
            ]

            for container in docker_containers
        }

    @pytest.fixture(scope="session")
    def docker_project(self, request):
        """
        Builds the Docker project if necessary, once per session.

        Returns the project instance, which can be used to start and stop
        the Docker containers.
        """
        docker_compose = Path(request.config.getoption("docker_compose"))

        if docker_compose.is_dir():
            docker_compose /= "docker-compose.yml"

        if not docker_compose.is_file():
            raise ValueError(
                f"Unable to find `{docker_compose}` for integration tests.",
            )

        project = project_from_options(
            project_dir=str(docker_compose.parent),
            options={"--file": [docker_compose.name]},
        )
        project.build()

        return project


plugin = DockerComposePlugin()
