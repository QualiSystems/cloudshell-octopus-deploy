import unittest
from cloudshell.octopus.session import OctopusServer
from cloudshell.octopus.environment import Environment


class EnvironmentTest(unittest.TestCase):
    def test_create_new_environment(self):
        octo_session = OctopusServer()
        quali_env = Environment(name='a short environment name, preferably 5-20 chars',
                                description='Some environment lol who carez yo!',
                                sort_order='5',
                                # PUT	If set to true, deployments will prompt for manual intervention (Fail/Retry/Ignore) when failures are encountered in activities that support it. May be overridden with the Octopus.UseGuidedFailure special variable.
                                user_guided_failure=False)
        # so you can deploy to different octopus servers?
        quali_env.deploy(octo_session)
        self.assertTrue(octo_session.environment_exists(quali_env))
