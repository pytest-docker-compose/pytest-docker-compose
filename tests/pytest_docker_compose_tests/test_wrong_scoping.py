import pytest
pytest_plugins = ["docker_compose"]


@pytest.mark.should_fail
def test_read_all_module(module_scoped_container_getter):
    assert module_scoped_container_getter.get("my_api_service").network_info[0]


@pytest.mark.should_fail
def test_read_all_function(function_scoped_container_getter):
    assert function_scoped_container_getter.get("my_api_service").network_info[0]
