from operator import contains
import requests
from urllib.parse import urljoin
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

import pytest

pytest_plugins = ["docker_compose"]


@pytest.fixture(scope="function")
def wait_for_api(function_scoped_container_getter):
    """Wait for the api from my_api_service to become responsive"""
    request_session = requests.Session()
    retries = Retry(total=5,
                    backoff_factor=0.1,
                    status_forcelist=[500, 502, 503, 504])
    request_session.mount('http://', HTTPAdapter(max_retries=retries))

    container = function_scoped_container_getter.get("my_api_service")
    assert hasattr(container, "network_info")
    assert container.network_info

    network_info = container.network_info[0]
    api_url = "http://%s:%s/" % (network_info.hostname, network_info.host_port)
    assert request_session.get(api_url)
    return request_session, api_url


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
    pytest.main(['--docker-compose', './my_network', '--docker-compose-no-build'])
