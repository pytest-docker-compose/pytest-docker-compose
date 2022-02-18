pytest-docker-compose
=====================
.. image:: https://circleci.com/gh/pytest-docker-compose/pytest-docker-compose/tree/master.svg?style=svg
    :target: https://circleci.com/gh/pytest-docker-compose/pytest-docker-compose/tree/master

This package contains a `pytest`_ plugin for integrating Docker Compose into your automated integration tests.

Given a path to a ``docker-compose.yml`` file, it will automatically build the project at the start of the test run, bring the containers up before each test starts, and tear them down after each test ends.


Dependencies
------------
Make sure you have `Docker`_ installed.

This plugin is automatically tested against the following software:

- Python 3.5 and 3.6.
- pytest 3, 4 and 5.

.. note:: This plugin is **not** compatible with Python 2.

Locally I tested it successfully against Python 3.7 as well but 3.7 proved hard to integrate into circleCI so it's not officially supported.

Installation
------------
Install the plugin using pip::

    > pip install pytest-docker-compose


Usage
-----
For performance reasons, the plugin is not enabled by default, so you must activate it manually in the tests that use it:

.. code-block:: python

    pytest_plugins = ["docker_compose"]

See `Installing and Using Plugins`_ for more information.

To interact with Docker containers in your tests, use the following fixtures, these fixtures tell docker-compose to start all the services and then they can fetch the associated containers for use in a test:

``function_scoped_container_getter``
    An object that fetches containers of the Docker ``compose.container.Container`` objects running during the test. The containers are fetched using ``function_scoped_container_getter.get('service_name')`` These containers each have an extra attribute called ``network_info`` added to them. This attribute has a list of ``pytest_docker_compose.NetworkInfo`` objects.

    This information can be used to configure API clients and other objects that will connect to services exposed by the Docker containers in your tests.

    ``NetworkInfo`` is a container with the following fields:

    - ``container_port``: The port (and usually also protocol name) exposed
      internally to the container.  You can use this value to find the correct
      port for your test, when the container exposes multiple ports.

    - ``hostname``: The hostname (usually "localhost") to use when connecting to
      the service from the host.

    - ``host_port``: The port number to use when connecting to the service from
      the host.

``docker_project``
    The ``compose.project.Project`` object that the containers are built from.
    This fixture is generally only used internally by the plugin.

To use the following fixtures please read `Use wider scoped fixtures`_.

``class_scoped_container_getter``
    Similar to ``function_scoped_container_getter`` just with a wider scope.

``module_scoped_container_getter``
    Similar to ``function_scoped_container_getter`` just with a wider scope.

``session_scoped_container_getter``
    Similar to ``function_scoped_container_getter`` just with a wider scope.

Waiting for Services to Come Online
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The fixtures called ``'scope'_scoped_container_getter`` will wait until every container is up before handing control over to the test.

However, just because a container is up does not mean that the services running on it are ready to accept incoming requests yet!

If your tests need to wait for a particular condition (for example, to wait for an HTTP health check endpoint to send back a 200 response), make sure that your fixtures account for this.

Here's an example of a fixture called ``wait_for_api`` that waits for an HTTP service to come online before a test called ``test_read_and_write`` can run.

.. code-block:: python

    import pytest
    import requests
    from urllib.parse import urljoin
    from urllib3.util.retry import Retry
    from requests.adapters import HTTPAdapter

    pytest_plugins = ["docker_compose"]

    # Invoking this fixture: 'function_scoped_container_getter' starts all services
    @pytest.fixture(scope="function")
    def wait_for_api(function_scoped_container_getter):
        """Wait for the api from my_api_service to become responsive"""
        request_session = requests.Session()
        retries = Retry(total=5,
                        backoff_factor=0.1,
                        status_forcelist=[500, 502, 503, 504])
        request_session.mount('http://', HTTPAdapter(max_retries=retries))

        service = function_scoped_container_getter.get("my_api_service").network_info[0]
        api_url = "http://%s:%s/" % (service.hostname, service.host_port)
        assert request_session.get(api_url)
        return request_session, api_url


    def test_read_and_write(wait_for_api):
        """The Api is now verified good to go and tests can interact with it"""
        request_session, api_url = wait_for_api
        data_string = 'some_data'
        request_session.put('%sitems/2?data_string=%s' % (api_url, data_string))
        item = request_session.get(urljoin(api_url, 'items/2')).json()
        assert item['data'] == data_string
        request_session.delete(urljoin(api_url, 'items/2'))

