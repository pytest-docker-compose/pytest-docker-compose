import pytest
import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

from pytest_docker_compose import generate_scoped_containers_fixture

pytest_plugins = ["docker_compose"]

module_scoped_containers = generate_scoped_containers_fixture('module')


@pytest.fixture(scope="module")
def wait_for_api(module_scoped_containers):
    """Wait for the api from my_api_service to become responsive"""
    request_session = requests.Session()
    retries = Retry(total=5,
                    backoff_factor=0.1,
                    status_forcelist=[500, 502, 503, 504])
    request_session.mount('http://', HTTPAdapter(max_retries=retries))

    service = module_scoped_containers["my_network_my_api_service_1"].network_info[0]
    api_url = "http://%s:%s/" % (service.hostname, service.host_port)
    assert request_session.get(api_url)
    return request_session, api_url


@pytest.fixture
def do_an_insert(wait_for_api):
    """Insert data to the database in the container my_db"""
    request_session, api_url = wait_for_api
    item_url = 'items/1'
    data_string = 'some_data'
    request_session.put('%s%s?data_string=%s' % (api_url, item_url, data_string))
    return item_url, data_string


def test_read_an_item(wait_for_api, do_an_insert):
    request_session, api_url = wait_for_api
    item_url, data_string = do_an_insert
    item = request_session.get(api_url + item_url).json()
    assert item['data'] == data_string


def test_read_and_write(wait_for_api):
    request_session, api_url = wait_for_api
    data_string = 'some_other_data'
    request_session.put('%sitems/2?data_string=%s' % (api_url, data_string))
    item = request_session.get('%sitems/2' % api_url).json()
    assert item['data'] == data_string


def test_read_all(wait_for_api):
    request_session, api_url = wait_for_api
    assert len(request_session.get('%sitems/all' % api_url).json()) == 2


if __name__ == '__main__':
    pytest.main(['--docker-compose', './my_network', '--docker-compose-no-build'])
