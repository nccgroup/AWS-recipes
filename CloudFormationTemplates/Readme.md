# AWS Recipes CloudFormation Templates

## Naming convention

***(HighLevelFunctionality)-(AccountType)-(ID)-(Name)-(Deployment).(yml|json)***

* HighLevelFunctionality : The functionality this template is part of
* AccountType : The type of account the template should be deployed in (master or target)
   * Master : Deploy as a stack
   * Target : Deploy as a stack set
* ID : Integer for each category, higher IDs may depend on lower ones
* Name : Additional description of the functionality provided by the template
* Deployment : The type of resources created by the template
   * Global : One stack per account
   * Region : One stack per region
