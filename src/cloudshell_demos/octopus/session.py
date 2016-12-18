from cloudshell_demos.octopus.environment_spec import EnvironmentSpec
import requests
import json
from urlparse import urljoin
import urllib
import time

import ssl
import copy

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
        :type environment_spec: cloudshell_demos.octopus.environment_spec.EnvironmentSpec
        :return:
        """
        env = copy.deepcopy(environment_spec)
        api_url = urljoin(self.host, '/api/environments')
        result = requests.post(api_url, params={'ApiKey': self._api_key}, json=env.json)
        self._valid_status_code(result, 'Failed to deploy environment; error: {0}'.format(result.text))
        env.set_id(json.loads(result.content)['Id'])
        return env

    def create_machine(self, machine_spec):
        """
        :type machine_spec: cloudshell_demos.octopus.machine_spec.MachineSpec
        :return:
        """
        self._validate_tentacle_uri(machine_spec.uri)
        api_url = urljoin(self.host, '/api/machines')
        result = requests.post(api_url, params={'ApiKey': self._api_key}, json=machine_spec.json)
        self._valid_status_code(result, 'Failed to create machine; error: {0}'.format(result.text))
        machine_spec.set_id(json.loads(result.content)['Id'])
        return machine_spec

    def find_machine_by_name(self, machine_name):
        """
        :type machine_name: str
        :return:
        """
        api_url = urljoin(self.host, '/api/machines/all')
        result = requests.get(api_url, params={'ApiKey': self._api_key})
        self._valid_status_code(result, 'Failed to find machine {1}; error: {0}'.format(result.text,
                                                                                        machine_name))
        machines = json.loads(result.content)
        for machine in machines:
            if machine['Name'] == machine_name:
                return machine
        raise Exception('Machine named {0} was not found on Octopus Deploy'.format(machine_name))

    def find_environment_by_name(self, environment_name):
        """
        :type machine_name: str
        :rtype: dict
        """
        api_url = urljoin(self.host, '/api/environments/all')
        result = requests.get(api_url, params={'ApiKey': self._api_key})
        self._valid_status_code(result, 'Failed to find environment {1}; error: {0}'.format(result.text,
                                                                                            environment_name))
        environments = json.loads(result.content)
        for environment_dict in environments:
            if environment_dict['Name'] == environment_name:
                return environment_dict
        raise Exception('Environment named {0} was not found on Octopus Deploy'.format(environment_name))

    def add_existing_machine_to_environment(self, machine_id, environment_id, roles=[]):
        api_url = urljoin(self.host, '/api/machines/{0}'.format(machine_id))
        result = requests.get(api_url, params={'ApiKey': self._api_key})
        existing_machine = json.loads(result.text)
        existing_machine['EnvironmentIds'].append(environment_id)
        if roles:
            existing_machine['Roles'].extend(roles)
        result = requests.put(api_url, params={'ApiKey': self._api_key}, json=existing_machine)
        self._valid_status_code(result,
                                'Failed to add existing machine with id {0} to environment {1}.'
                                '\nError: {2}'.format(machine_id, environment_id, result.text))
        return json.loads(result.content)

    def remove_existing_machine_from_environment(self, machine_id, environment_id):
        api_url = urljoin(self.host, '/api/machines/{0}'.format(machine_id))
        result = requests.get(api_url, params={'ApiKey': self._api_key})
        existing_machine = json.loads(result.text)
        if environment_id in existing_machine['EnvironmentIds']:
            existing_machine['EnvironmentIds'].remove(environment_id)
        result = requests.put(api_url, params={'ApiKey': self._api_key}, json=existing_machine)
        self._valid_status_code(result,
                                'Failed to remove existing machine with id {0} to environment {1}.'
                                '\nError: {2}'.format(machine_id, environment_id, result.text))
        return json.loads(result.content)

    def create_release(self, release_spec):
        """
        :type release_spec: cloudshell_demos.octopus.release_spec.ReleaseSpec
        :return:
        """
        api_url = urljoin(self.host, '/api/releases')
        result = requests.post(api_url, params={'ApiKey': self._api_key}, json=release_spec.json)
        self._valid_status_code(result, 'Failed to create release; error: {0}'.format(result.text))
        release_spec.set_id(json.loads(result.content)['Id'])
        return release_spec

    def deploy_release(self, release_spec, environment_spec):
        """
        :param release_spec: cloudshell_demos.octopus.release_spec.ReleaseSpec
        :type environment_spec: cloudshell_demos.octopus.environment_spec.EnvironmentSpec
        :return:
        """
        api_url = urljoin(self.host, '/api/deployments')
        deployment = {
            'EnvironmentId': environment_spec.id,
            'ReleaseId': release_spec.id
        }
        result = requests.post(api_url, params={'ApiKey': self._api_key}, json=deployment)
        self._valid_status_code(result, 'Failed to deploy release; error: {0}'.format(result.text))
        deployment_result = json.loads(result.text)
        return deployment_result

    def wait_for_deployment_to_complete(self, deployment_result, retries=5, sleep_seconds=60):
        deployment_outcome = False
        api_url = urljoin(self.host, 'api/tasks/{0}'.format(deployment_result['TaskId']))
        for retry in range(retries):
            try:
                result = requests.get(api_url, params={'ApiKey': self._api_key})
                self._valid_status_code(result, '')
                deployment_outcome = True
                break
            except:
                time.sleep(sleep_seconds)
        return deployment_outcome

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

    def create_lifecycle(self, lifecyle_name, lifecycle_description, environment_spec):
        """
        :type environment_spec: cloudshell_demos.octopus.machine_spec.EnvironmentSpec
        :return:
        """
        lifecycle = {
            'Name': lifecyle_name,
            'Description': lifecycle_description,
            'Phases': [{
                'Name': 'Cloudshell Sandbox Phase',
                'AutomaticDeploymentTargets': [environment_spec.name]
            }]
        }
        api_url = urljoin(self.host, '/api/lifecycles')
        result = requests.post(api_url, params={'ApiKey': self._api_key}, json=lifecycle)
        self._valid_status_code(result, 'Failed to create lifecycle; error: {0}'.format(result.text))
        lifecycle = json.loads(result.content)
        return lifecycle

    def delete_lifecycle(self, lifecycle_id):
        api_url = urljoin(self.host, 'api/lifecycles/{0}'.format(lifecycle_id))
        result = requests.delete(api_url, params={'ApiKey': self._api_key})
        self._valid_status_code(result, 'Failed to delete lifecycle; error: {0}'.format(result.text))
        return True

    def find_lifecycle_by_name(self, lifecycle_name):
        api_url = urljoin(self.host, '/api/lifecycles/all')
        result = requests.get(api_url, params={'ApiKey': self._api_key})
        self._valid_status_code(result, 'Failed to find machine {1}; error: {0}'.format(result.text,
                                                                                        lifecycle_name))
        lifecycles = json.loads(result.content)
        for lifecycle in lifecycles:
            if lifecycle['Name'] == lifecycle_name:
                return lifecycle
        raise Exception('Lifecycle named {0} was not found on Octopus Deploy'.format(lifecycle_name))

    def lifecycle_exists(self, lifecycle_dict):
        """
        :param lifecycle_dict: a json response from Octopus rest api
        :type lifecycle_dict: dict
        :return:
        """
        if 'Id' in lifecycle_dict:
            api_url = urljoin(self.host, '/api/lifecycles/{0}'.format(lifecycle_dict['Id']))
            result = requests.get(api_url, params={'ApiKey': self._api_key})
            try:
                self._valid_status_code(result, 'Lifeycle not found; error: {0}'.format(result.text))
            except:
                return False
            else:
                return True
        else:
            # Lifecycle object has no id, maybe you haven't deployed it yet?
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

    def machine_exists_on_environment(self, machine_id, environment_id):
        api_url = urljoin(self.host, '/api/machines/{0}'.format(machine_id))
        result = requests.get(api_url, params={'ApiKey': self._api_key})
        self._valid_status_code(result, 'Machine with id {1} not found; error: {0}'.format(result.text, machine_id))
        machine = json.loads(result.text)
        return True if environment_id in machine['EnvironmentIds'] else False

    def release_exists(self, release_spec):
        if hasattr(release_spec, 'id'):
            api_url = urljoin(self.host, '/api/releases/{0}'.format(release_spec.id))
            result = requests.get(api_url, params={'ApiKey': self._api_key}, json=release_spec.json)
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
        self.delete_environment_by_environment_id(environment.id)

    def delete_environment_by_environment_id(self, environment_id):
        api_url = urljoin(self.host, '/api/environments/{0}'.format(environment_id))
        result = requests.delete(api_url, params={'ApiKey': self._api_key})
        self._valid_status_code(result, 'Error during delete environment: {0}'.format(result.text))
        return True

    def delete_machine(self, machine_spec):
        if not self.machine_exists(machine_spec):
            raise Exception('Machine does not exist')
        api_url = urljoin(self.host, '/api/machines/{0}'.format(machine_spec.id))
        result = requests.delete(api_url, params={'ApiKey': self._api_key})

    def delete_release(self, release_spec):
        if not self.release_exists(release_spec):
            raise Exception('Release does not exist')
        api_url = urljoin(self.host, '/api/releases/{0}'.format(release_spec.id))
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
