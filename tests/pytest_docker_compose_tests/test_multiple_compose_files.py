import time
from urllib.parse import urljoin

import pytest

pytest_plugins = ["docker_compose"]


@pytest.fixture(scope="module")
def wait_for_api(wait_for_api_impl, module_scoped_container_getter):
    """Wait for the api from my_api_service to become responsive"""
    request_session, api_url = wait_for_api_impl("my_api_service", module_scoped_container_getter)

    start = time.time()
    while 'Exit' not in module_scoped_container_getter \
            .get("my_short_lived_service", wait_running=False) \
            .human_readable_state:
        if time.time() - start >= 5:
            raise RuntimeError(
                'my_short_lived_service should spin up, echo "Echoing" and '
                'then shut down, since it still running something went wrong'
            )
        time.sleep(.5)

    start = time.time()
    while 'Exit' not in module_scoped_container_getter \
            .get("other_short_lived_service", wait_running=False) \
            .human_readable_state:
        if time.time() - start >= 5:
            raise RuntimeError(
                'other_short_lived_service should spin up, echo "Echoing" and '
                'then shut down, since it still running something went wrong'
            )
        time.sleep(.5)

    return request_session, api_url


@pytest.mark.multiple_compose_files
def test_read_all(wait_for_api):
    request_session, api_url = wait_for_api
    assert len(request_session.get(urljoin(api_url, 'items/all')).json()) == 0


if __name__ == '__main__':
    pytest.main(['-m', 'multiple_compose_files', '--docker-compose', '.', '--docker-compose', './extra-service.yml'])
