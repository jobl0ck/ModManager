import os
from instances.instance import Instance

def test_instance_serializer():
    testdict = {
            "name": "Stoneblock 3",
            "mc_version": {
                "mc": "1.18.2",
                "loader": "forge",
                "loader_version": "40.2.10"
            },
            "mp_version": {
                "name":"1.8.0",
                "mid": "100",
                "vid": "id"
            },
            "platform": "ftb",
            "directory": "~/.modmanager/instances/stoneblock-3"
        }
    instance = Instance("testing", testdict)

    for key, val in testdict.items():
        if(key == "directory"):
            assert os.path.expanduser(val) == instance.to_dict()[key]
            continue


        assert instance.to_dict()[key] == val