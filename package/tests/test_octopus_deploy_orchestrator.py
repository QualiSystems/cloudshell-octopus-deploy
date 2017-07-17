import unittest
from uuid import uuid4
from context import OCTOPUS_HOST, OCTOPUS_API_KEY, TENTACLE_SERVER, THUMBPRINT, PROJECT_NAME
from cloudshell.api.cloudshell_api import CloudShellAPISession
from cloudshell_drivers.octopus_deploy_orchestrator.driver import OctopusDeployOrchestratorDriver, \
    OCTOPUS_DEPLOY_PROVIDER
from cloudshell.octopus.session import OctopusServer
from cloudshell.octopus.environment_spec import EnvironmentSpec
from cloudshell.octopus.machine_spec import MachineSpec
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
        self.PROJECT_ID = self.octo.find_project_by_name(PROJECT_NAME)['Id']

    def tearDown(self):
        if hasattr(self, 'MACHINES'):
            for machine in self.MACHINES:
                self.octo.delete_machine(machine.id)
        if hasattr(self, 'RELEASE'):
            self.octo.delete_release(self.RELEASE.id)

        if self.octo.channel_exists(self.PROJECT_ID,
                                    channel_name=self.resource_command_context.reservation.reservation_id):
            self.delete_channel()
        if hasattr(self, 'LIFECYCLES'):
            for lifecycle in self.LIFECYCLES:
                self.octo.delete_lifecycle(lifecycle['Id'])
        if hasattr(self, 'ENVIRONMENTS'):
            for environment in self.ENVIRONMENTS:
                self.octo.delete_environment(environment.id)

    def delete_channel(self):
        channel = self.octo.find_channel_by_name_on_project(project_id=self.PROJECT_ID,
                                                            channel_name=self.resource_command_context.reservation.reservation_id)
        self.octo.delete_channel(channel['Id'])

    def test_create_environment_command(self):
        result = self.driver.create_environment(self.resource_command_context)
        env = EnvironmentSpec.from_dict(json.loads(result))
        self.ENVIRONMENTS.append(env)
        self.assertTrue(self.octo.environment_exists(env.id))

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
        self.driver.add_existing_machine_to_environment(self.resource_command_context, machine_name, roles,
                                                        new_env.name)
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
        self.assertTrue(self.octo.environment_exists(env.id))
        self.driver.delete_environment(self.resource_command_context)
        self.ENVIRONMENTS.remove(env)
        self.assertFalse(self.octo.environment_exists(env.id))

    def test_create_lifecycle(self):
        env = self._given_an_environment_exists()
        lifecycle = self.driver.create_lifecycle(self.resource_command_context)
        self.LIFECYCLES.append(lifecycle)
        self.assertTrue(self.octo.lifecycle_exists(lifecycle['Id']))

    def _given_a_lifecycle_exists(self):
        self._given_a_machine_exists_on_an_environment()
        lifecycle = self.driver.create_lifecycle(self.resource_command_context)
        self.LIFECYCLES.append(lifecycle)
        return lifecycle

    def test_delete_lifecycle(self):
        lifecycle = self._given_a_lifecycle_exists()
        self.assertTrue(self.octo.lifecycle_exists(lifecycle['Id']))
        self.driver.delete_lifecycle(self.resource_command_context)
        self.LIFECYCLES.remove(lifecycle)
        self.assertFalse(self.octo.lifecycle_exists(lifecycle['Id']))

    def test_create_channel(self):
        self._given_a_lifecycle_exists()
        self.driver.create_channel(self.resource_command_context, PROJECT_NAME)
        self.assertTrue(self.octo.channel_exists(self.PROJECT_ID,
                                                 channel_name=self.resource_command_context.reservation.reservation_id))

    def _given_a_channel_exists(self):
        self._given_a_lifecycle_exists()
        self.driver.create_channel(self.resource_command_context, PROJECT_NAME)

    def test_delete_channel(self):
        self._given_a_channel_exists()
        self.assertTrue(self.octo.channel_exists(self.PROJECT_ID,
                                                 channel_name=self.resource_command_context.reservation.reservation_id))
        self.driver.delete_channel(self.resource_command_context, PROJECT_NAME)
        self.assertFalse(self.octo.channel_exists(self.PROJECT_ID,
                                                  channel_name=self.resource_command_context.reservation.reservation_id))

    def test_create_and_deploy_release(self):
        self._given_a_channel_exists()
        self.driver.create_and_deploy_release(self.resource_command_context, PROJECT_NAME)
        deployments = self._get_deployments()
        self.assertTrue(len(deployments) > 0)

    def _get_deployments(self):
        channel = self.octo.find_channel_by_name_on_project(self.PROJECT_ID,
                                                            self.resource_command_context.reservation.reservation_id)
        releases = self.octo.get_entity(channel['Links']['Releases'])['Items']
        deployments = self.octo.get_entity(releases[0]['Links']['Deployments'].replace('{?skip}', ''))['Items']
        return deployments

    def test_add_environment_to_optional_targets_of_lifecycle(self):
        env = self._given_an_environment_exists()
        phase_name = 'Test'
        self.driver.add_environment_to_optional_targets_of_lifecycle(self.resource_command_context,
                                                                     channel_name='SCA Demo', project_name=PROJECT_NAME,
                                                                     phase_name=phase_name, environment_name=env.name)
        phases = self.octo.get_entity('api/lifecycles/Lifecycles-140')['Phases']
        modified_phase = (phase for phase in phases if phase['Name'] == phase_name).next()
        self.assertTrue(env.id in modified_phase['OptionalDeploymentTargets'])
        self.octo.remove_environment_from_lifecycle_on_phase(env.id, 'Lifecycles-140', phase_name)

    def test_upgrade_environment_to_version(self):
        env = self._given_an_environment_exists()