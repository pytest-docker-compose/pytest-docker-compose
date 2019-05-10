import pytest
import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from pytest_docker_compose import DockerComposePlugin

pytest_plugins = ["docker_compose"]


@pytest.fixture(scope="session")
def session_containers(docker_project):
  containers = DockerComposePlugin._containers_up(docker_project)
  yield containers
  DockerComposePlugin._containers_down(docker_project, containers)


@pytest.fixture(scope="session")
def session_network_info(session_containers):
  return DockerComposePlugin._extract_network_info(session_containers)


@pytest.fixture(scope="session")
def wait_for_api(session_network_info):
    request_session = requests.Session()
    retries = Retry(total=5,
                    backoff_factor=0.1,
                    status_forcelist=[500, 502, 503, 504])
    request_session.mount('http://', HTTPAdapter(max_retries=retries))

    service = session_network_info["docker_compose_directory_my_api_service_1"][0]
    api_url = f"http://{service.hostname}:{service.host_port}/"
    assert request_session.get(api_url)
    return request_session, api_url


@pytest.fixture
def do_an_insert(wait_for_api):
    request_session, api_url = wait_for_api
    item_url = 'items/1'
    data_string = 'some_data'
    request_session.put(f'{api_url}{item_url}?data_string={data_string}')
    return item_url, data_string


def test_read_an_item(wait_for_api, do_an_insert):
    request_session, api_url = wait_for_api
    item_url, data_string = do_an_insert
    item = request_session.get(f'{api_url}{item_url}').json()
    assert item['data'] == data_string


def test_read_and_write(wait_for_api):
    request_session, api_url = wait_for_api
    data_string = 'some_other_data'
    request_session.put(f'{api_url}items/2?data_string={data_string}')
    item = request_session.get(f'{api_url}items/2').json()
    assert item['data'] == data_string


def test_read_all(wait_for_api):
    request_session, api_url = wait_for_api
    assert len(request_session.get(f'{api_url}items/all').json()) == 2


if __name__ == '__main__':
    pytest.main(['--docker-compose', './docker_compose_directory', '--docker-compose-no-build'])
