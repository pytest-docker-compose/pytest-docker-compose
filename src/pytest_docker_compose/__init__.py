import os
import time
from typing import List
from pathlib import Path
import warnings
from datetime import datetime

import pytest
from compose.cli.command import project_from_options
from compose.config.errors import ComposeFileNotFound
from compose.container import Container
from compose.project import Project
from compose.service import ImageType


class ContainersAlreadyExist(Exception):
    """Raised when running containers are unexpectedly found"""
    pass


class ContainerDoesntExist(Exception):
    """Raised when container doesn't exists"""
    pass


class ContainerNotRunning(Exception):
    """Raised when container doesn't exists"""
    pass


__all__ = [
    "DockerComposePlugin",
    "NetworkInfo",
    "plugin",
]


class NetworkInfo:
    def __init__(self, container_port: str, hostname: str, host_port: int, ):
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
                        host_port=port_config["HostPort"], )
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
            action='append',
            dest="docker_compose",
            default=[],
            help="Path to docker-compose.yml file, or directory containing same.",
        )

        group.addoption(
            "--docker-compose-directory",
            dest="project_dir",
            default=[],
            help="Path to docker-compose directory",
        )

        group.addoption("--docker-compose-remove-volumes", action="store_true",
                        default=False, help="Remove docker container volumes after tests")

        group.addoption("--docker-compose-no-build", action="store_true",
                        default=False, help="Boolean to not build docker containers")

        group.addoption("--use-running-containers", action="store_true",
                        default=False, help="Boolean to use a running set of containers "
                                            "instead of calling 'docker-compose up'")

    @classmethod
    def project_from_options_for_each_dir(cls, dirs, *args, **kwargs):
        """
        Create the Docker project from options, trying each project_dirs.
        """
        exc = None
        for project_dir in dirs:
            try:
                project = project_from_options(project_dir=project_dir, *args, **kwargs)
                return project, project_dir
            except ComposeFileNotFound as local_exc:
                exc = local_exc
        raise exc

    @classmethod
    def projectdir_from_basedirs_and_docker_compose_options(cls, basedirs, docker_compose_options):
        """
        Get the project directory from possible basedirs and given --docker-compose options.
        """
        for basedir in basedirs:
            found = True
            for docker_compose_option in docker_compose_options:
                docker_compose_path = Path(basedir).joinpath(docker_compose_option)
                if not docker_compose_path.is_file() and not docker_compose_path.is_dir():
                    found = False
                    break
            if found:
                return basedir
        return basedirs[-1]  # Fallback to last one

    @pytest.fixture(scope="session")
    def all_docker_projects(self):
        """
        Contains all docker projects for the current session, as a dict.
        """
        return {}

    @classmethod
    def get_docker_project(cls, request, all_docker_projects):
        """
        Get the Docker project, creating a new one if it doesn't exists.

        Returns the project instance, which can be used to start and stop the Docker containers.
        """
        testdir = request.fspath.dirname
        project_dir = request.config.getoption("project_dir")

        if project_dir:
            basedirs = [project_dir]
        else:
            basedirs = [d for d in (os.path.join(testdir, 'docker-compose'), testdir, '.') if Path(d).is_dir()]

        project = None
        for basedir in basedirs:
            try:
                project = all_docker_projects[basedir]
                break
            except KeyError:
                pass

        if not project:
            docker_compose_options = request.config.getoption("docker_compose")
            if docker_compose_options:
                files = []

                split_deprecated_displayed = False

                splitted_docker_compose_options = []
                for docker_compose_option in docker_compose_options:
                    if ',' in docker_compose_option:
                        if not split_deprecated_displayed:
                            warnings.warn(DeprecationWarning(
                                "Using ',' in --docker-compose option to specify multiple compose files is deprecated." 
                                "You can now use --docker-compose many times in the same command."))
                            split_deprecated_displayed = True

                        for splitted_docker_compose_option in docker_compose_option.split(','):
                            splitted_docker_compose_options.append(splitted_docker_compose_option)
                    else:
                        splitted_docker_compose_options.append(docker_compose_option)

                if not project_dir:
                    project_dir = cls.projectdir_from_basedirs_and_docker_compose_options(
                        basedirs, docker_compose_options)

                for docker_compose_option in docker_compose_options:
                    docker_compose_path = Path(project_dir).joinpath(docker_compose_option)

                    if docker_compose_path.is_dir():
                        docker_compose_path = docker_compose_path.joinpath("docker-compose.yml")

                    if not docker_compose_path.is_file():
                        raise ValueError(
                            "Unable to find `{docker_compose}` "
                            "for integration tests in following directories: `{basedirs}`.".format(
                                docker_compose=docker_compose_option,
                                basedirs=basedirs
                            ),
                        )

                    files.append(str(docker_compose_path.relative_to(project_dir)))

                project_key = '|'.join(files)
                project = project_from_options(
                    project_dir=str(project_dir),
                    options={"--file": files},
                )
            else:
                project, project_key = cls.project_from_options_for_each_dir(basedirs, options={})

            all_docker_projects[project_key] = project

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
        def scoped_containers_fixture(request, all_docker_projects):
            docker_project = cls.get_docker_project(request, all_docker_projects)

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

    def get(self, key: str, wait_running=True, timeout=15) -> Container:
        containers = self.docker_project.containers(service_names=[key], stopped=True)
        if not containers:
            raise ContainerDoesntExist("The service '%s' doesn't exists" % key)

        container = containers[0]
        if wait_running:
            start = time.time()
            while not container.is_running or container.is_restarting:
                if time.time() - start >= timeout:
                    raise ContainerNotRunning("The service '%s' is still %s after %s seconds" %
                                              (key, container.human_readable_state, timeout))
                time.sleep(0.1)
                containers = self.docker_project.containers(service_names=[key], stopped=True)
                if not containers:
                    raise ContainerDoesntExist("The service '%s' doesn't exists" % key)
                container = containers[0]

            # network_info is added only for wait running as it may lead to race condition issues.
            container.network_info = create_network_info_for_container(container)
        return container
