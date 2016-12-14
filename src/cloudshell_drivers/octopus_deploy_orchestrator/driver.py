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

    def add_existing_machine_to_environment(self, context):
        """
        :param ResourceCommandContext context: the context the command runs on
        """
        return self._add_existing_machine_to_environment(context)

    def create_environment(self, context):
        """
        :param ResourceCommandContext context: the context the command runs on
        """
        return self._create_environment(context)

    def _create_environment(self, context):
        cloudshell = self._get_cloudshell_api(context)
        octo = self._get_octopus_server(context, cloudshell)
        env = self._get_environment_spec(context)
        deployed_env = octo.create_environment(env)
        # todo add machines to environment
        return json.dumps(deployed_env.__dict__)

    def _add_existing_machine_to_environment(self, context):
        cloudshell = self._get_cloudshell_api(context)
        octo = self._get_octopus_server(context, cloudshell)

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