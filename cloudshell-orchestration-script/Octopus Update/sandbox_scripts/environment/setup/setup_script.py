from cloudshell.api.cloudshell_api import *
from cloudshell.helpers.scripts import cloudshell_scripts_helpers as helpers
from cloudshell.core.logger.qs_logger import get_qs_logger
import octopus_constants as oct

SERVICE_TARGET_TYPE = 'Service'
GET_LATEST_CHANNEL_RELEASE = 'get_channel_latest_release_version_name'
GET_RELEASE_BY_VERSION_NAME = 'get_release_by_version_name'
OCTOPUS_ORCHESTRATOR_SERVICE_NAME = 'Octopus Deploy Orchestrator'


class EnvironmentSetup(object):
    NO_DRIVER_ERR = "129"
    DRIVER_FUNCTION_ERROR = "151"

    def __init__(self):
        self.reservation_id = helpers.get_reservation_context_details().id
        self.logger = get_qs_logger(log_file_prefix="CloudShell Sandbox Setup",
                                    log_group=self.reservation_id,
                                    log_category='Setup')

    def execute(self):
        api = helpers.get_api_session()
        reservation_details = api.GetReservationDetails(self.reservation_id)
        octopus_service = self._get_octopus_service(reservation_details)
        if not octopus_service: return

        res_id = reservation_details.ReservationDescription.Id
        inputs = {input.ParamName: input.Value for input in api.GetReservationInputs(res_id).GlobalInputs}

        version_name = helpers.get_user_param('Version')
        if version_name.lower() == 'latest':
            version_id = self.get_latest_release_version_id(api, inputs, octopus_service.Alias, res_id)
        else:
            version_id = self.get_release_id_by_version_name(api, inputs, octopus_service.Alias, res_id, version_name)

        octo_environment_name = self._get_octopus_environment_name(reservation_details)

        if version_name:
            self._deploy_sandbox_to_octopus(res_id, octopus_service.Alias, inputs, api, octo_environment_name, version_id)

    def get_latest_release_version_id(self, api, inputs, octopus_service, res_id):
        project_name = InputNameValue('project_name', inputs['Project Name'])
        channel_name = InputNameValue('channel_name', inputs['Channel Name'])
        # api.WriteMessageToReservationOutput(res_id, '\n'.join([octopus_service, GET_LATEST_CHANNEL_RELEASE, project_name, channel_name]))
        version_id = api.ExecuteCommand(res_id, octopus_service, SERVICE_TARGET_TYPE, GET_LATEST_CHANNEL_RELEASE,
                                          [project_name, channel_name]).Output
        return version_id

    def get_release_id_by_version_name(self, api, inputs, octopus_service, res_id, version_name):
        project_input = InputNameValue('project_name', inputs['Project Name'])
        version_input = InputNameValue('version_name', version_name)
        version_id = api.ExecuteCommand(res_id, octopus_service, SERVICE_TARGET_TYPE, GET_RELEASE_BY_VERSION_NAME,
                                          [project_input, version_input]).Output
        return version_id

    def _deploy_sandbox_to_octopus(self, res_id, octopus_service, inputs, api, octopus_environment_name, version_id):
        project_name = InputNameValue('project_name', inputs['Project Name'])
        release_version = InputNameValue('release_version', version_id)
        environment_name = InputNameValue('environment_name', octopus_environment_name)

        api.ExecuteCommand(res_id, octopus_service, SERVICE_TARGET_TYPE, oct.DEPLOY_RELEASE_COMMAND,
                           [project_name, release_version, environment_name])

        api.WriteMessageToReservationOutput(res_id, 'Deployment to Octopus completed')

    def _get_octopus_environment_name(self, reservation_details):
        environment_name = '{0} - {1}'.format(reservation_details.ReservationDescription.Name,
                                              reservation_details.ReservationDescription.Id)
        environment_name = self._cut_long_env_name(environment_name)
        return environment_name

    def _cut_long_env_name(self, environment_name):
        over_length = len(environment_name) - 50
        if over_length > 0:
            environment_name = environment_name[over_length:]
        return environment_name

    def _get_octopus_service(self, reservation_details):
        # check if octopus service in blueprint, if not ignore this
        for service in reservation_details.ReservationDescription.Services:
            if service.ServiceName == OCTOPUS_ORCHESTRATOR_SERVICE_NAME:
                octopus_service = service
                break
        else:
            return None
        return octopus_service


