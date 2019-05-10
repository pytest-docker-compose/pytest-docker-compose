import typing
from pathlib import Path

import pytest
from compose.cli.command import project_from_options
from compose.container import Container
from compose.project import Project
from compose.service import ImageType


class ContainerAlreadyExist(Exception):
    """Raised when running containers are found during docker compose up"""
    pass


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
    container_port = None  # type: typing.Text
    """
    Port (and usually also protocol name) exposed internally on the
    container.
    """

    hostname = None  # type: typing.Text
    """
    Hostname to use when accessing this service.
    """

    host_port = None  # type: int
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

        group.addoption("--docker-compose-no-build", action="store_true",
                        default=False, help="Boolean to not build docker containers")

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
        containers = self._containers_up(docker_project)

        yield containers

        self._containers_down(docker_project, containers)

    @pytest.fixture
    def docker_network_info(self, docker_containers: typing.List[Container]):
        """
        Returns hostnames and exposed port numbers for each container,
        so that tests can interact with them.
        """
        return self._extract_network_info(docker_containers)

    @pytest.fixture(scope="function")
    def docker_network_info_function(self, docker_project: Project):
        containers = self._containers_up(docker_project)
        yield self._extract_network_info(containers)
        self._containers_down(docker_project, containers)

    @pytest.fixture(scope="class")
    def docker_network_info_class(self, docker_project: Project):
        containers = self._containers_up(docker_project)
        yield self._extract_network_info(containers)
        self._containers_down(docker_project, containers)

    @pytest.fixture(scope="module")
    def docker_network_info_module(self, docker_project: Project):
        containers = self._containers_up(docker_project)
        yield self._extract_network_info(containers)
        self._containers_down(docker_project, containers)

    @pytest.fixture(scope="session")
    def docker_network_info_session(self, docker_project: Project):
        containers = self._containers_up(docker_project)
        yield self._extract_network_info(containers)
        self._containers_down(docker_project, containers)

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
                "Unable to find `{docker_compose}` "
                "for integration tests.".format(
                    docker_compose=docker_compose,
                ),
            )

        project = project_from_options(
            project_dir=str(docker_compose.parent),
            options={"--file": [docker_compose.name]},
        )

        if not request.config.getoption("--docker-compose-no-build"):
            project.build()

        return project

    @classmethod
    def _containers_up(cls, docker_project: Project) -> typing.List[Container]:
        """
        Brings up all containers in the specified project.
        """
        if any(docker_project.containers()):
            raise ContainerAlreadyExist(f'pytest-docker-compose tried to '
                                        f'start containers but there are '
                                        f'already running containers: '
                                        f'{docker_project.containers()}, you '
                                        f'probably scoped your tests wrong')
        containers = docker_project.up()  # type: typing.List[Container]

        if not containers:
            raise ValueError("`docker-compose` didn't launch any containers!")

        return containers

    @classmethod
    def _containers_down(
            cls,
            docker_project: Project,
            docker_containers: typing.Iterable[Container],
    ) -> None:
        """
        Brings down containers that were launched using
        :py:meth:`_containers_up`.
        """
        # Send container logs to stdout, so that they get included in
        # the test report.
        # https://docs.pytest.org/en/latest/capture.html
        for container in sorted(docker_containers, key=lambda c: c.name):
            header = "Logs from {name}:".format(name=container.name)
            print(header)
            print("=" * len(header))
            print(
                container.logs().decode("utf-8", errors="replace") or
                "(no logs)"
            )
            print()

        docker_project.down(ImageType.none, False)

    @classmethod
    def _extract_network_info(
            cls,
            docker_containers: typing.Iterable[Container],
    ) -> typing.Dict[str, typing.List[NetworkInfo]]:
        """
        Generates :py:class:`NetworkInfo` instances corresponding to the
        specified containers.
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


plugin = DockerComposePlugin()
