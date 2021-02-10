import time

import pytest
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


@pytest.fixture(scope="session")
def wait_for_api_impl():
    def wait_for_api(service, container_getter):
        request_session = requests.Session()
        retries = Retry(total=5,
                        backoff_factor=0.1,
                        status_forcelist=[500, 502, 503, 504])
        request_session.mount('http://', HTTPAdapter(max_retries=retries))

        network_info = container_getter.get(service).network_info
        service = network_info[0]
        api_url = "http://%s:%s/" % (service.hostname, service.host_port)
        assert request_session.get(api_url)
        return request_session, api_url
    return wait_for_api
