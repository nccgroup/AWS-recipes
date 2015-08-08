# AWS-recipes

## Python tools

### aws_cloudtrail_enable_all_regions.py

### aws_iam_create_default_groups.py

#### Brief

#### Related blog posts

* http://...

### aws_iam_create_policy.py

### aws_iam_create_user.py

### aws_iam_delete_user.py

If you have the need to delete one -- or more -- IAM users, this tool can help
you do so seamlessly. Provide a list of usernames to be deleted, and removal of
all of their associated resources (_e.g._ access keys, login profile, inline
policies, group memberships, ...) will be taken care of.

    ./aws_iam_delete_user.py --user-name USER_1 USER_2 ... USER_N

### aws_iam_enable_mfa.py

If you haven't configured a virtual MFA device yet, this tool will do it for
you. Run it, scan the QR code displayed in your console, and enter two
consecutive codes to enable MFA for your account.

    ./aws_iam_enable_mfa.py

### aws_iam_rotate_my_key.py

Because credentials rotation is important, and because it is almost always
overlooked by AWS users, iSEC created a tool that does it for you. When you run
this tool, a new access key will be generate and stored in your
_~/aws/.credentials_ file. Your old access key will be deleted and, if you
configured MFA, an STS session using these new credentials will be initialized.

    ./aws_iam_rotate_my_key.py

### aws_iam_sort_users.py

### aws_recipes_configure_iam.py

### aws_recipes_init_sts_session.py

