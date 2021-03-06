#!/usr/local/bin/python3

import os, sys, pprint, logging
import Inventory_Modules
import argparse, boto3
from colorama import init,Fore,Back,Style
from botocore.exceptions import ClientError, NoCredentialsError

init()

parser = argparse.ArgumentParser(
	description="We\'re going to find all resources within any of the profiles we have access to.",
	prefix_chars='-+/')
parser.add_argument(
	"-p","--profile",
	dest="pProfile",
	metavar="profile to use",
	help="To specify a specific profile, use this parameter. Default will be ALL profiles, including those in ~/.aws/credentials and ~/.aws/config")
parser.add_argument(
	"-f","--fragment",
	dest="pstackfrag",
	metavar="CloudFormation stack fragment",
	default=["all"],
	help="String fragment of the cloudformation stack or stackset(s) you want to check for.")
parser.add_argument(
	"-s","--status",
	dest="pstatus",
	metavar="CloudFormation status",
	default="active",
	help="String that determines whether we only see 'CREATE_COMPLETE' or 'DELETE_COMPLETE' too")
parser.add_argument(
	"-r","--region",
	nargs="*",
	dest="pregion",
	metavar="region name string",
	default=["us-east-1"],
	help="String fragment of the region(s) you want to check for resources.")
parser.add_argument(
    '-d', '--debug',
    help="Print lots of debugging statements",
    action="store_const",
	dest="loglevel",
	const=logging.INFO,
    default=logging.CRITICAL)
parser.add_argument(
    '-v', '--verbose',
    help="Be verbose",
    action="store_const",
	dest="loglevel",
	const=logging.WARNING)
args = parser.parse_args()

pProfile=args.pProfile
pRegionList=args.pregion
pstackfrag=args.pstackfrag
pstatus=args.pstatus
verbose=args.loglevel
logging.basicConfig(level=args.loglevel)

SkipProfiles=["default","Shared-Fid"]
ChildAccounts=Inventory_Modules.find_child_accounts2(pProfile)

NumStacksFound=0
##########################
ERASE_LINE = '\x1b[2K'

print()
fmt='%-20s %-15s %-15s %-50s'
print(fmt % ("Account","Region","Status","StackSet Name"))
print(fmt % ("-------","------","------","-------------"))
RegionList=Inventory_Modules.get_ec2_regions(pRegionList)

sts_session = boto3.Session(profile_name=pProfile)
sts_client = sts_session.client('sts')
for account in ChildAccounts:
	role_arn = "arn:aws:iam::{}:role/AWSCloudFormationStackSetExecutionRole".format(account['AccountId'])
	logging.info("Role ARN: %s" % role_arn)
	try:
		account_credentials = sts_client.assume_role(
			RoleArn=role_arn,
			RoleSessionName="Find-StackSets")['Credentials']
	except ClientError as my_Error:
		if str(my_Error).find("AuthFailure") > 0:
			print(profile+": Authorization Failure for account {}".format(account['AccountId']))
	for region in RegionList:
		try:
			StackSets = None
			print(ERASE_LINE,Fore.RED+"Checking Account: ",account['AccountId'],"Region: ",region+Fore.RESET,end="\r")
			StackSets=Inventory_Modules.find_stacksets2(account_credentials,region,account['AccountId'],pstackfrag)
			logging.warning("Account: %s | Region: %s | Found %s Stacksets", account['AccountId'], region, len(StackSets))
			if not StackSets == []:
				print(ERASE_LINE,Fore.RED+"Account: ",account['AccountId'],"Region: ",region,"Found",len(StackSets),"Stacksets"+Fore.RESET,end="\r")
			for y in range(len(StackSets)):
				StackName=StackSets[y]['StackSetName']
				StackStatus=StackSets[y]['Status']
				print(fmt % (account['AccountId'],region,StackStatus,StackName))
				NumStacksFound += 1
		except ClientError as my_Error:
			if str(my_Error).find("AuthFailure") > 0:
				print(account['AccountId']+": Authorization Failure")
print(ERASE_LINE)
print(Fore.RED+"Found",NumStacksFound,"Stacksets across",len(ChildAccounts),"accounts across",len(RegionList),"regions"+Fore.RESET)
print()
