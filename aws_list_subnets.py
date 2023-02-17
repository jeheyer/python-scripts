#!/usr/bin/env python3

from boto3 import resource

ec2 = resource('ec2')

vpcs = list(ec2.vpcs.filter())
for _ in vpcs:
    vpc = ec2.Vpc(_.id)
    print(f"{vpc.id} = {vpc.cidr_block}")
    subnets = list(ec2.subnets.filter())
    for _ in subnets:
       subnet = ec2.Subnet(_.id)
       print(f" - {subnet.id} = {subnet.cidr_block} ({subnet.availability_zone})")
