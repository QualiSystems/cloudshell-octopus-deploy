from cloudshell.octopus.environment_spec import EnvironmentSpec
import requests
import json
from urlparse import urljoin
import urllib
import time

import ssl
import copy

from cloudshell.octopus.machine_spec import MachineSpec

VALIDATE_TENTACLE_CONTEXT = ssl._create_unverified_context()


class OctopusServer:
    def __init__(self, host, api_key):
        """
        :param host:
        :param api_key:
        :return:
        """
        self._host = host
        self._validate_host()
        self.rest_params = {'ApiKey': api_key}

    def _validate_host(self):
        result = requests.get(self.host)
        self._valid_status_code(result, 'Could not reach {0}\nPlease check if server is accessible'
                                .format(self._host))

    @property
    def host(self):
        return self._host

    def create_environment(self, environment_spec):
        """
        :type environment_spec: cloudshell.octopus.environment_spec.EnvironmentSpec
        :return:
        """
        env = copy.deepcopy(environment_spec)
        api_url = urljoin(self.host, '/api/environments')
        result = requests.post(api_url, params=self.rest_params, json=env.json)
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
        result = requests.post(api_url, params=self.rest_params, json=channel)
        self._valid_status_code(result, 'Failed to create channel; error: {0}'.format(result.text))
        return json.loads(result.content)

    def create_machine(self, machine_spec):
        """
        :type machine_spec: cloudshell.octopus.machine_spec.MachineSpec
        :return:
        """
        self._validate_tentacle_uri(machine_spec.uri)
        api_url = urljoin(self.host, '/api/machines')
        result = requests.post(api_url, params=self.rest_params, json=machine_spec.json)
        self._valid_status_code(result, 'Failed to create machine; error: {0}'.format(result.text))
        machine_spec.set_id(json.loads(result.content)['Id'])
        return machine_spec


    def create_release(self, release_spec):
        """
        :type release_spec: cloudshell.octopus.release_spec.ReleaseSpec
        :return:
        """
        api_url = urljoin(self.host, '/api/releases')
        result = requests.post(api_url, params=self.rest_params, json=release_spec.json)
        self._valid_status_code(result, 'Failed to create release; error: {0}'.format(result.text))
        release_spec.set_id(json.loads(result.content)['Id'])
        return release_spec

    def create_lifecycle(self, lifecyle_name, lifecycle_description, environment_id):
        """
        :type environment_id: str
        :return:
        """
        lifecycle = {
            'Name': lifecyle_name,
            'Description': lifecycle_description,
            'Phases': [{
                'Name': 'Cloudshell Sandbox Phase',
                'AutomaticDeploymentTargets': [environment_id]
            }]
        }
        api_url = urljoin(self.host, '/api/lifecycles')
        result = requests.post(api_url, params=self.rest_params, json=lifecycle)
        self._valid_status_code(result, 'Failed to create lifecycle; error: {0}'.format(result.text))
        lifecycle = json.loads(result.content)
        return lifecycle

    def add_environment_to_lifecycle_on_phase(self, environment_id, lifecycle_id, phase_name):
        lifecycle = self.get_lifecycle_by_id(lifecycle_id)
        lifecycle = self._add_env_to_optional_targets_of_lifecycle(environment_id, lifecycle, phase_name)
        api_url = urljoin(self.host, '/api/lifecycles/{0}'.format(lifecycle_id))
        result = requests.put(api_url, params=self.rest_params, json=lifecycle)
        self._valid_status_code(result, 'Failed to create lifecycle; error: {0}'.format(result.text))
        lifecycle = json.loads(result.content)
        return lifecycle

    def remove_environment_from_lifecycle_on_phase(self, environment_id, lifecycle_id, phase_name):
        lifecycle = self.get_lifecycle_by_id(lifecycle_id)
        lifecycle = self._remove_env_from_optional_targets_of_lifecycle(environment_id, lifecycle, phase_name)
        api_url = urljoin(self.host, '/api/lifecycles/{0}'.format(lifecycle_id))
        result = requests.put(api_url, params=self.rest_params, json=lifecycle)
        self._valid_status_code(result, 'Failed to create lifecycle; error: {0}'.format(result.text))
        lifecycle = json.loads(result.content)
        return lifecycle

    def _add_env_to_optional_targets_of_lifecycle(self, environment_id, lifecycle, phase_name):
        for phase in lifecycle['Phases']:
            if phase['Name'] == phase_name:
                phase['OptionalDeploymentTargets'].append(environment_id)
                break
        else:
            raise Exception('Could not add environment {0} to lifecycle {1}'
                            ' because did not find phase {2}'.format(environment_id, lifecycle['Id'], phase_name))
        return lifecycle

    def _remove_env_from_optional_targets_of_lifecycle(self, environment_id, lifecycle, phase_name):
        for phase in lifecycle['Phases']:
            if phase['Name'] == phase_name:
                try:
                    phase['OptionalDeploymentTargets'].remove(environment_id)
                except:
                    raise Exception('Failed to remove remove environment {0} from lifecycle {1}'.format(environment_id, lifecycle['Id']))
                break
        else:
            raise Exception('Could not remove environment {0} from lifecycle {1}'
                            ' because did not find phase {2}'.format(environment_id, lifecycle['Id'], phase_name))
        return lifecycle

    def get_lifecycle_by_id(self, lifecycle_id):
        api_url = urljoin(self.host, '/api/lifecycles/{0}'.format(lifecycle_id))
        result = requests.get(api_url, params=self.rest_params)
        self._valid_status_code(result, 'Failed to get lifecycle with id {0}'.format(lifecycle_id))
        lifecycle = json.loads(result.content)
        return lifecycle

    def get_release_by_id(self, project_id, release_id):
        api_url = urljoin(self.host, '/api/releases/{0}'.format(release_id))
        result = requests.get(api_url, params=self.rest_params)
        self._valid_status_code(result,
                                'Failed to find release {0} on project {1}\n Error: {2}'.format(release_id,
                                                                                                project_id,
                                                                                                result.text))
        release = json.loads(result.content)
        return release

    def get_latest_channel_release(self, channel_id):
        api_url = urljoin(self.host, '/api/channels/{0}/releases'.format(channel_id))
        result = requests.get(api_url, params=self.rest_params)
        self._valid_status_code(result, 'Failed to get channel releases; error: {0}'.format(result.text))
        releases = json.loads(result.content)
        if not releases:
            raise Exception('No releases found on this channel')
        # releases are always ordered from most recent to oldest
        # https://github.com/OctopusDeploy/OctopusDeploy-Api/wiki/Releases
        return releases['Items'][0]

    def get_release_by_version_name(self, project_id, version_name):
        api_url = urljoin(self.host, '/api/projects/{0}/releases/{1}'.format(project_id, version_name))
        result = requests.get(api_url, params=self.rest_params)
        self._valid_status_code(result, 'Failed to get release named {1}; error: {0}'.format(result.text, version_name))
        release = json.loads(result.content)
        return release

    def deploy_release(self, release_id, environment_id):
        """
        :param release_id: str
        :type environment_id: str
        :return:
        """
        api_url = urljoin(self.host, '/api/deployments')
        deployment = {
            'EnvironmentId': environment_id,
            'ReleaseId': release_id
        }
        result = requests.post(api_url, params=self.rest_params, json=deployment)
        self._valid_status_code(result, 'Failed to deploy release; error: {0}'.format(result.text))
        deployment_result = json.loads(result.text)

        self.wait_till_deployment_completes(deployment_result)

        return deployment_result

    def delete_environment(self, environment_id):
        self._delete_machines_associated_with_environment(environment_id)
        api_url = urljoin(self.host, '/api/environments/{0}'.format(environment_id))
        result = requests.delete(api_url, params=self.rest_params)
        self._valid_status_code(result, 'Error during delete environment: {0}'.format(result.text))
        return True

    def _delete_machines_associated_with_environment(self, environment_id):
        environment_machines_url = urljoin(self.host, 'api/environments/{0}/machines'.format(environment_id))
        while True:
            result = requests.get(environment_machines_url, params=self.rest_params)
            environment_machines = json.loads(result.content)
            if not environment_machines['Items']:
                break
            for machine in environment_machines['Items']:
                self.delete_machine(machine['Id'])

    def delete_machine(self, machine_id):
        if not self.machine_exists(machine_id):
            raise Exception('Machine does not exist')
        api_url = urljoin(self.host, '/api/machines/{0}'.format(machine_id))
        result = requests.delete(api_url, params=self.rest_params)

    def delete_release(self, release_id):
        if not self.release_exists(release_id):
            raise Exception('Release does not exist')
        api_url = urljoin(self.host, '/api/releases/{0}'.format(release_id))
        return requests.delete(api_url, params=self.rest_params)

    def delete_lifecycle(self, lifecycle_id):
        api_url = urljoin(self.host, 'api/lifecycles/{0}'.format(lifecycle_id))
        result = requests.delete(api_url, params=self.rest_params)
        self._valid_status_code(result, 'Failed to delete lifecycle; error: {0}'.format(result.text))
        return True

    def delete_channel(self, channel_id):
        self._delete_channel_releases(channel_id)
        api_url = urljoin(self.host, '/api/channels/{0}'.format(channel_id))
        result = requests.delete(api_url, params=self.rest_params)
        self._valid_status_code(result, 'Failed to delete channel; error: {0}'.format(result.text))
        return json.loads(result.content)

    def _delete_channel_releases(self, channel_id):
        api_url = urljoin(self.host, '/api/channels/{0}/releases'.format(channel_id))
        result = requests.get(api_url, params=self.rest_params)
        self._valid_status_code(result, 'Failed to get channel releases; error: {0}'.format(result.text))
        releases_dict = json.loads(result.content)
        if 'Items' in releases_dict:
            for release in releases_dict['Items']:
                self.delete_release(release['Id'])

    def add_existing_machine_to_environment(self, machine_id, environment_id, roles=[]):
        api_url = urljoin(self.host, '/api/machines/{0}'.format(machine_id))
        result = requests.get(api_url, params=self.rest_params)
        existing_machine = json.loads(result.text)
        existing_machine['EnvironmentIds'].append(environment_id)
        if roles:
            existing_machine['Roles'].extend(roles)
        result = requests.put(api_url, params=self.rest_params, json=existing_machine)
        self._valid_status_code(result,
                                'Failed to add existing machine with id {0} to environment {1}.'
                                '\nError: {2}'.format(machine_id, environment_id, result.text))
        return json.loads(result.content)

    def remove_existing_machine_from_environment(self, machine_id, environment_id):
        api_url = urljoin(self.host, '/api/machines/{0}'.format(machine_id))
        result = requests.get(api_url, params=self.rest_params)
        existing_machine = json.loads(result.text)
        if environment_id in existing_machine['EnvironmentIds']:
            existing_machine['EnvironmentIds'].remove(environment_id)
        result = requests.put(api_url, params=self.rest_params, json=existing_machine)
        self._valid_status_code(result,
                                'Failed to remove existing machine with id {0} to environment {1}.'
                                '\nError: {2}'.format(machine_id, environment_id, result.text))
        return json.loads(result.content)

    def wait_till_deployment_completes(self, deployment_result, retries=30, wait_duration=60):
        deployments = self._get_release_deployments(deployment_result)

        for deployment in deployments:
            deployment_completed = False
            task_url = urljoin(self.host, deployment['Links']['Task'])
            for retry in xrange(retries):
                result = requests.get(task_url, params=self.rest_params)
                if json.loads(result.content)['IsCompleted']:
                    deployment_completed = True
                    break
                else:
                    time.sleep(wait_duration)
            if not deployment_completed:
                raise Exception('Timeout after {0}'.format(str(retries*wait_duration)))

    def _get_release_deployments(self, deployment_result):
        deployments_url = urljoin(self.host, deployment_result['Links']['Release'] + '/deployments')
        result = requests.get(deployments_url, params=self.rest_params)
        self._valid_status_code(result, 'Failed to get release deployments; error: {0}'.format(result.text))
        deployments = json.loads(result.content)['Items']
        return deployments

    def environment_exists(self, environment_id):
        api_url = urljoin(self.host, '/api/environments/{0}'.format(environment_id))
        result = requests.get(api_url, params=self.rest_params)
        try:
            self._valid_status_code(result, 'Environment not found; error: {0}'.format(result.text))
        except:
            return False
        return True

    def get_entity(self, relative_path):
        api_url = urljoin(self.host, relative_path)
        result = requests.get(api_url, params=self.rest_params)
        self._valid_status_code(result, 'Couldn''t get entity. error: {0}'.format(result.text))
        return json.loads(result.content)

    def find_lifecycle_by_name(self, lifecycle_name):
        api_url = urljoin(self.host, '/api/lifecycles/all')
        result = requests.get(api_url, params=self.rest_params)
        self._valid_status_code(result, 'Failed to find lifecycle {1}; error: {0}'.format(result.text, lifecycle_name))
        lifecycles = json.loads(result.content)
        for lifecycle in lifecycles:
            if lifecycle['Name'] == lifecycle_name:
                return lifecycle
        raise Exception('Lifecycle named {0} was not found on Octopus Deploy'.format(lifecycle_name))

    def find_project_by_name(self, project_name):
        api_url = urljoin(self.host, '/api/projects/all')
        result = requests.get(api_url, params=self.rest_params)
        self._valid_status_code(result, 'Failed to find project {1}; error: {0}'.format(result.text, project_name))
        projects = json.loads(result.content)
        for project in projects:
            if project['Name'] == project_name:
                return project
        raise Exception('Project named {0} was not found on Octopus Deploy'.format(project_name))

    def find_machine_by_name(self, machine_name):
        """
        :type machine_name: str
        :return:
        """
        api_url = urljoin(self.host, '/api/machines/all')
        result = requests.get(api_url, params=self.rest_params)
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
        result = requests.get(api_url, params=self.rest_params)
        self._valid_status_code(result, 'Failed to find environment {1}; error: {0}'.format(result.text,
                                                                                            environment_name))
        environments = json.loads(result.content)
        for environment_dict in environments:
            if environment_dict['Name'] == environment_name:
                return environment_dict
        raise Exception('Environment named {0} was not found on Octopus Deploy'.format(environment_name))

    def find_channel_by_name_on_project(self, project_id, channel_name):
        api_url = urljoin(self.host, '/api/projects/{0}/channels'.format(project_id))
        result = requests.get(api_url, params=self.rest_params)
        project_channels = json.loads(result.text)['Items']
        for channel in project_channels:
            if channel['Name'] == channel_name:
                return channel
        raise Exception('Channel named {0} was not found on Octopus Deploy'.format(channel_name))

    def channel_exists(self, project_id, channel_name):
        api_url = urljoin(self.host, '/api/projects/{0}/channels'.format(project_id))
        result = requests.get(api_url, params=self.rest_params)
        project_channels = json.loads(result.text)['Items']
        for channel in project_channels:
            if channel['Name'] == channel_name:
                return True
        return False

    def lifecycle_exists(self, lifecycle_id):
        api_url = urljoin(self.host, '/api/lifecycles/{0}'.format(lifecycle_id))
        result = requests.get(api_url, params=self.rest_params)
        try:
            self._valid_status_code(result, 'Lifeycle not found; error: {0}'.format(result.text))
        except:
            return False
        return True

    def machine_exists(self, machine_id):
        api_url = urljoin(self.host, '/api/machines/{0}'.format(machine_id))
        result = requests.get(api_url, params=self.rest_params)
        try:
            self._valid_status_code(result, 'Machine not found; error: {0}'.format(result.text))
        except:
            return False
        return True

    def machine_exists_on_environment(self, machine_id, environment_id):
        api_url = urljoin(self.host, '/api/machines/{0}'.format(machine_id))
        result = requests.get(api_url, params=self.rest_params)
        self._valid_status_code(result, 'Machine with id {1} not found; error: {0}'.format(result.text, machine_id))
        machine = json.loads(result.text)
        return True if environment_id in machine['EnvironmentIds'] else False

    def release_exists(self, release_id):
        api_url = urljoin(self.host, '/api/releases/{0}'.format(release_id))
        result = requests.get(api_url, params=self.rest_params)
        try:
            self._valid_status_code(result, 'Machine not found; error: {0}'.format(result.text))
        except:
            return False
        return True

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
