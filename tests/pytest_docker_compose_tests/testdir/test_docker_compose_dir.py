import requests
from urllib.parse import urljoin
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

import pytest

pytest_plugins = ["docker_compose"]


@pytest.fixture(scope="function")
def wait_for_api(wait_for_api_impl, function_scoped_container_getter):
    """Wait for the api from my_api_service to become responsive"""
    return wait_for_api_impl("my_api_service", function_scoped_container_getter)


def test_read_and_write(wait_for_api):
    request_session, api_url = wait_for_api
    data_string = 'some_data'
    request_session.put('%sitems/2?data_string=%s' % (api_url, data_string))
    item = request_session.get(urljoin(api_url, 'items/2')).json()
    assert item['data'] == data_string
    request_session.delete(urljoin(api_url, 'items/2'))


def test_read_all(wait_for_api):
    request_session, api_url = wait_for_api
    assert len(request_session.get(urljoin(api_url, 'items/all')).json()) == 0


if __name__ == '__main__':
    pytest.main([])
