pytest_plugins = ["docker_compose"]


def test_can_connect_to_autoassigned_ports(module_scoped_containers):
    ctr = module_scoped_containers['my_network_db_without_port_1']
    assert ctr.network_info[0]
    assert ctr.network_info[0].host_port != ''
    assert ctr.network_info[0].hostname != ''
