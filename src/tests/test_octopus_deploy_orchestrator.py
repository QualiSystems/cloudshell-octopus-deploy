import unittest
from uuid import uuid4
from context import OCTOPUS_HOST, OCTOPUS_API_KEY, TENTACLE_SERVER, THUMBPRINT, PROJECT_ID
from cloudshell.api.cloudshell_api import CloudShellAPISession
from cloudshell_drivers.octopus_deploy_orchestrator.driver import OctopusDeployOrchestratorDriver, \
    OCTOPUS_DEPLOY_PROVIDER
from cloudshell_demos.octopus.session import OctopusServer
from cloudshell_demos.octopus.environment_spec import EnvironmentSpec
import json


class MockObject(object):
    pass


def get_mock_resource_command_context():
    rcc = MockObject()
    rcc.reservation = MockObject()
    rcc.reservation.reservation_id = str(uuid4())
    rcc.reservation.description = 'Hmm, interesting description'
    rcc.reservation.domain = 'Global'
    rcc.resource = MockObject()
    rcc.resource.attributes = {OCTOPUS_DEPLOY_PROVIDER: 'Octopus-Azure'}
    rcc.connectivity = MockObject()
    rcc.connectivity.server_address = 'localhost'
    rcc.connectivity.admin_auth_token = CloudShellAPISession(host=rcc.connectivity.server_address,
                                                             domain=rcc.reservation.domain,
                                                             username='admin',
                                                             password='admin').token_id
    return rcc


class OctopusDeployOrchestratorTest(unittest.TestCase):
    def setUp(self):
        self.resource_command_context = get_mock_resource_command_context()
        self.driver = OctopusDeployOrchestratorDriver()
        self.octo = OctopusServer(OCTOPUS_HOST, OCTOPUS_API_KEY)
        self.DEPLOYED_ENV = None

    def tearDown(self):
        if self.DEPLOYED_ENV:
            self.octo.delete_environment(self.DEPLOYED_ENV)

    def test_create_environment_command(self):
        result = self.driver.create_environment(self.resource_command_context)
        self.DEPLOYED_ENV = EnvironmentSpec.from_dict(json.loads(result))
        self.assertTrue(self.octo.environment_exists(self.DEPLOYED_ENV))
