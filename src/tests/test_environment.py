import unittest
from cloudshell.octopus.session import OctopusServer
from cloudshell.octopus.environment_spec import EnvironmentSpec
from cloudshell.octopus.machine_spec import MachineSpec
from cloudshell.octopus.release_spec import ReleaseSpec
from context import OCTOPUS_HOST, OCTOPUS_API_KEY, TENTACLE_SERVER, THUMBPRINT, PROJECT_ID
from random import randint


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

    def tearDown(self):
        if hasattr(self, 'MACHINES'):
            for machine in self.MACHINES:
                self.OCTO_SESSION.delete_machine(machine)
        if hasattr(self, 'RELEASE'):
            self.OCTO_SESSION.delete_release(self.RELEASE)
        if hasattr(self, 'DEPLOYED_ENV'):
            self.OCTO_SESSION.delete_environment(self.QUALI_ENV_SPEC)

    def test_create_new_environment(self):
        self.DEPLOYED_ENV = self.OCTO_SESSION.create_machine(self.QUALI_ENV_SPEC)
        self.assertTrue(self.OCTO_SESSION.machine_exists(self.QUALI_ENV_SPEC))

    def test_create_machine(self):
        self.DEPLOYED_ENV = self._given_an_environment_exists_on_octopus()
        machine_spec = \
            MachineSpec(name='machine_name',
                                   roles=['role1', 'role2'],
                                   thumbprint=THUMBPRINT,
                                   uri=TENTACLE_SERVER,
                                   environment_ids=[self.DEPLOYED_ENV.id])
        self.MACHINES = [self.OCTO_SESSION.create_machine(machine_spec)]
        self.assertTrue(self.OCTO_SESSION.machine_exists(self.MACHINES[0]))

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
        self.RELEASE = self._given_a_release_exists_on_octopus()
        result = self.OCTO_SESSION.deploy_release(self.RELEASE, self.DEPLOYED_ENV)
        self.assertTrue(self.OCTO_SESSION.wait_for_deployment_to_complete(result))

    def _given_an_environment_exists_on_octopus(self, octopus_session=None, env=None, machine_specs=[]):
        if not octopus_session:
            octopus_session = self.OCTO_SESSION
        if not env:
            env = self.QUALI_ENV_SPEC
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
