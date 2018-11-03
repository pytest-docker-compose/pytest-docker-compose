pytest-docker-compose
=====================
This package contains a `pytest`_ plugin for integrating Docker Compose into
your automated integration tests.

Given a path to a ``docker-compose.yml`` file, it will automatically build the
project at the start of the test run, bring the containers up before each test
starts, and tear them down after each test ends.


Dependencies
------------
Make sure you have `Docker`_ installed.

This plugin has been tested against the following software:

- Python 3.6 and 3.5.
- pytest 3.5 and 3.4.

.. note:: This plugin is **not** compatible with Python 2.


Installation
------------
Install the plugin using pip::

    > pip install pytest-docker-compose


Usage
-----
For performance reasons, the plugin is not enabled by default, so you must
activate it manually in the tests that use it:

.. code-block:: python

    pytest_plugins = ["docker_compose"]

See `Installing and Using Plugins`_ for more information.

To interact with Docker containers in your tests, use the following fixtures:

``docker_network_info``
    A list of ``pytest_docker_compose.NetworkInfo`` objects for each container,
    grouped by service name.

    This information can be used to configure API clients and other objects that
    will connect to services exposed by the Docker containers in your tests.

    ``NetworkInfo`` is a container with the following fields:

    - ``container_port``: The port (and usually also protocol name) exposed
      internally to the container.  You can use this value to find the correct
      port for your test, when the container exposes multiple ports.

    - ``hostname``: The hostname (usually "localhost") to use when connecting to
      the service from the host.

    - ``host_port``: The port number to use when connecting to the service from
      the host.

    .. tip::
        Unless you need to interface directly with Docker primitives, this is
        the correct fixture to use in your tests.

``docker_containers``
    A list of the Docker ``compose.container.Container`` objects running during
    the test.

``docker_project``
    The ``compose.project.Project`` object that the containers are built from.
    This fixture is generally only used internally by the plugin.


Fixture Scope
~~~~~~~~~~~~~
The ``docker_network_info`` and ``docker_containers`` fixtures use "function"
scope, meaning that all of the containers are torn down after each individual
test.

This is done so that every test gets to run in a "clean" environment.

However, this can potentially make a test suite take a very long time to
complete, so you can declare you own versions of the fixtures with a different
scope if desired.

Here is an example of creating a fixture that will keep all of the containers
running throughout the entire test session:

.. code-block:: python

    import pytest
    from pytest_docker_compose import DockerComposePlugin

    @pytest.fixture(scope="session"):
    def session_containers(docker_project):
      containers = DockerComposePlugin._containers_up(docker_project)
      yield containers
      DockerComposePlugin._containers_down(docker_project, containers)

    @pytest.fixture(scope="session"):
    def session_network_info(session_containers):
      return DockerComposePlugin._extract_network_info(session_containers)

.. caution::
    Take extra care to ensure that residual data/configuration/files/etc. are
    cleaned up on all of the containers after each test!

.. danger::
    This functionality has not been tested extensively, and you may run into
    strange and/or difficult-to-isolate issues that are unique to your
    environment/configuration/etc.

    It is strongly recommended that you investigate alternative approaches to
    improving test performance, for example by using `pytest-xdist`_ to run
    tests in parallel.

Waiting for Services to Come Online
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The fixture will wait until every container is up before handing control over to
the test.

However, just because a container is up does not mean that the services running
on it are ready to accept incoming requests yet!

If your tests need to wait for a particular condition (for example, to wait for
an HTTP health check endpoint to send back a 200 response), make sure that your
fixtures account for this.

Here's a simple example of a fixture that waits for an HTTP service to come
online before starting each test.

.. code-block:: python

    import pytest
    import typing
    from pytest_docker_compose import NetworkInfo
    from time import sleep, time

    from my_app import ApiClient

    pytest_plugins = ["docker_compose"]


    @pytest.fixture(name="api_client")
    def fixture_api_client(
            docker_network_info: typing.Dict[str, typing.List[NetworkInfo]],
    ) -> ApiClient:
        # ``docker_network_info`` is grouped by service name.
        service = docker_network_info["my_api_service"][0]

        # Create an instance of our custom application's API client.
        api_client = ApiClient(
            base_url=f"http://{service.hostname}:{service.host_port}/api/v1",
        )

        # Wait for the HTTP service to be ready.
        start = time()
        timeout = 5

        for name, network_info in docker_network_info.items():
            while True:
                if time() - start >= timeout:
                    raise RuntimeError(
                        f"Unable to start all container services "
                        "within {timeout} seconds.",
                    )

                try:
                    if api_client.health_check()["status"] == "ok":
                        break
                except (ConnectionError, KeyError):
                    pass

                sleep(0.1)

        # HTTP service is up and listening for requests.
        return api_client


    # Tests can then interact with the API client directly.
    def test_frog_blast_the_vent_core(api_client: ApiClient):
        assert api_client.frog_blast_the_vent_core() == {
            "status": "I'm out of ammo!",
        }


Running Integration Tests
-------------------------
Use `pytest`_ to run your tests as normal:

.. code-block:: sh

    pytest

By default, this will look for a ``docker-compose.yml`` file in the current
working directory.  You can specify a different file via the
``--docker-compose`` option:

.. code-block:: sh

    pytest --docker-compose=/path/to/docker-compose.yml

.. tip::
    Alternatively, you can specify this option in your ``pytest.ini`` file:

    .. code-block:: ini

        [pytest]
        addopts = --docker-compose=/path/to/docker-compose.yml

    The option will be ignored for tests that do not use this plugin.

    See `Configuration Options`_ for more information on using configuration
    files to modify pytest behavior.


.. _Configuration Options: https://docs.pytest.org/en/latest/customize.html#adding-default-options
.. _Docker: https://www.docker.com/
.. _Installing and Using Plugins: https://docs.pytest.org/en/latest/plugins.html#requiring-loading-plugins-in-a-test-module-or-conftest-file
.. _pytest: https://docs.pytest.org/
.. _pytest-xdist: https://github.com/pytest-dev/pytest-xdist
