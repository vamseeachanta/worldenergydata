from worldenergydata.bsee.data.loaders.lease.local_files import DataFromLocalFiles

lease_data_from_local_files = DataFromLocalFiles()

class LeaseRouter:

    def __init__(self):
            pass

    def router(self, cfg):

        if 'groups' in cfg['data'] and cfg['data']['groups'][0]['bottom_lease'] is not None:
            cfg = self.get_lease_data_groups(cfg)

        return cfg

    def get_lease_data_groups(self, cfg):

        cfg, lease_data_groups = lease_data_from_local_files.router(cfg)

        return cfg
