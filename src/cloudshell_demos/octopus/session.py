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

    def create_channel(self, name, project_id, lifecycle_id):
        channel = {
            'Name': name,
            'ProjectId': project_id,
            'LifecycleId': lifecycle_id
        }
        api_url = urljoin(self.host, '/api/channels')
        result = requests.post(api_url, params={'ApiKey': self._api_key}, json=channel)
        self._valid_status_code(result, 'Failed to create channel; error: {0}'.format(result.text))
        return json.loads(result.content)

    def delete_channel(self, channel_id):
        self._delete_channel_releases(channel_id)
        api_url = urljoin(self.host, '/api/channels/{0}'.format(channel_id))
        result = requests.delete(api_url, params={'ApiKey': self._api_key})
        self._valid_status_code(result, 'Failed to delete channel; error: {0}'.format(result.text))
        return json.loads(result.content)

    def _delete_channel_releases(self, channel_id):
        api_url = urljoin(self.host, '/api/channels/{0}/releases'.format(channel_id))
        result = requests.get(api_url, params={'ApiKey': self._api_key})
        self._valid_status_code(result, 'Failed to get channel releases; error: {0}'.format(result.text))
        releases_dict = json.loads(result.content)
        if 'Items' in releases_dict:
            for release in releases_dict['Items']:
                self.delete_release_by_release_id(release['Id'])

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

    def find_channel_by_name_on_project(self, project_id, channel_name):
        api_url = urljoin(self.host, '/api/projects/{0}/channels'.format(project_id))
        result = requests.get(api_url, params={'ApiKey': self._api_key})
        project_channels = json.loads(result.text)['Items']
        for channel in project_channels:
            if channel['Name'] == channel_name:
                return channel
        raise Exception('Channel named {0} was not found on Octopus Deploy'.format(channel_name))

    def channel_exists(self, project_id, channel_name):
        api_url = urljoin(self.host, '/api/projects/{0}/channels'.format(project_id))
        result = requests.get(api_url, params={'ApiKey': self._api_key})
        project_channels = json.loads(result.text)['Items']
        for channel in project_channels:
            if channel['Name'] == channel_name:
                return True
        return False

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

    def deploy_release(self, release_spec, environment_id):
        """
        :param release_spec: cloudshell_demos.octopus.release_spec.ReleaseSpec
        :type environment_id: str
        :return:
        """
        api_url = urljoin(self.host, '/api/deployments')
        deployment = {
            'EnvironmentId': environment_id,
            'ReleaseId': release_spec.id
        }
        result = requests.post(api_url, params={'ApiKey': self._api_key}, json=deployment)
        self._valid_status_code(result, 'Failed to deploy release; error: {0}'.format(result.text))
        deployment_result = json.loads(result.text)

        self._wait_till_deployment_completes(deployment_result)

        return deployment_result

    def _wait_till_deployment_completes(self, deployment_result, retries=10, wait_duration=60):
        deployments = self._get_release_deployments(deployment_result)

        for deployment in deployments:
            deployment_completed = False
            task_url = urljoin(self.host, deployment['Links']['Task'])
            for retry in xrange(retries):
                result = requests.get(task_url, params={'ApiKey': self._api_key})
                if json.loads(result.content)['IsCompleted']:
                    deployment_completed = True
                    break
                else:
                    time.sleep(wait_duration)
            if not deployment_completed:
                raise Exception('Timeout after {0}'.format(str(retries*wait_duration)))

    def _get_release_deployments(self, deployment_result):
        deployments_url = urljoin(self.host, deployment_result['Links']['Release'] + '/deployments')
        result = requests.get(deployments_url, params={'ApiKey': self._api_key})
        self._valid_status_code(result, 'Failed to get release deployments; error: {0}'.format(result.text))
        deployments = json.loads(result.content)['Items']
        return deployments

    def wait_for_deployment_to_complete(self, deployment_result, retries=20, sleep_seconds=30):
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
                'AutomaticDeploymentTargets': [environment_spec.id]
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

    def get_entity(self, relative_path):
        api_url = urljoin(self.host, relative_path)
        result = requests.get(api_url, params={'ApiKey': self._api_key})
        self._valid_status_code(result, 'Couldn''t get entity. error: {0}'.format(result.text))
        return json.loads(result.content)

    def find_lifecycle_by_name(self, lifecycle_name):
        api_url = urljoin(self.host, '/api/lifecycles/all')
        result = requests.get(api_url, params={'ApiKey': self._api_key})
        self._valid_status_code(result, 'Failed to find lifecycle {1}; error: {0}'.format(result.text, lifecycle_name))
        lifecycles = json.loads(result.content)
        for lifecycle in lifecycles:
            if lifecycle['Name'] == lifecycle_name:
                return lifecycle
        raise Exception('Lifecycle named {0} was not found on Octopus Deploy'.format(lifecycle_name))

    def find_project_by_name(self, project_name):
        api_url = urljoin(self.host, '/api/projects/all')
        result = requests.get(api_url, params={'ApiKey': self._api_key})
        self._valid_status_code(result, 'Failed to find project {1}; error: {0}'.format(result.text, project_name))
        projects = json.loads(result.content)
        for project in projects:
            if project['Name'] == project_name:
                return project
        raise Exception('Project named {0} was not found on Octopus Deploy'.format(project_name))

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

    def delete_release_by_release_id(self, release_id):
        api_url = urljoin(self.host, '/api/releases/{0}'.format(release_id))
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
