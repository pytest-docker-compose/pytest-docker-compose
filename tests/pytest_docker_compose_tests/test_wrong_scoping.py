import pytest
pytest_plugins = ["docker_compose"]


@pytest.mark.should_fail
def test_read_all_module(module_scoped_containers):
    assert module_scoped_containers["my_network_my_api_service_1"].network_info[0]


@pytest.mark.should_fail
def test_read_all_function(function_scoped_containers):
    assert function_scoped_containers["my_network_my_api_service_1"].network_info[0]
