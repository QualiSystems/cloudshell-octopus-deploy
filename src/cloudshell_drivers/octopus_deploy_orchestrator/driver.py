from cloudshell.api.cloudshell_api import CloudShellAPISession
from cloudshell.shell.core.resource_driver_interface import ResourceDriverInterface
from cloudshell.shell.core.driver_context import InitCommandContext, ResourceCommandContext
from cloudshell_demos.octopus.session import OctopusServer
from cloudshell_demos.octopus.environment_spec import EnvironmentSpec

# cloudshell_demos attribute names
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

    def add_existing_machine_to_environment(self, context, machine_name, machine_roles, environment_id):
        """
        :param machine_name: the name of existing machine in Octopus Deploy
        :param machine_roles: a comma separated list of role names, must be at least one
        :param environment_id: id of environment in octopus deploy server
        :type machine_name: str
        :type machine_roles: str
        :type environment_id: str
        :param ResourceCommandContext context: the context the command runs on
        """
        return self._add_existing_machine_to_environment(context, machine_name, machine_roles, environment_id)

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

    def create_environment(self, context):
        """
        :param ResourceCommandContext context: the context the command runs on
        """
        return self._create_environment(context)

    def delete_environment(self, context):
        """
        :param ResourceCommandContext context: the context the command runs on
        """
        return self._delete_environment(context)

    def _create_environment(self, context):
        cloudshell = self._get_cloudshell_api(context)
        octo = self._get_octopus_server(context, cloudshell)
        env = self._get_environment_spec(context)
        deployed_env = octo.create_environment(env)
        # todo add machines to environment
        return json.dumps(deployed_env.__dict__)

    def _add_existing_machine_to_environment(self, context, machine_name, machine_roles, environment_id):
        """
        :param machine_name: the name of existing machine in Octopus Deploy
        :param machine_roles: a comma separated list of role names, must be at least one
        :param environment_id: environment to which the machine will be added
        :type machine_name: str
        :type machine_roles: str
        :type environment_id: str
        :param ResourceCommandContext context: the context the command runs on
        :return:
        """
        roles = self._parse_roles(machine_roles)
        cloudshell = self._get_cloudshell_api(context)
        octo = self._get_octopus_server(context, cloudshell)
        machine = octo.find_machine_by_name(machine_name)
        octo.add_existing_machine_to_environment(machine['Id'], environment_id, roles)

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

    def _delete_environment(self, context):
        cloudshell = self._get_cloudshell_api(context)
        octo = self._get_octopus_server(context, cloudshell)
        env = self._get_environment_spec(context)
        environment_id = octo.find_environment_by_name(env.name)['Id']
        if octo.delete_environment_by_environment_id(environment_id):
            return 'Environment deleted'
