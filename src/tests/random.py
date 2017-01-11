from cloudshell.api.cloudshell_api import CloudShellAPISession
z  = CloudShellAPISession(host='localhost', username='admin', password='admin')
from cloudshell.api.cloudshell_api import *
attr_name = 'Extension Script Configurations'
attr_value = 'lololo'
deployment = Deployment(Attributes=[NameValuePair(Name=attr_name, Value=attr_value)])
deploy_model = 'Azure VM From Marketplace'
app_name = 'Web Server'
default_deployment = DefaultDeployment(Deployment=deployment, Installation=None, Name=deploy_model)
change_request = ApiEditAppRequest(app_name, app_name, '', None, default_deployment)
r = z.EditAppsInReservation('372a671f-16c5-464c-aaad-9401aecc1b83', [change_request])