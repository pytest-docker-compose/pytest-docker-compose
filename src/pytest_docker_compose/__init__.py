import typing
from pathlib import Path
import warnings
from datetime import datetime

import pytest
from compose.cli.command import project_from_options
from compose.container import Container
from compose.project import Project
from compose.service import ImageType


class ContainersAlreadyExist(Exception):
    """Raised when running containers are unexpectedly found"""
    pass


__all__ = [
    "DockerComposePlugin",
    "NetworkInfo",
    "plugin",
]


class NetworkInfo:
    def __init__(self, container_port: typing.Text,
                 hostname: typing.Text, host_port: int,):
        """
        Container for info about how to connect to a service exposed by a
        Docker container.

        :param container_port: Port (and usually also protocol name) exposed
        internally on the container.
        :param hostname: Hostname to use when accessing this service.
        :param host_port: Port number to use when accessing this service.
        """
        self.container_port = container_port
        self.hostname = hostname
        self.host_port = host_port


def create_network_info_for_container(container):
    """
    Generates :py:class:`NetworkInfo` instances corresponding to all available
    port bindings in a container
    """
    return [NetworkInfo(container_port=container_port,
                        hostname=port_config["HostIp"] or "localhost",
                        host_port=port_config["HostPort"],)
            for container_port, port_configs in
            container.get("HostConfig.PortBindings").items()
            for port_config in port_configs]


class DockerComposePlugin:
    """
    Integrates docker-compose into pytest integration tests.
    """
    def __init__(self):
        self.function_scoped_containers = self.generate_scoped_containers_fixture('function')
        self.class_scoped_containers = self.generate_scoped_containers_fixture('class')
        self.module_scoped_containers = self.generate_scoped_containers_fixture('module')
        self.session_scoped_containers = self.generate_scoped_containers_fixture('session')

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

        group.addoption("--use-running-containers", action="store_true",
                        default=False, help="Boolean to use a running set of containers "
                                            "instead of calling 'docker-compose up'")

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
                    docker_compose=docker_compose.absolute(),
                ),
            )

        project = project_from_options(
            project_dir=str(docker_compose.parent),
            options={"--file": [docker_compose.name]},
        )

        if not request.config.getoption("--docker-compose-no-build"):
            project.build()

        # I don't think it's great style to monkey_patch project like this but
        # it is the most straightforward way of propagating this information
        setattr(project, 'pytest_use_running_containers',
                request.config.getoption("--use-running-containers"))

        if project.pytest_use_running_containers:
            if not request.config.getoption("--docker-compose-no-build"):
                warnings.warn(UserWarning(
                    "You used the '--use-running-containers' without the "
                    "'--docker-compose-no-build' flag, the newly build "
                    "containers won't be used if there are already "
                    "containers running!"))
            current_containers = project.containers()
            containers = project.up()
            if not set(current_containers) == set(containers):
                warnings.warn(UserWarning(
                    "You used the '--use-running-containers' but "
                    "pytest-docker-compose could not find all containers "
                    "running. The remaining containers have been started."))
        else:
            if any(project.containers()):
                raise ContainersAlreadyExist(
                    "There are already existing containers, please remove all "
                    "containers by running 'docker-compose down' before using "
                    "the pytest-docker-compose plugin. Alternatively, you "
                    "can use the '--use-running-containers' flag to indicate "
                    "you will use the currently running containers.")
        return project

    @pytest.fixture
    def docker_containers(self, docker_project: Project):
        """
        Depending on the 'pytest --use-running-containers' flag: either spins
        up all containers or returns the containers that are currently running.

        Note that this fixture's scope is a single test; the containers
        will be stopped after the test is finished if the
        '--use-running-containers' is not supplied to pytest.

        This is intentional; stopping the containers destroys local
        storage, so that the next test can start with fresh containers.
        """
        warnings.warn("This fixture will be deprecated in a future version in "
                      "favor of defining the fixture like this:\n"
                      "from pytest_docker_compose import "
                      "generate_scoped_containers_fixture\n"
                      "function_scoped_containers = "
                      "generate_scoped_containers_fixture('function')",
                      DeprecationWarning)
        if docker_project.pytest_use_running_containers:
            now = datetime.now()
            containers = docker_project.containers()
            yield containers
            self.print_container_logs(containers, now)
        else:
            containers = self._containers_up(docker_project)
            yield containers
            self.print_container_logs(containers)
            docker_project.down(ImageType.none, False)

    @pytest.fixture
    def docker_network_info(self, docker_containers: typing.List[Container]):
        """
        Returns hostnames and exposed port numbers for each container,
        so that tests can interact with them. Note that this fixture depends on
        'docker_containers' and is thus also function scoped.
        """
        warnings.warn("This fixture will be deprecated in a future version in "
                      "favor of defining the fixture like this:\n"
                      "from pytest_docker_compose import "
                      "generate_scoped_containers_fixture\n"
                      "function_scoped_containers = "
                      "generate_scoped_containers_fixture('function')",
                      DeprecationWarning)
        return self._extract_network_info(docker_containers)

    @classmethod
    def _containers_up(cls, docker_project: Project) -> typing.List[Container]:
        """Brings up all containers in the specified project."""
        if any(docker_project.containers()):
            raise ContainersAlreadyExist(
                'pytest-docker-compose tried to start containers but there are'
                ' already running containers: %s, you probably scoped your'
                ' tests wrong' % docker_project.containers())
        containers = docker_project.up()  # type: typing.List[Container]

        if not containers:
            raise ValueError("`docker-compose` didn't launch any containers!")

        return containers

    @staticmethod
    def print_container_logs(docker_containers: typing.Iterable[Container],
                             since: datetime = datetime.fromtimestamp(0)) -> None:
        """
        Send container logs to stdout, so that they get included in
        the test report.
        https://docs.pytest.org/en/latest/capture.html
        """
        for container in sorted(docker_containers, key=lambda c: c.name):
            header = "Logs from {name}:".format(name=container.name)
            print(header, '\n', "=" * len(header))
            print(container.logs(since=since).decode("utf-8", errors="replace")
                  or "(no logs)", '\n')

    @staticmethod
    def _extract_network_info(docker_containers: typing.Iterable[Container]) \
            -> typing.Dict[str, typing.List[NetworkInfo]]:
        """
        Generates :py:class:`NetworkInfo` instances for each container and
        returns them in a dict of lists.
        """
        return {container.name: create_network_info_for_container(container)
                for container in docker_containers}

    @classmethod
    def generate_scoped_containers_fixture(cls, scope):
        @pytest.fixture(scope=scope)
        def scoped_containers_fixture(docker_project: Project):
            now = datetime.utcnow()
            if docker_project.pytest_use_running_containers:
                containers = docker_project.containers()
            else:
                containers = cls._containers_up(docker_project)

            for container in containers:
                container.network_info = create_network_info_for_container(container)
            yield {container.name: container for container in containers}
            cls.print_container_logs(containers, now)

            if not docker_project.pytest_use_running_containers:
                docker_project.down(ImageType.none, False)
        scoped_containers_fixture.__wrapped__.__doc__ = """
            Spins up the containers for the Docker project and returns them in a
            dictionary. Each container has one additional attribute called
            network_info to simplify accessing the hostnames and exposed port
            numbers for each container.
            This set of containers is scoped to '%s'
            """ % scope
        return scoped_containers_fixture


plugin = DockerComposePlugin()
