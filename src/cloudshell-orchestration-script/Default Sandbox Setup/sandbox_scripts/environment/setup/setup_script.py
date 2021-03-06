from multiprocessing.pool import ThreadPool
from threading import Lock

from cloudshell.helpers.scripts import cloudshell_scripts_helpers as helpers
from cloudshell.api.cloudshell_api import *
from cloudshell.api.common_cloudshell_api import CloudShellAPIError
from cloudshell.core.logger.qs_logger import get_qs_logger
from remap_child_resources_constants import *
import octopus_constants as oct

from sandbox_scripts.helpers.resource_helpers import *
from sandbox_scripts.profiler.env_profiler import profileit

SERVICE_TARGET_TYPE = 'Service'

DEPLOY_COMMAND = 'deploy'

CREATE_PROFILE_COMMAND = 'create_profile'

CLOUD_PROVIDER_ATTR = 'cloud_provider'

AZURE_RESOURCE_ATTR = 'Azure Resource'

PROFILE_NAME_ATTR = 'Profile Name'

OCTOPUS_ORCHESTRATOR_SERVICE_NAME = 'Octopus Deploy Orchestrator'


class EnvironmentSetup(object):
    NO_DRIVER_ERR = "129"
    DRIVER_FUNCTION_ERROR = "151"

    def __init__(self):
        self.reservation_id = helpers.get_reservation_context_details().id
        self.logger = get_qs_logger(log_file_prefix="CloudShell Sandbox Setup",
                                    log_group=self.reservation_id,
                                    log_category='Setup')

    @profileit(scriptName='Setup')
    def execute(self):
        api = helpers.get_api_session()
        resource_details_cache = {}

        api.WriteMessageToReservationOutput(reservationId=self.reservation_id,
                                            message='Beginning reservation setup')

        self._prepare_connectivity(api, self.reservation_id)

        reservation_details = api.GetReservationDetails(self.reservation_id)

        self._deploy_cloud_provider_services(api, reservation_details)

        octo_environment_name = self._get_octopus_environment_name(reservation_details)
        environment_parameters_for_octopus_apps = self._create_octopus_environment(reservation_details, api,
                                                                                   octo_environment_name)

        api.WriteMessageToReservationOutput(self.reservation_id, 'Octopus parameters are: {0}'
                                            .format(environment_parameters_for_octopus_apps))

        deploy_result = self._deploy_apps_in_reservation(api=api,
                                                         reservation_details=reservation_details,
                                                         octopus_app_params=environment_parameters_for_octopus_apps)

        self._try_exeucte_autoload(api=api,
                                   deploy_result=deploy_result,
                                   resource_details_cache=resource_details_cache)

        # refresh reservation_details after app deployment if any deployed apps
        if deploy_result and deploy_result.ResultItems:
            reservation_details = api.GetReservationDetails(self.reservation_id)

        self._connect_all_routes_in_reservation(api=api,
                                                reservation_details=reservation_details,
                                                reservation_id=self.reservation_id,
                                                resource_details_cache=resource_details_cache)

        self._run_async_power_on_refresh_ip_install(api=api,
                                                    reservation_details=reservation_details,
                                                    deploy_results=deploy_result,
                                                    resource_details_cache=resource_details_cache,
                                                    reservation_id=self.reservation_id)

        self.logger.info("Setup for reservation {0} completed".format(self.reservation_id))
        api.WriteMessageToReservationOutput(reservationId=self.reservation_id,
                                            message='Reservation setup finished successfully')

        self._deploy_sandbox_to_octopus(reservation_details, api, octo_environment_name)

    def _deploy_sandbox_to_octopus(self, reservation_details, api, octopus_environment_name):
        octopus_service = self._get_octopus_service(reservation_details).Alias
        if not octopus_service: return

        res_id = reservation_details.ReservationDescription.Id
        inputs = {input.ParamName: input.Value for input in api.GetReservationInputs(res_id).GlobalInputs}
        project_name = InputNameValue('project_name', inputs['Project Name'])
        channel_name = InputNameValue('channel_name', inputs['Channel Name'])
        release_version = InputNameValue('release_version', inputs['Release Version'])
        phase_name = InputNameValue('phase_name', inputs['Phase Name'])
        environment_name = InputNameValue('environment_name', octopus_environment_name)

        api.ExecuteCommand(res_id, octopus_service, SERVICE_TARGET_TYPE, oct.ADD_ENVIRONMENT_TO_LIFECYCLE_COMMAND,
                           [project_name, channel_name, environment_name, phase_name])
        api.ExecuteCommand(res_id, octopus_service, SERVICE_TARGET_TYPE, oct.DEPLOY_RELEASE_COMMAND,
                           [project_name, release_version, environment_name])

        api.WriteMessageToReservationOutput(res_id, 'Deployment to Octopus completed')

    def _create_octopus_environment(self, reservation_details, api, octopus_environment_name):
        octopus_service = self._get_octopus_service(reservation_details)
        if not octopus_service: return
        res_id = reservation_details.ReservationDescription.Id
        environment_name = octopus_environment_name

        api.ExecuteCommand(res_id, octopus_service.Alias, SERVICE_TARGET_TYPE, oct.CREATE_ENVIRONMENT,
                           [InputNameValue('environment_name', environment_name)])
        octopus_deploy_name = (attr.Value for attr in octopus_service.Attributes if
                               attr.Name == 'Octopus Deploy Provider').next()
        octopus_deploy = api.GetResourceDetails(octopus_deploy_name)
        api_key = (attr.Value for attr in octopus_deploy.ResourceAttributes if attr.Name == 'API Key').next()
        environment_parameters_for_octopus_apps = '{0} {1} "{2}"'.format(octopus_deploy.Address, api_key,
                                                                         environment_name)

        api.WriteMessageToReservationOutput(res_id, 'Created to Octopus environment')
        return environment_parameters_for_octopus_apps

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

    def _deploy_cloud_provider_services(self, api, reservation_details):
        cloud_provider = self._get_cloud_provider_from_azure_apps(reservation_details)
        if cloud_provider is not None:
            pool = ThreadPool()
            deploy_commands = []
            cdn_profiles = []
            for service in reservation_details.ReservationDescription.Services:
                service_attributes = {attr.Name: attr.Value for attr in service.Attributes}

                if AZURE_RESOURCE_ATTR in service_attributes.keys():
                    deploy_commands.append((api.ExecuteCommand, (reservation_details.ReservationDescription.Id,
                                                                 service.Alias, SERVICE_TARGET_TYPE, DEPLOY_COMMAND,
                                                                 [InputNameValue(CLOUD_PROVIDER_ATTR,
                                                                                 service_attributes[
                                                                                     AZURE_RESOURCE_ATTR])])))

                if PROFILE_NAME_ATTR in service_attributes.keys():
                    self.create_profile(api, cdn_profiles, service_attributes[AZURE_RESOURCE_ATTR], reservation_details,
                                        service,
                                        service_attributes)

            for deploy_command in deploy_commands:
                pool.apply_async(*deploy_command)
            pool.close()
            pool.join()

    def create_profile(self, api, cdn_profiles, cloud_provider, reservation_details, service, service_attributes):
        profile = service_attributes[PROFILE_NAME_ATTR]
        if profile not in cdn_profiles:
            cdn_profiles.append(profile)
            api.ExecuteCommand(reservation_details.ReservationDescription.Id, service.Alias, SERVICE_TARGET_TYPE,
                               CREATE_PROFILE_COMMAND, [InputNameValue(CLOUD_PROVIDER_ATTR, cloud_provider)])

    def _get_cloud_provider_from_azure_apps(self, reservation_details):
        """
        :type reservation_details: cloudshell.api.cloudshell_api.GetReservationDescriptionResponseInfo
        :return:
        """
        for app in reservation_details.ReservationDescription.Apps:
            try:
                path = self._get_active_deployment_path(app)
                if 'azure' in path.DeploymentService.Name.lower():
                    return self._get_cloud_provider_attribute_value(path)
            except StopIteration:
                continue
        return None

    def _get_cloud_provider_attribute_value(self, path):
        return (attr.Value for attr in path.DeploymentService.Attributes if attr.Name == 'Cloud Provider').next()

    def _get_active_deployment_path(self, app):
        return (deployment_path for deployment_path in app.DeploymentPaths if deployment_path.IsDefault is True).next()

    def _prepare_connectivity(self, api, reservation_id):
        """
        :param CloudShellAPISession api:
        :param str reservation_id:
        """
        self.logger.info("Preparing connectivity for reservation {0}".format(self.reservation_id))
        api.WriteMessageToReservationOutput(reservationId=self.reservation_id, message='Preparing connectivity')
        api.PrepareSandboxConnectivity(reservation_id)

    def _try_exeucte_autoload(self, api, deploy_result, resource_details_cache):
        """
        :param GetReservationDescriptionResponseInfo reservation_details:
        :param CloudShellAPISession api:
        :param BulkAppDeploymentyInfo deploy_result:
        :param (dict of str: ResourceInfo) resource_details_cache:
        :return:
        """

        if deploy_result is None:
            self.logger.info("No apps to discover")
            api.WriteMessageToReservationOutput(reservationId=self.reservation_id, message='No apps to discover')
            return

        message_written = False

        for deployed_app in deploy_result.ResultItems:
            if not deployed_app.Success:
                continue
            deployed_app_name = deployed_app.AppDeploymentyInfo.LogicalResourceName

            resource_details = api.GetResourceDetails(deployed_app_name)
            resource_details_cache[deployed_app_name] = resource_details

            autoload = "true"
            autoload_param = get_vm_custom_param(resource_details, "autoload")
            if autoload_param:
                autoload = autoload_param.Value
            if autoload.lower() != "true":
                self.logger.info("Apps discovery is disabled on deployed app {0}".format(deployed_app_name))
                continue

            try:
                self.logger.info("Executing Autoload command on deployed app {0}".format(deployed_app_name))
                if not message_written:
                    api.WriteMessageToReservationOutput(reservationId=self.reservation_id,
                                                        message='Apps are being discovered...')
                    message_written = True

                api.AutoLoad(deployed_app_name)

                # for devices that are autoloaded and have child resources attempt to call "Connect child resources"
                # which copies CVCs from app to deployed app ports.
                api.ExecuteCommand(self.reservation_id, deployed_app_name,
                                   TARGET_TYPE_RESOURCE,
                                   REMAP_CHILD_RESOURCES, [])

            except CloudShellAPIError as exc:
                if exc.code not in (EnvironmentSetup.NO_DRIVER_ERR,
                                    EnvironmentSetup.DRIVER_FUNCTION_ERROR,
                                    MISSING_COMMAND_ERROR):
                    self.logger.error(
                        "Error executing Autoload command on deployed app {0}. Error: {1}".format(deployed_app_name,
                                                                                                  exc.rawxml))
                    api.WriteMessageToReservationOutput(reservationId=self.reservation_id,
                                                        message='Discovery failed on "{0}": {1}'
                                                        .format(deployed_app_name, exc.message))

            except Exception as exc:
                self.logger.error("Error executing Autoload command on deployed app {0}. Error: {1}"
                                  .format(deployed_app_name, str(exc)))
                api.WriteMessageToReservationOutput(reservationId=self.reservation_id,
                                                    message='Discovery failed on "{0}": {1}'
                                                    .format(deployed_app_name, exc.message))

    def _deploy_apps_in_reservation(self, api, reservation_details, octopus_app_params):
        apps = reservation_details.ReservationDescription.Apps
        if not apps or (len(apps) == 1 and not apps[0].Name):
            self.logger.info("No apps found in reservation {0}".format(self.reservation_id))
            api.WriteMessageToReservationOutput(reservationId=self.reservation_id,
                                                message='No apps to deploy')
            return None

        self.update_octopus_apps(api, apps, octopus_app_params)

        app_names = map(lambda x: x.Name, apps)
        app_inputs = map(lambda x: DeployAppInput(x.Name, "Name", x.Name), apps)

        api.WriteMessageToReservationOutput(reservationId=self.reservation_id,
                                            message='Apps deployment started')
        self.logger.info(
            "Deploying apps for reservation {0}. App names: {1}".format(reservation_details, ", ".join(app_names)))

        res = api.DeployAppToCloudProviderBulk(self.reservation_id, app_names, app_inputs)

        return res

    def update_octopus_apps(self, api, apps, octopus_app_params):
        change_requests = []
        for app in apps:
            try:
                dp = (path for path in app.DeploymentPaths if path.IsDefault).next()
                api.WriteMessageToReservationOutput(self.reservation_id, 'Found app {0}'.format(app.Name))
            except:
                continue
            attributes = {attr.Name: attr.Value for attr in dp.DeploymentService.Attributes}
            if 'Extension Script file' in attributes and 'octopus' in attributes['Extension Script file']:
                api.WriteMessageToReservationOutput(self.reservation_id, 'It is an Octopus Deploy app...')
                extension_script_params = octopus_app_params if 'Octopus Role' not in attributes \
                    else octopus_app_params + ' ' + attributes['Octopus Role']
                change_request = self._get_change_request_app_attribute_value_7_1(app.Name,
                                                                                  'Azure - ' + dp.DeploymentService.Model,
                                                                                  'Extension Script Configurations',
                                                                                  extension_script_params)
                change_requests.append(change_request)
        if change_requests:
            api.EditAppsInReservation(self.reservation_id, change_requests)

    def _connect_all_routes_in_reservation(self, api, reservation_details, reservation_id, resource_details_cache):
        """
        :param CloudShellAPISession api:
        :param GetReservationDescriptionResponseInfo reservation_details:
        :param str reservation_id:
        :param (dict of str: ResourceInfo) resource_details_cache:
        :return:
        """
        connectors = reservation_details.ReservationDescription.Connectors
        endpoints = []
        for endpoint in connectors:
            if endpoint.State in ['Disconnected', 'PartiallyConnected', 'ConnectionFailed'] \
                    and endpoint.Target and endpoint.Source:
                endpoints.append(endpoint.Target)
                endpoints.append(endpoint.Source)

        if not endpoints:
            self.logger.info("No routes to connect for reservation {0}".format(self.reservation_id))
            return

        self.logger.info("Executing connect routes for reservation {0}".format(self.reservation_id))
        self.logger.debug("Connecting: {0}".format(",".join(endpoints)))
        api.WriteMessageToReservationOutput(reservationId=self.reservation_id,
                                            message='Connecting all apps')
        res = api.ConnectRoutesInReservation(self.reservation_id, endpoints, 'bi')
        return res

    def _run_async_power_on_refresh_ip_install(self, api, reservation_details, deploy_results, resource_details_cache,
                                               reservation_id):
        """
        :param CloudShellAPISession api:
        :param GetReservationDescriptionResponseInfo reservation_details:
        :param BulkAppDeploymentyInfo deploy_results:
        :param (dict of str: ResourceInfo) resource_details_cache:
        :param str reservation_id:
        :return:
        """
        # filter out resources not created in this reservation
        resources = get_resources_created_in_res(reservation_details=reservation_details, reservation_id=reservation_id)
        if len(resources) == 0:
            api.WriteMessageToReservationOutput(
                reservationId=self.reservation_id,
                message='No resources to power on or install')
            self._validate_all_apps_deployed(deploy_results)
            return

        pool = ThreadPool(len(resources))
        lock = Lock()
        message_status = {
            "power_on": False,
            "wait_for_ip": False,
            "install": False
        }

        async_results = [pool.apply_async(self._power_on_refresh_ip_install,
                                          (api, lock, message_status, resource, deploy_results, resource_details_cache))
                         for resource in resources]

        pool.close()
        pool.join()

        for async_result in async_results:
            res = async_result.get()
            if not res[0]:
                raise Exception("Reservation is Active with Errors - " + res[1])

        self._validate_all_apps_deployed(deploy_results)

    def _validate_all_apps_deployed(self, deploy_results):
        if deploy_results is not None:
            for deploy_res in deploy_results.ResultItems:
                if not deploy_res.Success:
                    raise Exception("Reservation is Active with Errors - " + deploy_res.Error)

    def _power_on_refresh_ip_install(self, api, lock, message_status, resource, deploy_result, resource_details_cache):
        """
        :param CloudShellAPISession api:
        :param Lock lock:
        :param (dict of str: Boolean) message_status:
        :param ReservedResourceInfo resource:
        :param BulkAppDeploymentyInfo deploy_result:
        :param (dict of str: ResourceInfo) resource_details_cache:
        :return:
        """

        deployed_app_name = resource.Name
        deployed_app_data = None

        power_on = "true"
        wait_for_ip = "true"

        try:
            self.logger.debug("Getting resource details for resource {0} in reservation {1}"
                              .format(deployed_app_name, self.reservation_id))

            resource_details = get_resource_details_from_cache_or_server(api, deployed_app_name, resource_details_cache)
            # check if deployed app
            vm_details = get_vm_details(resource_details)
            if not hasattr(vm_details, "UID"):
                self.logger.debug("Resource {0} is not a deployed app, nothing to do with it".format(deployed_app_name))
                return True, ""

            auto_power_on_param = get_vm_custom_param(resource_details, "auto_power_on")
            if auto_power_on_param:
                power_on = auto_power_on_param.Value

            wait_for_ip_param = get_vm_custom_param(resource_details, "wait_for_ip")
            if wait_for_ip_param:
                wait_for_ip = wait_for_ip_param.Value

            # check if we have deployment data
            if deploy_result is not None:
                for data in deploy_result.ResultItems:
                    if data.Success and data.AppDeploymentyInfo.LogicalResourceName == deployed_app_name:
                        deployed_app_data = data
        except Exception as exc:
            self.logger.error("Error getting resource details for deployed app {0} in reservation {1}. "
                              "Will use default settings. Error: {2}".format(deployed_app_name,
                                                                             self.reservation_id,
                                                                             str(exc)))

        try:
            self._power_on(api, deployed_app_name, power_on, lock, message_status)
        except Exception as exc:
            self.logger.error("Error powering on deployed app {0} in reservation {1}. Error: {2}"
                              .format(deployed_app_name, self.reservation_id, str(exc)))
            return False, "Error powering on deployed app {0}".format(deployed_app_name)

        try:
            self._wait_for_ip(api, deployed_app_name, wait_for_ip, lock, message_status)
        except Exception as exc:
            self.logger.error("Error refreshing IP on deployed app {0} in reservation {1}. Error: {2}"
                              .format(deployed_app_name, self.reservation_id, str(exc)))
            return False, "Error refreshing IP deployed app {0}. Error: {1}".format(deployed_app_name, exc.message)

        try:
            self._install(api, deployed_app_data, deployed_app_name, lock, message_status)
        except Exception as exc:
            self.logger.error("Error installing deployed app {0} in reservation {1}. Error: {2}"
                              .format(deployed_app_name, self.reservation_id, str(exc)))
            return False, "Error installing deployed app {0}. Error: {1}".format(deployed_app_name, str(exc))

        return True, ""

    def _install(self, api, deployed_app_data, deployed_app_name, lock, message_status):
        installation_info = None
        if deployed_app_data:
            installation_info = deployed_app_data.AppInstallationInfo
        else:
            self.logger.info("Cant execute installation script for deployed app {0} - No deployment data"
                             .format(deployed_app_name))
            return

        if installation_info and hasattr(installation_info, "ScriptCommandName"):
            self.logger.info("Executing installation script {0} on deployed app {1} in reservation {2}"
                             .format(installation_info.ScriptCommandName, deployed_app_name, self.reservation_id))

            if not message_status['install']:
                with lock:
                    if not message_status['install']:
                        message_status['install'] = True
                        api.WriteMessageToReservationOutput(reservationId=self.reservation_id,
                                                            message='Apps are installing...')

            script_inputs = []
            for installation_script_input in installation_info.ScriptInputs:
                script_inputs.append(
                    InputNameValue(installation_script_input.Name, installation_script_input.Value))

            installation_result = api.InstallApp(self.reservation_id, deployed_app_name,
                                                 installation_info.ScriptCommandName, script_inputs)

            self.logger.debug("Installation_result: " + installation_result.Output)

    def _wait_for_ip(self, api, deployed_app_name, wait_for_ip, lock, message_status):
        if wait_for_ip.lower() == "true":

            if not message_status['wait_for_ip']:
                with lock:
                    if not message_status['wait_for_ip']:
                        message_status['wait_for_ip'] = True
                        api.WriteMessageToReservationOutput(
                            reservationId=self.reservation_id,
                            message='Waiting for apps IP addresses, this may take a while...')

            self.logger.info("Executing 'Refresh IP' on deployed app {0} in reservation {1}"
                             .format(deployed_app_name, self.reservation_id))

            api.ExecuteResourceConnectedCommand(self.reservation_id, deployed_app_name,
                                                "remote_refresh_ip",
                                                "remote_connectivity")
        else:
            self.logger.info("Wait For IP is off for deployed app {0} in reservation {1}"
                             .format(deployed_app_name, self.reservation_id))

    def _power_on(self, api, deployed_app_name, power_on, lock, message_status):
        if power_on.lower() == "true":
            self.logger.info("Executing 'Power On' on deployed app {0} in reservation {1}"
                             .format(deployed_app_name, self.reservation_id))

            if not message_status['power_on']:
                with lock:
                    if not message_status['power_on']:
                        message_status['power_on'] = True
                        api.WriteMessageToReservationOutput(reservationId=self.reservation_id,
                                                            message='Apps are powering on...')

            api.ExecuteResourceConnectedCommand(self.reservation_id, deployed_app_name, "PowerOn", "power")
        else:
            self.logger.info("Auto Power On is off for deployed app {0} in reservation {1}"
                             .format(deployed_app_name, self.reservation_id))

    def _get_change_request_app_attribute_value_7_1(self, app_name, deploy_model, attr_name, attr_value):
        deployment = Deployment(Attributes=[NameValuePair(Name=attr_name, Value=attr_value)])
        default_deployment = DefaultDeployment(Deployment=deployment, Installation=None, Name=deploy_model)
        change_request = ApiEditAppRequest(app_name, app_name, '', None,
                                           default_deployment)
        return change_request

    def _get_change_request_app_attribute_value_7_2(self, app_name, deploy_model, attr_name, attr_value):
        deployment = {'Attributes': [{'Name': attr_name, 'Value': attr_value}]}
        default_deployment = {'Deployment': deployment, 'Installation': None, 'Name': deploy_model}
        change_request = ApiEditAppRequest(app_name, app_name, '', None, default_deployment)
        return change_request
