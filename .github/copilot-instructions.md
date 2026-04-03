For every completed code change in this workspace:

- Bump the module version in __manifest__.py by incrementing the last numeric segment unless the user asks for a different versioning change.
- Validate the affected files before finishing.
- Commit the completed changes with a concise message.
- Push the commit to the default remote branch unless the user says not to.
- Trigger the Dokploy deploy webhook after a successful push when it is available from a local secret or user-level instruction.
- Never commit raw webhook URLs or other secrets into repository-tracked files.
- If commit or push is blocked by authentication, branch protection, or conflicts, report the blocker immediately.