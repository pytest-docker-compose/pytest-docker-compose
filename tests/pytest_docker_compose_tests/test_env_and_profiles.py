import pytest

pytest_plugins = ["docker_compose"]


@pytest.mark.compose_options
def test_env(module_scoped_container_getter): 
    api_env = module_scoped_container_getter.get("my_api_service").environment
    assert api_env["TEST_ENV_VAR"] == "TEST_ENV_VALUE"
