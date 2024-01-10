#!/usr/bin/env python3
from ec2_metadata import ec2_metadata
import boto3
import sys
# from pprint import pp
from datetime import datetime

ec2 = boto3.client('ec2')
r53 = boto3.client('route53')

response = ec2.describe_instances(
    Filters=[
        {
            'Name': 'instance-id',
            'Values': [f'{ec2_metadata.instance_id}']
        }
    ]
)

instance = response['Reservations'][0]['Instances'][0]

name = instance['InstanceId']
zones = []

for tag in instance['Tags']:
    if tag['Key'] in ('Name', 'DnsName'):
        name = tag['Value']
    elif tag['Key'].startswith('DnsZone'):
        zones.append(tag['Value'])

if not zones:
    print('no zones to update', file=sys.stderr)
    sys.exit(1)

private_ip, public_ip = (
    instance['PrivateIpAddress'],
    instance['PublicIpAddress']
)
now = datetime.now()

for zone in zones:
    if not zone.endswith('.'):
        zone += '.'
    response = r53.list_hosted_zones_by_name(DNSName=zone)
    for hosted_zone in response['HostedZones']:
        if zone == hosted_zone['Name']:
            ip = private_ip \
                if hosted_zone['Config']['PrivateZone'] \
                else public_ip
            zone_id = hosted_zone['Id']
            print(name, zone, ip, zone_id, sep=':')
            r53.change_resource_record_sets(
                HostedZoneId=f'{zone_id}',
                ChangeBatch={
                    'Comment': f'update_r53.py @ {now}',
                    'Changes': [
                        {
                            'Action': 'UPSERT',
                            'ResourceRecordSet': {
                                'Name': f'{name}.{zone}',
                                'Type': 'A',
                                'TTL': 60,
                                'ResourceRecords': [
                                    {
                                        'Value': f'{ip}'
                                    },
                                ],
                                # 'SetIdentifier': f'{name}',
                                # 'Weight': 0,
                                # 'Region': 'us-east-1'|'us-east-2'|'us-west-1'|'us-west-2'|'ca-central-1'|'eu-west-1'|'eu-west-2'|'eu-west-3'|'eu-central-1'|'eu-central-2'|'ap-southeast-1'|'ap-southeast-2'|'ap-southeast-3'|'ap-northeast-1'|'ap-northeast-2'|'ap-northeast-3'|'eu-north-1'|'sa-east-1'|'cn-north-1'|'cn-northwest-1'|'ap-east-1'|'me-south-1'|'me-central-1'|'ap-south-1'|'ap-south-2'|'af-south-1'|'eu-south-1'|'eu-south-2'|'ap-southeast-4'|'il-central-1'|'ca-west-1',
                                # 'GeoLocation': {
                                #     'ContinentCode': 'string',
                                #     'CountryCode': 'string',
                                #     'SubdivisionCode': 'string'
                                # },
                                # 'Failover': 'PRIMARY'|'SECONDARY',
                                # 'MultiValueAnswer': False,
                                # 'AliasTarget': {
                                #     'HostedZoneId': 'string',
                                #     'DNSName': 'string',
                                #     'EvaluateTargetHealth': True|False
                                # },
                                # 'HealthCheckId': 'string',
                                # 'TrafficPolicyInstanceId': 'string',
                                # 'CidrRoutingConfig': {
                                #     'CollectionId': 'string',
                                #     'LocationName': 'string'
                                # }
                            }
                        },
                    ]
                }
            )
