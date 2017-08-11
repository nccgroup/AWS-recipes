# AWS Recipes CloudFormation Templates

## Naming convention

***(HighLevelFunctionality)-(AccountType)-(ID)-(Name)-(Deployment).(yml|json)***

* HighLevelFunctionality : The functionality this template is part of
* AccountType : The type of account the template should be deployed in (master or target)
   * master : Deploy as a stack
   * target : Deploy as a stack set
* ID : Integer for each category, higher IDs may depend on lower ones
* Name : Additional description of the functionality provided by the template
* Deployment : The type of resources created by the template
   * global : One stack per account
   * region : One stack per region
