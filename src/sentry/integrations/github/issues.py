from __future__ import absolute_import

from sentry.integrations.exceptions import ApiError, IntegrationError
from sentry.integrations.issues import IssueSyncMixin


class GitHubIssueSync(IssueSyncMixin):

    def get_create_issue_config(self, group, **kwargs):
        fields = super(GitHubIssueSync, self).get_create_issue_config(group, **kwargs)
        try:
            repos = self.get_repositories()
        except ApiError:
            repo_choices = [(' ', ' ')]
        else:
            repo_choices = [(repo['full_name'], repo['full_name']) for repo in repos]

        params = kwargs.get('params', {})
        repo = params.get('repo')
        default_repo = repo or repo_choices[0][0]
        assignees = self.get_allowed_assignees(default_repo)

        return [
            {
                'name': 'repo',
                'label': 'GitHub Repository',
                'type': 'select',
                'default': default_repo,
                'choices': repo_choices,
                'updatesForm': True,
            }
        ] + fields + [
            {
                'name': 'assignee',
                'label': 'Assignee',
                'default': '',
                'type': 'select',
                'required': False,
                'choices': assignees,
            }
        ]

    def create_issue(self, data, **kwargs):
        client = self.get_client()

        repo = data.get('repo')

        if not repo:
            raise IntegrationError('repo kwarg must be provided')

        try:
            issue = client.create_issue(
                repo=repo,
                data={
                    'title': data['title'],
                    'body': data['description'],
                    'assignee': data.get('assignee'),
                })
        except ApiError as e:
            raise IntegrationError(self.message_from_error(e))

        return {
            'key': issue['number'],
            'title': issue['title'],
            'description': issue['body'],
            'repo': repo,
        }

    def get_link_issue_config(self, group, **kwargs):
        try:
            repos = self.get_repositories()
        except ApiError:
            repo_choices = [(' ', ' ')]
        else:
            repo_choices = [(repo['full_name'], repo['full_name']) for repo in repos]

        params = kwargs.get('params', {})
        repo = params.get('repo')
        default_repo = repo or repo_choices[0][0]
        issues = self.get_repo_issues(default_repo)

        return [
            {
                'name': 'repo',
                'label': 'GitHub Repository',
                'type': 'select',
                'default': default_repo,
                'choices': repo_choices,
                'updatesForm': True,
            },
            {
                'name': 'externalIssue',
                'label': 'Issue',
                'default': '',
                'type': 'select',
                'choices': issues,

            },
            {
                'name': 'comment',
                'label': 'Comment',
                'default': '',
                'type': 'textarea',
                'required': False,
                'help': ('Leave blank if you don\'t want to '
                         'add a comment to the GitHub issue.'),
            }
        ]

    def get_issue(self, data):
        repo = data.get('repo')
        issue_num = data.get('externalIssue')
        client = self.get_client()

        if not repo:
            raise IntegrationError('repo must be provided')

        if not issue_num:
            raise IntegrationError('issue must be provided')

        try:
            issue = client.get_issue(repo, issue_num)
        except ApiError as e:
            raise IntegrationError(self.message_from_error(e))

        comment = data.get('comment')
        if comment:
            try:
                client.create_comment(
                    repo=repo,
                    issue_id=issue['number'],
                    data={
                        'body': comment,
                    },
                )
            except ApiError as e:
                raise IntegrationError(self.message_from_error(e))

        return {
            'key': issue['number'],
            'title': issue['title'],
            'description': issue['body'],
            'repo': repo,
        }

    def get_allowed_assignees(self, repo):
        client = self.get_client()
        try:
            response = client.get_assignees(repo)
        except Exception as e:
            self.raise_error(e)

        users = tuple((u['login'], u['login']) for u in response)

        return (('', 'Unassigned'), ) + users

    def get_repo_issues(self, repo):
        client = self.get_client()
        try:
            response = client.get_issues(repo)
        except Exception as e:
            self.raise_error(e)

        issues = tuple((i['number'], 'GH-{} {}'.format(i['number'], i['title'])) for i in response)

        return issues