#!/usr/bin/env python3

from os import environ
from boto3 import resource, setup_default_session

AWS_PROFILE = environ.get("AWS_PROFILE", "default")
AWS_REGION = environ.get("AWS_REGION", "us-east-1")

print(f"Getting VPCs and Subnets for region '{AWS_REGION}' using profile '{AWS_PROFILE}'")
try:
    setup_default_session(profile_name=AWS_PROFILE)
    EC2 = resource('ec2', region_name=AWS_REGION)
except Exception as e:
    quit(e)

VPC_LIST = list(EC2.vpcs.filter())
for VPC in VPC_LIST:
    vpc = EC2.Vpc(VPC.id)
    print(f"{vpc.id} = {vpc.cidr_block}")

    FILTER = {'Name': "vpc-id", 'Values': [vpc.id]}
    subnets = list(EC2.subnets.filter(Filters=[FILTER]))
    for subnet in subnets:
        subnet = EC2.Subnet(subnet.id)
        print(f" - {subnet.id} = {subnet.cidr_block} ({subnet.availability_zone})")
