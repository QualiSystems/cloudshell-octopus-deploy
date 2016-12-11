from cloudshell.octopus.environment import Environment
import requests
import json
from urlparse import urljoin


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

    def deploy_environment(self, environment):
        """
        :type environment: cloudshell.octopus.environment.Environment
        :return:
        """
        api_url = urljoin(self.host, '/api/environments')
        result = requests.post(api_url, params={'ApiKey': self._api_key}, json=environment.json)
        self._valid_status_code(result, 'Failed to deploy environment; error: {0}'.format(result.text))
        environment.set_id(json.loads(result.content)['Id'])

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
            # Environment has no id, maybe you haven't deployed it yet?
            return False

    def delete_environment(self, environment):
        if not self.environment_exists(environment):
            raise Exception('Environment does not exist')
        api_url = urljoin(self.host, '/api/environments/{0}'.format(environment.id))
        result = requests.delete(api_url, params={'ApiKey': self._api_key}, json=environment.json)

    def _valid_status_code(self, result, error_msg):
        # Consider any status other than 2xx an error
        if not result.status_code // 100 == 2:
            raise Exception(error_msg)