import unittest
from random import randint
from cloudshell_demos.octopus.session import OctopusServer
from cloudshell_demos.octopus.environment_spec import EnvironmentSpec
from cloudshell_demos.octopus.machine_spec import MachineSpec
from cloudshell_demos.octopus.release_spec import ReleaseSpec
from context import OCTOPUS_HOST, OCTOPUS_API_KEY, TENTACLE_SERVER, THUMBPRINT, PROJECT_ID


class OctopusDeployTest(unittest.TestCase):
    def setUp(self):
        self.OCTO_SESSION = OctopusServer(host=OCTOPUS_HOST, api_key=OCTOPUS_API_KEY)
        self.QUALI_ENV_SPEC = EnvironmentSpec(name='some_appropriate_name',
                                              description='Some environment lol who carez yo!',
                                              sort_order=5,
                                              use_guided_failure=False)
        self.QUALI_RELEASE_SPEC = ReleaseSpec(project_id=PROJECT_ID,
                                              version='.'.join([str(randint(0, 8000000)),
                                                                str(randint(0, 8000000)),
                                                                str(randint(0, 8000000))]),
                                              release_notes='Ya welli')
        self.MACHINE_SPEC = MachineSpec(name='machine_name',
                                        roles=['role1', 'role2'],
                                        thumbprint=THUMBPRINT,
                                        uri=TENTACLE_SERVER,
                                        environment_ids=[])
        self.ENVIRONMENTS = []
        self.MACHINES = []

    def tearDown(self):
        if hasattr(self, 'MACHINES'):
            for machine in self.MACHINES:
                self.OCTO_SESSION.delete_machine(machine)
        if hasattr(self, 'RELEASE'):
            self.OCTO_SESSION.delete_release(self.RELEASE)
        if hasattr(self, 'ENVIRONMENTS'):
            for environment in self.ENVIRONMENTS:
                self.OCTO_SESSION.delete_environment(environment)

    def test_create_new_environment(self):
        self.DEPLOYED_ENV = self.OCTO_SESSION.create_environment(self.QUALI_ENV_SPEC)
        self.ENVIRONMENTS.append(self.DEPLOYED_ENV)
        self.assertTrue(self.OCTO_SESSION.environment_exists(self.DEPLOYED_ENV))

    def test_create_machine(self):
        self.DEPLOYED_ENV = self._given_an_environment_exists_on_octopus()
        self.ENVIRONMENTS.append(self.DEPLOYED_ENV)
        machine_spec = MachineSpec(name='machine_name',
                                   roles=['role1', 'role2'],
                                   thumbprint=THUMBPRINT,
                                   uri=TENTACLE_SERVER,
                                   environment_ids=[self.DEPLOYED_ENV.id])
        deployed_machine_spec = self.OCTO_SESSION.create_machine(machine_spec)
        self.MACHINES.append(deployed_machine_spec)
        self.assertTrue(self.OCTO_SESSION.machine_exists(deployed_machine_spec))

    def test_add_existing_machine_to_environment(self):
        self.DEPLOYED_ENV = self._given_an_environment_exists_on_octopus()
        self.ENVIRONMENTS.append(self.DEPLOYED_ENV)
        deployed_machine_spec = self._given_a_machine_exists()
        another_env = self._given_an_environment_exists_on_octopus(name='lolbert')
        self.ENVIRONMENTS.append(another_env)
        self.OCTO_SESSION.add_existing_machine_to_environment(deployed_machine_spec.id, another_env.id)
        self.assertTrue(self.OCTO_SESSION.machine_exists_on_environment(deployed_machine_spec.id, another_env.id))

    def test_create_release(self):
        release_spec = ReleaseSpec(project_id=PROJECT_ID,
                                   version='.'.join([str(randint(0, 8000000)),
                                                     str(randint(0, 8000000)),
                                                     str(randint(0, 8000000))]),
                                   release_notes='Ya welli')
        self.RELEASE = self.OCTO_SESSION.create_release(release_spec)
        self.assertTrue(self.OCTO_SESSION.release_exists(self.RELEASE))

    def test_deploy_release(self):
        self.DEPLOYED_ENV = self._given_an_environment_exists_on_octopus(machine_specs=[self.MACHINE_SPEC])
        self.ENVIRONMENTS.append(self.DEPLOYED_ENV)
        self.RELEASE = self._given_a_release_exists_on_octopus()
        result = self.OCTO_SESSION.deploy_release(self.RELEASE, self.DEPLOYED_ENV)
        self.assertTrue(self.OCTO_SESSION.wait_for_deployment_to_complete(result))

    def _given_an_environment_exists_on_octopus(self, octopus_session=None, env=None, machine_specs=[], name=None):
        if not octopus_session:
            octopus_session = self.OCTO_SESSION
        if not env:
            env = self.QUALI_ENV_SPEC
        if name:
            env.name = name
        deployed_env = octopus_session.create_environment(env)
        if machine_specs:
            self.MACHINES = []
        for machine_spec in machine_specs:
            machine_spec.environment_ids.append(deployed_env.id)
            self.MACHINES.append(self.OCTO_SESSION.create_machine(machine_spec))
        return deployed_env

    def _given_a_release_exists_on_octopus(self, octopus_session=None, release=None):
        if not octopus_session:
            octopus_session = self.OCTO_SESSION
        if not release:
            release = self.QUALI_RELEASE_SPEC
        return octopus_session.create_release(release)

    def _given_a_machine_exists(self):
        machine_spec = \
            MachineSpec(name='machine_name',
                        roles=['role1', 'role2'],
                        thumbprint=THUMBPRINT,
                        uri=TENTACLE_SERVER,
                        environment_ids=[self.DEPLOYED_ENV.id])
        deployed_machine_spec = self.OCTO_SESSION.create_machine(machine_spec)
        self.MACHINES = [deployed_machine_spec]
        return deployed_machine_spec
