import pytest
import requests
from urllib.parse import urljoin
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

pytest_plugins = ["docker_compose"]


@pytest.mark.should_fail
def test_read_all_module(module_scoped_containers):
    request_session = requests.Session()
    retries = Retry(total=5,
                    backoff_factor=0.1,
                    status_forcelist=[500, 502, 503, 504])
    request_session.mount('http://', HTTPAdapter(max_retries=retries))

    service = module_scoped_containers["my_network_my_api_service_1"].network_info[0]
    api_url = "http://%s:%s/" % (service.hostname, service.host_port)
    assert request_session.get(api_url)
    assert len(request_session.get(urljoin(api_url, 'items/all')).json()) == 0


@pytest.mark.should_fail
def test_read_all_function(docker_network_info):
    request_session = requests.Session()
    retries = Retry(total=5,
                    backoff_factor=0.1,
                    status_forcelist=[500, 502, 503, 504])
    request_session.mount('http://', HTTPAdapter(max_retries=retries))

    service = docker_network_info["my_network_my_api_service_1"][0]
    api_url = "http://%s:%s/" % (service.hostname, service.host_port)
    assert len(request_session.get(urljoin(api_url, 'items/all')).json()) == 0
