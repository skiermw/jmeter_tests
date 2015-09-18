#!/usr/bin/env python
#   load_policy.py
#
import sys
import json
from pprint import pprint
import urllib2
import urllib
import requests
from collections import defaultdict

def ReadPolJSON():
    #filename = 'leased_policy.json'
    #filename = 'claims_policies.json'
    filename = 'renewal_policies.json'

    global outfile
    outputfile = 'renewal_input.txt'
    outfile = open(outputfile, 'w')
    
    global server
    server = 'dcdevappsrv1'
    print('Server: %s' % server)
    
    pol_json = []
    
    with open(filename) as pol_file:
        pol_json = json.load(pol_file)
        for policy in pol_json['policies']:
            CreateQuote(policy)

    outfile.close()
    

def CreateQuote(pol_json):
    # Set environment
    environ = 'demo'
    # Address, Applicant, 
    #  Create the quote with policy json body
    
    url = 'http://%s:8083/direct/quote' % server
    response = requests.post(url, data=json.dumps(pol_json))
    quote_auth_token = response.headers['quoteauthtoken']
    quote_json = json.loads(response.text)
    #print(quote_json)
    #print(' ')
    if response.status_code != 200:
        print('quote status: %s' % response.status_code)
    #print(quote_json)
    quote_stream_id = quote_json['streamId']
    #print(quote_stream_id)
    quote_stream_rev = quote_json['streamRevision']
    
    #print ('Stream ID: %s ' % quote_stream_id)
    #print ('Stream Rev: %s' % quote_stream_rev)
    #print ('Auth Token: %s' % quote_auth_token)
        
    # remove all vehicles
    veh_coll = []
    for veh in quote_json['events'][0]['quote']['vehicles']:
        veh_coll.append( veh['id'])
    url = 'http://%s:8083/direct/quote/%s/%s/vehicles' % (server, quote_stream_id, quote_stream_rev)
    payload = {'ids': json.dumps(veh_coll)}
    headers = {'quoteAuthToken': quote_auth_token}
    response = requests.delete(url, params=payload, headers=headers)
    response_json = json.loads(response.text)
    #print(response_json)
    #print('vehicle delete response:')
    quote_stream_rev = response_json['streamRevision']
    #print('vehicle delete response:')
    #print(response.text)
    if response.status_code != 200:
        print('vehicle delete response: %s' % response.status_code)
    
    # add vehicles from input json back on
    #  create json for coverages 
    coverage_input = {}
    vehicles = []
    coverages = []
    for vehicle in pol_json['vehicles']:
        #print('@@@@@@@@@@ Vehicle')
        vehicle_body = {}
        veh = {}
        veh['year'] = vehicle['year']
        veh['make'] = vehicle['make']
        veh['model'] = vehicle['model']
        veh['trim'] = vehicle['trim']
        veh['vin'] = vehicle['vin']
        veh['lengthOfOwnership'] = vehicle['lengthOfOwnership']
        veh['ownership'] = vehicle['ownership']
        veh['businessUse'] = vehicle['businessUse']
        if 'antiTheftDevice' in vehicle:
            veh['antiTheftDevice'] = vehicle['antiTheftDevice']
        #  write vehicle
        url = 'http://%s:8083/direct/quote/%s/%s/vehicle' % (server, quote_stream_id, quote_stream_rev)
        payload = json.dumps(veh)
        headers = {'quoteAuthToken': quote_auth_token}
        response = requests.post(url, data=payload, headers=headers)
        response_json = json.loads(response.text)
        
        quote_stream_rev = response_json['streamRevision']
        #print(quote_stream_rev)
        if response.status_code != 200:
            print('Add vehicle status: %s' % response.status_code)

        # read the response to get new vehicle id
        #response_json = json.loads(response.text)
        vehicle_body['id'] = response_json['events'][0]['vehicle']['id']
        if 'financeCompany' in vehicle:
            #print('finance company')
            fin_co_input = {}
            fin_co_input['name'] = vehicle['financeCompany']['name']
            fin_co_input['loanNumber'] = vehicle['financeCompany']['loanNumber']
            fin_co_input['address'] = {}
            fin_co_input['address']['street'] = vehicle['financeCompany']['address']['street']
            fin_co_input['address']['street2'] = vehicle['financeCompany']['address']['street2']
            fin_co_input['address']['city'] = vehicle['financeCompany']['address']['city']
            fin_co_input['address']['state'] = vehicle['financeCompany']['address']['state']
            fin_co_input['address']['zip'] = vehicle['financeCompany']['address']['zip']
            
            #write finance company
            url = 'http://%s:8083/direct/quote/%s/%s/vehicle/%s/financeCompany' % (server, quote_stream_id, quote_stream_rev, vehicle_body['id'])
            payload = json.dumps(fin_co_input)
            headers = {'quoteAuthToken': quote_auth_token}
            response = requests.post(url, data=payload, headers=headers)
            response_json = json.loads(response.text)
            if response.status_code == 200:
                quote_stream_rev = response_json['streamRevision']
                
            if response.status_code != 200:
                print('Add finance co status: %s' % response.status_code)
            #print(response.url)
            #print(response.text)
        
        coverages = []
        for coverage in vehicle['coverages']:
            coverage_body = {}
            limits = []
            if coverage['type'] == 'RoadsideAssistance':
                continue
            else:
                for limit in coverage['limits']:
                    limit_body = {}
                    limit_body['type'] = limit['type']
                    limit_body['value'] = limit['value']
                    limits.append(limit_body)
    
            coverage_body['type'] = coverage['type']
            coverage_body['limits'] = limits
            coverages.append(coverage_body)
   
        vehicle_body['coverages'] = coverages
        #print('vehicle body')
        #print(vehicle_body)
        vehicles.append(vehicle_body)
        
    
    coverage_input['vehicles'] = vehicles
    #print('coverage_input = %s' % coverage_input)
    url = 'http://%s:8083/direct/quote/%s/%s/coverages' % (server, quote_stream_id, quote_stream_rev)
    payload = json.dumps(coverage_input)
    headers = {'quoteAuthToken': quote_auth_token}
    response = requests.put(url, data=payload, headers=headers)
    if response.status_code != 200:
        print('Update Coverages status: %s' % response.status_code)
   
    response_json = json.loads(response.text)
    if response.status_code == 200:
        quote_stream_rev = response_json['streamRevision']
    else:
        print(' ')
        print(response.url)
        print(response.text)
                

    #print(response.url)
    
    #print ('Stream Rev: %s' % quote_stream_rev)
    
    ########################################################################################
    ##### delete all drivers
    drivers_coll = []
    applicant_id = quote_json['events'][0]['quote']['applicant']['id']
    for driver in quote_json['events'][0]['quote']['drivers']:
        #  Special processing for driver that is also applicant (can't delete that driver)
        if driver['id'] == applicant_id:
            continue
        else:
            drivers_coll.append( driver['id'])
    url = 'http://%s:8083/direct/quote/%s/%s/drivers' % (server, quote_stream_id, quote_stream_rev)
    payload = {'ids': json.dumps(drivers_coll)}
    headers = {'quoteAuthToken': quote_auth_token}
    response = requests.delete(url, params=payload, headers=headers)
    quote_stream_rev =  quote_stream_rev + 1
    #print('Delete driver response:')
    #print(response.text)
    if response.status_code != 200:
        print('driver delete response: %s' % response.status_code)
    
    # add drivers from input json back on
    #  create json for coverages 
    
    drivers = []
    driver_ct = 0
    for driver in pol_json['drivers']:
        #print('@@@@@@@@@@ Driver')
        driver_body = {}
        driver_body['firstName'] = driver['firstName']
        driver_body['middleName'] = driver['middleName']
        driver_body['lastName'] = driver['lastName']
        driver_body['birthDate'] = driver['birthDate']
        driver_body['email'] = driver['email']
        driver_body['phoneNumber'] = driver['phoneNumber']
        driver_body['gender'] = driver['gender']
        driver_body['ssn'] = driver['ssn']
        driver_body['maritalStatus'] = driver['maritalStatus']
        driver_body['licenseNumber'] = driver['licenseNumber']
        driver_body['licenseState'] = driver['licenseState']
        
        #  write driver
          
        payload = json.dumps(driver_body)
        headers = {'quoteAuthToken': quote_auth_token}
        # assuming first driver is the applicant (which can't be deleted) so update with needed info
        #   all other drivers will be deleted from quote then re-added from json
        if driver_ct == 0:
            url = 'http://%s:8083/direct/quote/%s/%s/driver/%s' % (server, quote_stream_id, quote_stream_rev, applicant_id)
            response = requests.put(url, data=payload, headers=headers)
            if response.status_code != 200:
                print('Update driver status: %s' % response.status_code)
            #print(response.text)
        else:
            url = 'http://%s:8083/direct/quote/%s/%s/driver' % (server, quote_stream_id, quote_stream_rev)
            response = requests.post(url, data=payload, headers=headers)
            if response.status_code != 200:
                print('Add driver status: %s' % response.status_code)
            [{"failureCodes":[{"code":"InvalidLimitType","defaultMessage":"Uninsured Motorist Property Damage coverage requires Per Occurrence and Deductible limits. It cannot have other types."}],"field":"vehicles[0].coverages[5]"},{"failureCodes":[{"code":"UmpdPrerequisiteRequired","defaultMessage":"Collision coverage must be absent when buying Uninsured Motorist Property Damage coverage"}],"field":"vehicles[0]"}]
        quote_stream_rev =  quote_stream_rev + 1
        driver_ct = driver_ct + 1
        
    ### get Clue and MVR
    url = 'http://%s:8083/direct/quote/%s/%s/drivingRecord' % (server, quote_stream_id, quote_stream_rev)
    headers = {'quoteAuthToken': quote_auth_token}
    data = urllib.urlencode(pol_json)
    response = requests.post(url, data=payload, headers=headers)
    quote_stream_rev =  quote_stream_rev + 1
    #print (' Clue / MVR')
    #print(response.text)
    if response.status_code != 200:
        print("Clue/MVR: %s" % response.status_code)
    #print(response.url)
    
    ### Rate this puppy
    rating_channel = {"ratingChannel":"PublicWebsite"}
    url = 'http://%s:8083/direct/quote/%s/%s/rate' % (server, quote_stream_id, quote_stream_rev)
    headers = {'quoteAuthToken': quote_auth_token}
    data = json.dumps(rating_channel)
    response = requests.post(url, data=data, headers=headers)
    quote_stream_rev =  quote_stream_rev + 1
    #print(response.text)
    if response.status_code != 200:
        print("Rate: %s" % response.status_code)
    response_json = json.loads(response.text)
    if response.status_code == '200':
        quote_stream_rev = response_json['streamRevision']

    ### Answer Speed Racer question
    speed_racer = {"isASpeedRacer":'false'}
    url = 'http://%s:8083/direct/quote/%s/%s' % (server, quote_stream_id, quote_stream_rev)
    headers = {'quoteAuthToken': quote_auth_token}
    data = json.dumps(speed_racer)
    response = requests.patch(url, data=data, headers=headers)
    response_json = json.loads(response.text)
    #print(response.text)
    if response.status_code != 200:
        print("Speed Racer: %s" % response.status_code)
    #print(response.url)
    quote_stream_rev = response_json['streamRevision']

    ### Generate Policy Number
    url = 'http://%s:8083/direct/quote/%s/%s/policyNumber' % (server, quote_stream_id, quote_stream_rev)
    headers = {'quoteAuthToken': quote_auth_token}
    response = requests.post(url, headers=headers)
    response_json = json.loads(response.text)
    #print(response.text)
    if response.status_code != 200:
        print("Policy Number: %s" % response.status_code)
    #print(response.url)CreateQuote(pol_json)
    quote_stream_rev = response_json['streamRevision']
    policy_number = response_json['events'][0]['policyNumber']
    ### Purchase
    body = {}
    body['quoteId'] = quote_stream_id
    body['ipAddress'] = '10.8.30.145'
    body['expectedStreamRevision'] = quote_stream_rev
    body['channelOfOrigin'] = 'PublicWebsite'
    data = urllib.urlencode(body)
    #print(data)
    url = 'http://%s:8083/direct/policy?%s' % (server, data)
    headers = {'quoteAuthToken': quote_auth_token}
    response = requests.post(url, headers=headers)
    #print(response.text)
    if response.status_code != 200:
        print("Purchase: %s" % response.status_code)
    #print(response.url)
    response_json = json.loads(response.text)
    policy_stream_rev = response_json['streamRevision']

    print('Policy description: %s' % pol_json['testPolicyDescription'])
    print('  Policy Number: %s' % policy_number)
    print('  Policy stream rev: %s' % policy_stream_rev)
    print('  Policy stream ID: %s' % response_json['streamId'])
    print('  Policy eff date: %s' % response_json['timestamp'])

    #print(outfile.name)
          
    outfile.write(response_json['streamId']+"\n")
    #outfile.write('policy_number')
    
'''
    ### Get Policy Number
    
    body = {}
    body['everything'] = 'true'
    body['discounts'] = 'true'
    body['coverages'] = 'true'
    body['vehicles'] = 'true'
    body['nonDescribedVehicle'] = 'true'
    body['applicant'] = 'true'
    body['drivers'] = 'true'
    body['namedInsureds'] = 'true'
    body['additionalListedInsureds'] = 'true'
    body['timestamp'] = response_json['timestamp']
    data = urllib.urlencode(body)
    url = 'http://dcdemoappsrv1:8083/direct/policy/%s?%s' %  (response_json['streamId'], data)
    response = requests.get(url)
    print('Get Policy Number: %s' % response.status_code)
    print(response.url)
    response_json = json.loads(response.text)
    
    print("Policy Number: %s" % response_json['policyNumber'])
'''  
def main():
   
   
   ReadPolJSON()
   
   
   

      
# Start program
if __name__ == "__main__":
   main()
