import unittest
from cloudshell.octopus.session import OctopusServer
from cloudshell.octopus.environment import Environment
from context import OCTOPUS_HOST, OCTOPUS_API_KEY


class EnvironmentTest(unittest.TestCase):
    def test_create_new_environment(self):
        octo_session = OctopusServer(host=OCTOPUS_HOST,
                                     api_key=OCTOPUS_API_KEY)
        quali_env = Environment(name='some_appropriate_name',
                                description='Some environment lol who carez yo!',
                                sort_order=5,
                                use_guided_failure=False)
        # so you can deploy to different octopus servers?
        octo_session.deploy_environment(quali_env)
        self.assertTrue(octo_session.environment_exists(quali_env))
        octo_session.delete_environment(quali_env)

