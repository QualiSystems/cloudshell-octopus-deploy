from cloudshell.api.cloudshell_api import CloudShellAPISession, ApiEditAppRequest, AppDetails, Deployment, \
    NameValuePair, \
    DefaultDeployment, Installation, Script

api = CloudShellAPISession(username='admin', password='admin', domain='Global', host='localhost')
res = api.GetReservationDetails(reservationId='61c6c382-dae6-4500-893a-dc6fb29b55a5').ReservationDescription
app = res.Apps[0]

edit_vals = ApiEditAppRequest('Octopus-Tentacle',
                              'Octopus-Tentacle',
                              '',
                              None,
                              DefaultDeployment={'Name': 'Azure - Azure VM From Marketplace',
                                                 'Deployment': {
                                                     'Attributes': [{'Name': 'Extension Script Configurations', 'Value':
                                                         'lollert'}]},
                                                 'Installation': None})

result = api.EditAppsInReservation(res.Id, editAppsRequests=[edit_vals])
print api
