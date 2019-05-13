import pytest
import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from pytest_docker_compose import generate_scoped_network_info_fixture

pytest_plugins = ["docker_compose"]

docker_network_info_function = generate_scoped_network_info_fixture('function')


@pytest.fixture(scope="function")
def wait_for_api(docker_network_info_function):
    request_session = requests.Session()
    retries = Retry(total=5,
                    backoff_factor=0.1,
                    status_forcelist=[500, 502, 503, 504])
    request_session.mount('http://', HTTPAdapter(max_retries=retries))

    service = docker_network_info_function["docker_compose_directory_my_api_service_1"][0]
    api_url = f"http://{service.hostname}:{service.host_port}/"
    assert request_session.get(api_url)
    return request_session, api_url


def test_read_and_write(wait_for_api):
    request_session, api_url = wait_for_api
    data_string = 'some_other_data'
    request_session.put(f'{api_url}items/2?data_string={data_string}')
    item = request_session.get(f'{api_url}items/2').json()
    assert item['data'] == data_string


def test_read_all(wait_for_api):
    request_session, api_url = wait_for_api
    assert len(request_session.get(f'{api_url}items/all').json()) == 0


if __name__ == '__main__':
    pytest.main(['--docker-compose', './docker_compose_directory', '--docker-compose-no-build'])
