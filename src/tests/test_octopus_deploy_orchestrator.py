import unittest
from uuid import uuid4
from context import OCTOPUS_HOST, OCTOPUS_API_KEY, TENTACLE_SERVER, THUMBPRINT, PROJECT_ID
from cloudshell.api.cloudshell_api import CloudShellAPISession
from cloudshell_drivers.octopus_deploy_orchestrator.driver import OctopusDeployOrchestratorDriver, \
    OCTOPUS_DEPLOY_PROVIDER
from cloudshell_demos.octopus.session import OctopusServer
from cloudshell_demos.octopus.environment_spec import EnvironmentSpec
from cloudshell_demos.octopus.machine_spec import MachineSpec
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
        self.ENVIRONMENTS = []
        self.MACHINES = []
        self.LIFECYCLES = []

    def tearDown(self):
        if hasattr(self, 'MACHINES'):
            for machine in self.MACHINES:
                self.octo.delete_machine(machine)
        if hasattr(self, 'RELEASE'):
            self.octo.delete_release(self.RELEASE)
        if hasattr(self, 'LIFECYCLES'):
            for lifecycle in self.LIFECYCLES:
                self.octo.delete_lifecycle(lifecycle['Id'])
        if hasattr(self, 'ENVIRONMENTS'):
            for environment in self.ENVIRONMENTS:
                self.octo.delete_environment(environment)

    def test_create_environment_command(self):
        result = self.driver.create_environment(self.resource_command_context)
        env = EnvironmentSpec.from_dict(json.loads(result))
        self.ENVIRONMENTS.append(env)
        self.assertTrue(self.octo.environment_exists(env))

    def _given_an_environment_exists(self, random_environment_id=None):
        if random_environment_id:
            self.resource_command_context.reservation.reservation_id = str(uuid4())
        result = self.driver.create_environment(self.resource_command_context)
        env = EnvironmentSpec.from_dict(json.loads(result))
        self.ENVIRONMENTS.append(env)
        return env

    def _given_a_machine_exists(self, environment_id):
        machine_spec = \
            MachineSpec(name='machine_name',
                        roles=['role1', 'role2'],
                        thumbprint=THUMBPRINT,
                        uri=TENTACLE_SERVER,
                        environment_ids=[environment_id])
        deployed_machine_spec = self.octo.create_machine(machine_spec)
        self.MACHINES.append(deployed_machine_spec)
        return deployed_machine_spec

    def _given_a_machine_exists_on_an_environment(self):
        env = self._given_an_environment_exists()
        machine = self._given_a_machine_exists(env.id)
        return env, machine

    def _given_the_machine_is_also_associated_with_another_environment(self, machine):
        self.resource_command_context.reservation.reservation_id = str(uuid4())
        env = self._given_an_environment_exists()
        self.octo.add_existing_machine_to_environment(machine.id, env.id)
        return env

    def test_add_existing_machine_to_environment_command(self):
        old_env = self._given_an_environment_exists()
        machine_name = self._given_a_machine_exists(old_env.id).name

        new_env = self._given_an_environment_exists(True)
        roles = 'MachineRole1'
        self.driver.add_existing_machine_to_environment(self.resource_command_context, machine_name, roles, new_env.id)
        machine_id = self.octo.find_machine_by_name(machine_name)['Id']
        self.assertTrue(self.octo.machine_exists_on_environment(machine_id, new_env.id))
        self.octo.remove_existing_machine_from_environment(machine_id, new_env.id)

    # can only remove machine from environment if it still is associated with another environment
    def test_remove_existing_machine_from_environment_command(self):
        old_env, machine = self._given_a_machine_exists_on_an_environment()
        new_env = self._given_the_machine_is_also_associated_with_another_environment(machine)
        self.assertTrue(self.octo.machine_exists_on_environment(machine.id, new_env.id))
        self.driver.remove_existing_machine_from_environment(self.resource_command_context, machine.name, new_env.name)
        self.assertFalse(self.octo.machine_exists_on_environment(machine.id, new_env.id))

    def test_delete_environment(self):
        env = self._given_an_environment_exists()
        self.assertTrue(self.octo.environment_exists(env))
        self.driver.delete_environment(self.resource_command_context)
        self.ENVIRONMENTS.remove(env)
        self.assertFalse(self.octo.environment_exists(env))

    def test_create_lifecycle(self):
        env = self._given_an_environment_exists()
        lifecycle = self.driver.create_lifecycle(self.resource_command_context)
        self.LIFECYCLES.append(lifecycle)
        self.assertTrue(self.octo.lifecycle_exists(lifecycle))

    def _given_a_lifecycle_exists(self):
        env = self._given_an_environment_exists()
        lifecycle = self.driver.create_lifecycle(self.resource_command_context)
        self.LIFECYCLES.append(lifecycle)
        return lifecycle

    def test_delete_lifecycle(self):
        lifecycle = self._given_a_lifecycle_exists()
        self.assertTrue(self.octo.lifecycle_exists(lifecycle))
        self.driver.delete_lifecycle(self.resource_command_context)
        self.LIFECYCLES.remove(lifecycle)
        self.assertFalse(self.octo.lifecycle_exists(lifecycle))

