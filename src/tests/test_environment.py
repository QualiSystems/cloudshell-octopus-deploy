import unittest
from cloudshell.octopus.session import OctopusServer
from cloudshell.octopus.environment_spec import EnvironmentSpec
from cloudshell.octopus.machine_spec import MachineSpec
from context import OCTOPUS_HOST, OCTOPUS_API_KEY, TENTACLE_SERVER


class OctopusDeployTest(unittest.TestCase):
    def setUp(self):
        self.OCTO_SESSION = OctopusServer(host=OCTOPUS_HOST, api_key=OCTOPUS_API_KEY)
        self.QUALI_ENV_SPEC = EnvironmentSpec(name='some_appropriate_name',
                                              description='Some environment lol who carez yo!',
                                              sort_order=5,
                                              use_guided_failure=False)

    def tearDown(self):
        if hasattr(self, 'MACHINE'):
            self.OCTO_SESSION.delete_machine(self.MACHINE)
        self.OCTO_SESSION.delete_environment(self.QUALI_ENV_SPEC)

    def test_create_new_environment(self):
        self.OCTO_SESSION.create_machine(self.QUALI_ENV_SPEC)
        self.assertTrue(self.OCTO_SESSION.machine_exists(self.QUALI_ENV_SPEC))

    def test_create_machine(self):
        env = self._given_an_environment_exists_on_octopus()
        machine_spec = MachineSpec(name='machine_name',
                                   roles=['role1', 'role2'],
                                   thumbprint='84B16EEA820A9D68523D56FCD0B9A290346E85D7',
                                   uri=TENTACLE_SERVER,
                                   environment_ids=[env.id])
        self.MACHINE = self.OCTO_SESSION.create_machine(machine_spec)
        self.OCTO_SESSION.machine_exists(machine_spec)

    def _given_an_environment_exists_on_octopus(self, octopus_session=None, env=None):
        if not octopus_session:
            octopus_session = self.OCTO_SESSION
        if not env:
            env = self.QUALI_ENV_SPEC
        return octopus_session.create_environment(env)
