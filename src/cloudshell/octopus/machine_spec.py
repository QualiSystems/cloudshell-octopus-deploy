import json


class MachineSpec:
    def __init__(self, name, roles, thumbprint, uri, environment_ids, tenant_ids=None):
        """
        :type name: str
        :type roles: list[str]
        :type thumbprint: str
        :type uri: str
        :type environment_ids: list[str]
        :type tenant_ids: list[str]
        :return:
        """
        self._name = name
        self._roles = roles
        self._tenant_ids = tenant_ids or []
        self._thumbprint = thumbprint
        self._uri = uri
        self._environment_ids = environment_ids

    @property
    def name(self):
        return self._name

    @property
    def roles(self):
        return self._roles

    @property
    def tenant_ids(self):
        return self._tenant_ids

    @property
    def thumbprint(self):
        return self._thumbprint

    @property
    def uri(self):
        return self._uri

    @property
    def environment_ids(self):
        return self._environment_ids

    @property
    def json(self):
        machine_dict = dict()
        machine_dict['Name'] = self.name
        machine_dict['Roles'] = self.roles
        machine_dict['TenantIds'] = self.tenant_ids
        machine_dict['EnvironmentIds'] = self.environment_ids
        machine_dict['Endpoint'] = {
            'CommunicationStyle': 'TentaclePassive',
            'Uri': self.uri,
            'Thumbprint': self.thumbprint
        }
        return machine_dict

    def set_id(self, id):
        self.id = id
