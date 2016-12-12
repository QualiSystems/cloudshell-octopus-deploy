from cloudshell.octopus.environment_spec import EnvironmentSpec
import requests
import json
from urlparse import urljoin
import urllib

import ssl
VALIDATE_TENTACLE_CONTEXT = ssl._create_unverified_context()


class OctopusServer:
    def __init__(self, host, api_key):
        """
        :param host:
        :param api_key:
        :return:
        """
        self._host = host
        self._api_key = api_key
        self._validate_host()

    def _validate_host(self):
        result = requests.get(self.host)
        self._valid_status_code(result, 'Could not reach {0}\nPlease check if server is accessible'
                                .format(self._host))


    @property
    def host(self):
        return self._host

    @property
    def api_key(self):
        return self._api_key

    def create_environment(self, environment_spec):
        """
        :type environment_spec: cloudshell.octopus.environment_spec.EnvironmentSpec
        :return:
        """
        api_url = urljoin(self.host, '/api/environments')
        result = requests.post(api_url, params={'ApiKey': self._api_key}, json=environment_spec.json)
        self._valid_status_code(result, 'Failed to deploy environment_spec; error: {0}'.format(result.text))
        environment_spec.set_id(json.loads(result.content)['Id'])
        return environment_spec

    def create_machine(self, machine_spec):
        """
        :type environment_spec: cloudshell.octopus.environment_spec.EnvironmentSpec
        :return:
        """
        self._validate_tentacle_uri(machine_spec.uri)
        api_url = urljoin(self.host, '/api/machines')
        result = requests.post(api_url, params={'ApiKey': self._api_key}, json=machine_spec.json)
        self._valid_status_code(result, 'Failed to create machine_spec; error: {0}'.format(result.text))
        machine_spec.set_id(json.loads(result.content)['Id'])
        return machine_spec

    def environment_exists(self, environment):
        if hasattr(environment, 'id'):
            api_url = urljoin(self.host, '/api/environments/{0}'.format(environment.id))
            result = requests.get(api_url, params={'ApiKey': self._api_key}, json=environment.json)
            try:
                self._valid_status_code(result, 'Environment not found; error: {0}'.format(result.text))
            except:
                return False
            else:
                return True
        else:
            # EnvironmentSpec has no id, maybe you haven't deployed it yet?
            return False

    def machine_exists(self, machine_spec):
        if hasattr(machine_spec, 'id'):
            api_url = urljoin(self.host, '/api/machines/{0}'.format(machine_spec.id))
            result = requests.get(api_url, params={'ApiKey': self._api_key}, json=machine_spec.json)
            try:
                self._valid_status_code(result, 'Machine not found; error: {0}'.format(result.text))
            except:
                return False
            else:
                return True
        else:
            # EnvironmentSpec has no id, maybe you haven't deployed it yet?
            return False

    def delete_environment(self, environment):
        if not self.environment_exists(environment):
            raise Exception('Environment does not exist')
        api_url = urljoin(self.host, '/api/environments/{0}'.format(environment.id))
        result = requests.delete(api_url, params={'ApiKey': self._api_key})

    def delete_machine(self, machine_spec):
        if not self.machine_exists(machine_spec):
            raise Exception('Machine does not exist')
        api_url = urljoin(self.host, '/api/machines/{0}'.format(machine_spec.id))
        result = requests.delete(api_url, params={'ApiKey': self._api_key})

    def _valid_status_code(self, result, error_msg):
        # Consider any status other than 2xx an error
        if not result.status_code // 100 == 2:
            raise Exception(error_msg)

    def _validate_tentacle_uri(self, uri):
        reply = urllib.urlopen(uri, context=VALIDATE_TENTACLE_CONTEXT)
        class Result(object):
            pass
        result = Result()
        result.status_code = reply.getcode()
        # noinspection PyTypeChecker
        self._valid_status_code(result=result,
                                error_msg='Unable to access Octopus Tentacle at {0}'
                                .format(uri))
