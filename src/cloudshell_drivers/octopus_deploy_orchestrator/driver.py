from cloudshell.api.cloudshell_api import CloudShellAPISession
from cloudshell.shell.core.resource_driver_interface import ResourceDriverInterface
from cloudshell.shell.core.driver_context import InitCommandContext, ResourceCommandContext
from cloudshell.octopus.session import OctopusServer
from cloudshell.octopus.environment_spec import EnvironmentSpec
from cloudshell.octopus.release_spec import ReleaseSpec

# cloudshell attribute names
OCTOPUS_DEPLOY_PROVIDER = 'Octopus Deploy Provider'
OCTOPUS_API_KEY = 'API Key'
import json


class OctopusDeployOrchestratorDriver(ResourceDriverInterface):
    def __init__(self):
        """
        ctor must be without arguments, it is created with reflection at run time
        """

    def initialize(self, context):
        """
        Initialize the driver session, this function is called everytime a new instance of the driver is created
        This is a good place to load and cache the driver configuration, initiate sessions etc.
        :param InitCommandContext context: the context the command runs on
        """
        pass

    def add_environment_to_optional_targets_of_lifecycle(self, project_name, channel_name, environment_name, phase_name):
        return self._add_environment_to_optional_targets_of_lifecycle(project_name, channel_name, environment_name, phase_name)

    def add_existing_machine_to_environment(self, context, machine_name, machine_roles, environment_name):
        """
        :param machine_name: the name of existing machine in Octopus Deploy
        :param machine_roles: a comma separated list of role names, must be at least one
        :param environment_id: id of environment in octopus deploy server
        :type machine_name: str
        :type machine_roles: str
        :type environment_id: str
        :param ResourceCommandContext context: the context the command runs on
        """
        return self._add_existing_machine_to_environment(context, machine_name, machine_roles, environment_name)

    def remove_existing_machine_from_environment(self, context, machine_name, environment_name):
        """
        :param machine_name: the name of existing machine in Octopus Deploy
        :param machine_roles: a comma separated list of role names, must be at least one
        :param environment_id: id of environment in octopus deploy server
        :type machine_name: str
        :type machine_roles: str
        :type environment_id: str
        :param ResourceCommandContext context: the context the command runs on
        """
        return self._remove_existing_machine_from_environment(context, machine_name, environment_name)

    def create_environment(self, context, environment_name):
        """
        :param ResourceCommandContext context: the context the command runs on
        """
        return self._create_environment(context, environment_name)

    def delete_environment(self, context, environment_name):
        """
        :param ResourceCommandContext context: the context the command runs on
        """
        return self._delete_environment(context, environment_name)

    def create_lifecycle(self, context):
        """
        :param ResourceCommandContext context: the context the command runs on
        """
        return self._create_lifecycle(context)

    def delete_lifecycle(self, context):
        """
        :param ResourceCommandContext context: the context the command runs on
        """
        return self._delete_lifecycle(context)

    def deploy_environment_to_release(self, context, project_name, release_version, environment_name):
        cloudshell = self._get_cloudshell_api(context)
        octo = self._get_octopus_server(context, cloudshell)
        project = octo.find_project_by_name(project_name)
        release = octo.get_release_by_id(project['Id'], release_version)
        environment = octo.find_environment_by_name(environment_name)
        octo.deploy_release(release['Id'], environment['Id'])
        return 'Deployed {0} - {1} to {2}'.format(project_name, release['Version'], environment_name)

    def get_channel_latest_release_version_name(self, context, project_name, channel_name):
        cloudshell = self._get_cloudshell_api(context)
        octo = self._get_octopus_server(context, cloudshell)
        project = octo.find_project_by_name(project_name)
        channel = octo.find_channel_by_name_on_project(project['Id'], channel_name)
        release = octo.get_latest_channel_release(channel['Id'])
        return str(release['Id'])

    def get_release_by_version_name(self, context, project_name, version_name):
        cloudshell = self._get_cloudshell_api(context)
        octo = self._get_octopus_server(context, cloudshell)
        project = octo.find_project_by_name(project_name)
        release = octo.get_release_by_version_name(project['Id'], version_name)
        return str(release['Id']) # strip quotes

    def add_environment_to_optional_targets_of_lifecycle(self, context, project_name, channel_name, environment_name, phase_name):
        cloudshell = self._get_cloudshell_api(context)
        octo = self._get_octopus_server(context, cloudshell)
        project = octo.find_project_by_name(project_name)
        channel = octo.find_channel_by_name_on_project(project['Id'], channel_name)
        lifecycle_id = channel['LifecycleId']
        environment = octo.find_environment_by_name(environment_name)
        octo.add_environment_to_lifecycle_on_phase(environment['Id'], lifecycle_id, phase_name)

    def remove_environment_from_optional_targets_of_lifecycle(self, context, project_name, channel_name, environment_name, phase_name):
        cloudshell = self._get_cloudshell_api(context)
        octo = self._get_octopus_server(context, cloudshell)
        project = octo.find_project_by_name(project_name)
        channel = octo.find_channel_by_name_on_project(project['Id'], channel_name)
        lifecycle_id = channel['LifecycleId']
        environment = octo.find_environment_by_name(environment_name)
        octo.remove_environment_from_lifecycle_on_phase(environment['Id'], lifecycle_id, phase_name)

    def create_and_deploy_release(self, context, project_name):
        return self._create_and_deploy_release(context, project_name)

    def delete_release(self, context, project_name):
        return self._delete_release(context, project_name)

    def _create_and_deploy_release(self, context, project_name):
        cloudshell = self._get_cloudshell_api(context)
        octo = self._get_octopus_server(context, cloudshell)
        release_spec = self._get_release_spec(context, octo, project_name)
        # environment_id = octo.find_environment_by_name(context.reservation.reservation_id)['Id']
        octo.create_release(release_spec)
        # octo.deploy_release(release_spec, environment_id)

    def _delete_release(self, context, project_name):
        cloudshell = self._get_cloudshell_api(context)
        octo = self._get_octopus_server(context, cloudshell)
        release_spec = self._get_release_spec(context, octo, project_name)
        octo.delete_release(release_spec.id)

    def _get_release_spec(self, context, octo, project_name, channel_name=None):
        channel_name = channel_name or context.reservation.reservation_id
        project = octo.find_project_by_name(project_name)
        channel = octo.find_channel_by_name_on_project(project_id=project['Id'], channel_name=channel_name)
        # octopus deploy release version - "You can also use the letter i to increment part of the last release"
        release_spec = ReleaseSpec(project['Id'], version='1.i', release_notes='Cloudshell Release', channel_id=channel['Id'])
        return release_spec

    def create_channel(self, context, project_name):
        """
        :param ResourceCommandContext context: the context the command runs on
        """
        return self._create_channel(context, project_name)

    def delete_channel(self, context, project_name):
        """
        :param ResourceCommandContext context: the context the command runs on
        """
        return self._delete_channel(context, project_name)

    def _create_channel(self, context, project_name):
        """
        :param project_name: name of project with which channel is associated
        :param ResourceCommandContext context: the context the command runs on
        """
        cloudshell = self._get_cloudshell_api(context)
        octo = self._get_octopus_server(context, cloudshell)
        project = octo.find_project_by_name(project_name)
        lifecycle = octo.find_lifecycle_by_name(context.reservation.reservation_id)
        octo.create_channel(context.reservation.reservation_id, project['Id'], lifecycle['Id'])
        return 'Channel created'

    def _delete_channel(self, context, project_name):
        """
        :param project_name: name of project with which channel is associated
        :param ResourceCommandContext context: the context the command runs on
        """
        cloudshell = self._get_cloudshell_api(context)
        octo = self._get_octopus_server(context, cloudshell)
        project = octo.find_project_by_name(project_name)
        channel = octo.find_channel_by_name_on_project(project_id=project['Id'],
                                             channel_name=context.reservation.reservation_id)
        octo.delete_channel(channel['Id'])
        return 'Channel deleted'

    def _create_environment(self, context, environment_name):
        cloudshell = self._get_cloudshell_api(context)
        octo = self._get_octopus_server(context, cloudshell)
        env = self._get_environment_spec(context)
        env._name = environment_name
        deployed_env = octo.create_environment(env)
        # todo add machines to environment
        return json.dumps(deployed_env.__dict__)

    def _create_lifecycle(self, context):
        cloudshell = self._get_cloudshell_api(context)
        octo = self._get_octopus_server(context, cloudshell)
        environment = self._get_deployed_environment_spec(self._get_environment_spec(context), octo)
        #lifecycle name == environment name == reservation id
        return octo.create_lifecycle(environment.name, 'Cloudshell Sandbox Lifecycle', environment.id)

    def _delete_lifecycle(self, context):
        cloudshell = self._get_cloudshell_api(context)
        octo = self._get_octopus_server(context, cloudshell)
        #lifecycle name == environment name == reservation id
        lifecycle_name = self._get_environment_spec(context).name
        lifecycle = octo.find_lifecycle_by_name(lifecycle_name)
        return octo.delete_lifecycle(lifecycle['Id'])

    def _get_deployed_environment_spec(self, env_spec, octo_session):
        id = octo_session.find_environment_by_name(env_spec.name)['Id']
        env_spec.set_id(id)
        return env_spec

    def _add_existing_machine_to_environment(self, context, machine_name, machine_roles, environment_name):
        """
        :param machine_name: the name of existing machine in Octopus Deploy
        :param machine_roles: a comma separated list of role names, must be at least one
        :param environment_name: environment to which the machine will be added
        :type machine_name: str
        :type machine_roles: str
        :type environment_name: str
        :param ResourceCommandContext context: the context the command runs on
        :return:
        """
        roles = self._parse_roles(machine_roles)
        cloudshell = self._get_cloudshell_api(context)
        octo = self._get_octopus_server(context, cloudshell)
        machine = octo.find_machine_by_name(machine_name)
        environment = octo.find_environment_by_name(environment_name)
        octo.add_existing_machine_to_environment(machine['Id'], environment['Id'], roles)

    def _remove_existing_machine_from_environment(self, context, machine_name, environment_name):
        cloudshell = self._get_cloudshell_api(context)
        octo = self._get_octopus_server(context, cloudshell)
        environment = octo.find_environment_by_name(environment_name)
        machine = octo.find_machine_by_name(machine_name)
        if self._check_if_last_environment_machine_is_associated_with(environment, machine):
            return 'Could not remove {0} from {1}, a machine must be associated with at least one environment' \
               'and {1} was the last environment with which {0} was associated'.format(machine_name, environment_name)
        octo.remove_existing_machine_from_environment(machine['Id'], environment['Id'])
        return 'Removed {0} from {1}'

    def _check_if_last_environment_machine_is_associated_with(self, environment, machine):
        return len(machine['EnvironmentIds']) == 1 and environment['Id'] in machine['EnvironmentIds']

    def _parse_roles(self, machine_roles):
        roles = machine_roles.split(',')
        roles = filter(None, roles)
        return roles

    def _get_environment_spec(self, context):
        return EnvironmentSpec(name=context.reservation.reservation_id,
                               description=context.reservation.description,
                               sort_order=0,
                               use_guided_failure=False)

    def _get_octopus_server(self, context, cloudshell):
        try:
            octopus_server = cloudshell.GetResourceDetails(context.resource.attributes[OCTOPUS_DEPLOY_PROVIDER])
        except Exception as e:
            raise Exception('Could not find the Octopus Deploy Provider resource on Cloudshell.'
                            ' \nError details: \n{0}'.format(e.message))
        octopus_attributes = self._get_resource_attributes_as_dict(octopus_server.ResourceAttributes)
        return OctopusServer(host=octopus_server.Address, api_key=octopus_attributes[OCTOPUS_API_KEY])

    def _get_resource_attributes_as_dict(self, attributes_list):
        return {resource_attribute.Name: resource_attribute.Value for resource_attribute in attributes_list}

    def _get_cloudshell_api(self, context):
        return CloudShellAPISession(host=context.connectivity.server_address,
                                    token_id=context.connectivity.admin_auth_token,
                                    domain=context.reservation.domain)

    def cleanup(self):
        """
        Destroy the driver session, this function is called everytime a driver instance is destroyed
        This is a good place to close any open sessions, finish writing to log files
        """
        pass

    def _delete_environment(self, context, environment_name):
        cloudshell = self._get_cloudshell_api(context)
        octo = self._get_octopus_server(context, cloudshell)
        environment_id = octo.find_environment_by_name(environment_name)['Id']
        if octo.delete_environment(environment_id):
            return 'Environment deleted'