Use wider scoped fixtures
~~~~~~~~~~~~~~~~~~~~~~~~~
The ``function_scoped_container_getter`` fixture uses "function" scope, meaning that all of the containers are torn down after each individual test.

This is done so that every test gets to run in a "clean" environment. However, this can potentially make a test suite take a very long time to complete.

There are two options to make containers persist beyond a single test. The best way is to use the fixtures that are explicitly scoped to different scopes. There are three additional fixtures for this purpose: ``class_scoped_container_getter``, ``module_scoped_container_getter`` and ``session_scoped_container_getter``. Notice that you need to be careful when using these! There are two main caveats to keep in mind:

1. Manage your scope correctly, using 'module' scope and 'function' scope in one single file will throw an error! This is because the module scoped fixture will spin up the containers and then the function scoped fixture will try to spin up the containers again. Docker compose does not allow you to spin up containers twice.
2. Clean up your environment after each test. Because the containers are not restarted their environments can carry the information from previous tests. Therefore you need to be very careful when designing your tests such that they leave the containers in the same state that it started in or you might run into difficult to understand behaviour.

A second method to make containers persist beyond a single test is to supply the --use-running-containers flag to pytest like so:

.. code-block:: bash

    pytest --use-running-containers

With this flag, pytest-docker-compose checks that all containers are running
during the project creation. If they are not running a warning is given and
they are spun up anyways. They are then used for all the tests and NOT TORE
DOWN afterwards.

This mode is best used in combination with the '--docker-compose-no-build' flag since the newly build containers won't be used anyways. like so:

.. code-block:: bash

    pytest --docker-compose-no-build --use-running-containers

It is off course possible to add these options to ``pytest.ini``.

Notice that for this mode the scoping of the fixtures becomes less important since the containers are fully persistent throughout all tests. I only recommend using this if your network takes excessively long to spin up/tear down. It should really be a last resort and you should probably look into speeding up your network instead of using this.



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

Docker compose allows for specifying multiple compose files as described in the `docs here <https://docs.docker.com/compose/extends/>`_. To specify more than one compose file, separate them with a ``,``:

.. code-block:: sh

    pytest --docker-compose=/path/to/docker-compose.yml,/another/docker-compose.yml,/third/docker-compose.yml

.. tip::
    Alternatively, you can specify this option in your ``pytest.ini`` file:

    .. code-block:: ini

        [pytest]
        addopts = --docker-compose=/path/to/docker-compose.yml

    The option will be ignored for tests that do not use this plugin.

    See `Configuration Options`_ for more information on using configuration
    files to modify pytest behavior.

Remove volumes after tests
--------------------------
There is another configuration option that will delete the volumes of containers after running.

.. code-block:: sh

    pytest --docker-compose-remove-volumes

This option will be ignored if the plugin is not used. Again, this option can also be added to the pytest.ini file.

For more examples on how to use this plugin look at the testing suite of this plugin itself! It will give you some examples for configuring pytest.ini and how to use the different fixtures to run docker containers.

.. _Configuration Options: https://docs.pytest.org/en/latest/customize.html#adding-default-options
.. _Docker: https://www.docker.com/
.. _Installing and Using Plugins: https://docs.pytest.org/en/latest/plugins.html#requiring-loading-plugins-in-a-test-module-or-conftest-file
.. _pytest: https://docs.pytest.org/
.. _pytest-xdist: https://github.com/pytest-dev/pytest-xdist
