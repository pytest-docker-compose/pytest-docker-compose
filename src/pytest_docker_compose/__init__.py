from typing import List
import os.path
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
    def __init__(self, container_port: str, hostname: str, host_port: int,):
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


def create_network_info_for_container(container: Container):
    """
    Generates :py:class:`NetworkInfo` instances corresponding to all available
    port bindings in a container
    """
    # If ports are exposed by the docker container but not by docker expose
    # container.ports looks like this:
    # container.ports == {'4369/tcp': None,
    # '5984/tcp': [{'HostIp': '0.0.0.0', 'HostPort': '32872'}],
    # '9100/tcp': None}
    return [NetworkInfo(container_port=container_port,
                        hostname=port_config["HostIp"] or "localhost",
                        host_port=port_config["HostPort"],)
            for container_port, port_configs in container.ports.items()
            if port_configs is not None for port_config in port_configs]


class DockerComposePlugin:
    """
    Integrates docker-compose into pytest integration tests.
    """
    def __init__(self):
        self.function_scoped_container_getter = self.generate_scoped_containers_fixture('function')
        self.class_scoped_container_getter = self.generate_scoped_containers_fixture('class')
        self.module_scoped_container_getter = self.generate_scoped_containers_fixture('module')
        self.session_scoped_container_getter = self.generate_scoped_containers_fixture('session')

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

        group.addoption("--docker-compose-remove-volumes", action="store_true",
                        default=False, help="Remove docker container volumes after tests")

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

        compose_files = []

        for docker_compose in [Path(f) for f in request.config.getoption("docker_compose").split(',')]:
            if docker_compose.is_dir():
                docker_compose /= "docker-compose.yml"

            if not docker_compose.is_file():
                raise ValueError(
                    "Unable to find `{docker_compose}` "
                    "for integration tests.".format(
                        docker_compose=docker_compose.absolute(),
                    ),
                )

            compose_files.append(docker_compose)

        if len(compose_files) > 1:
            # py35 needs strings for os.path functions
            project_dir = os.path.commonpath([str(f) for f in compose_files]) or '.'
            compose_files = [p.relative_to(project_dir) for p in compose_files]
        else:
            project_dir = '.'

        # py35 needs strings for os.path functions
        compose_files = map(str, compose_files)

        project = project_from_options(
            project_dir=str(project_dir),
            options={"--file": compose_files},
        )

        if not request.config.getoption("--docker-compose-no-build"):
            project.build()

        if request.config.getoption("--use-running-containers"):
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

    @classmethod
    def generate_scoped_containers_fixture(cls, scope: str):
        """
        Create scoped fixtures that retrieve or spin up all containers, and add
        network info objects to containers and then yield the containers for
        duration of test.

        After the tests wrap up the fixture prints the logs of each containers
        and tears them down unless '--use-running-containers' was supplied.
        """
        @pytest.fixture(scope=scope)  # type: ignore
        def scoped_containers_fixture(docker_project: Project, request):
            now = datetime.utcnow()
            if request.config.getoption("--use-running-containers"):
                containers = docker_project.containers()  # type: List[Container]
            else:
                if any(docker_project.containers()):
                    raise ContainersAlreadyExist(
                        'pytest-docker-compose tried to start containers but there are'
                        ' already running containers: %s, you probably scoped your'
                        ' tests wrong' % docker_project.containers())
                containers = docker_project.up()
                if not containers:
                    raise ValueError("`docker-compose` didn't launch any containers!")

            container_getter = ContainerGetter(docker_project)
            yield container_getter

            if request.config.getoption("--verbose"):
                for container in sorted(containers, key=lambda c: c.name):
                    header = "Logs from {name}:".format(name=container.name)
                    print(header, '\n', "=" * len(header))
                    print(container.logs(since=now).decode("utf-8", errors="replace")
                          or "(no logs)", '\n')

            if not request.config.getoption("--use-running-containers"):
                docker_project.down(ImageType.none, request.config.getoption("--docker-compose-remove-volumes"))

        scoped_containers_fixture.__wrapped__.__doc__ = """
            Spins up the containers for the Docker project and returns an
            object that can retrieve the containers. The returned containers
            all have one additional attribute called network_info to simplify
            accessing the hostnames and exposed port numbers for each container.
            This set of containers is scoped to '%s'
            """ % scope
        return scoped_containers_fixture


plugin = DockerComposePlugin()


class ContainerGetter:
    """
    A class that retrieves containers from the docker project and adds a
    convenience wrapper for the available ports
    """
    def __init__(self, docker_project: Project) -> None:
        self.docker_project = docker_project

    def get(self, key: str) -> Container:
        containers = self.docker_project.containers(service_names=[key])
        if not containers:
            containers = self.docker_project.containers(service_names=[key], stopped=True)
            warnings.warn(UserWarning(
                "The service '%s' only has a stopped container, "
                "it stopped with '%s'" % (key, containers[0].human_readable_state)
            ))
        container = containers[0]
        container.network_info = create_network_info_for_container(container)
        return container
