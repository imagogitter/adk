# CI/CD Setup Guide

## Required GitHub Secrets

Configure these secrets in your GitHub repository settings (Settings > Secrets and variables > Actions):

### Authentication
- `DOCKER_USERNAME`: Username for container registry
- `DOCKER_PASSWORD`: Password/token for container registry
- `GH_TOKEN`: GitHub personal access token with packages:write permission

### Deployment Keys
- `STAGING_SSH_KEY`: SSH private key for staging server access
- `PROD_SSH_KEY`: SSH private key for production server access

### Environment Variables
- `STAGING_HOST`: Staging server hostname/IP
- `PROD_HOST`: Production server hostname/IP
- `DB_CONNECTION_STRING`: Database connection string
- `API_KEY`: API authentication key

## Environment Configuration

### Configure GitHub Environments

1. **Staging Environment**
   - Name: `staging`
   - No protection rules (auto-deploys)
   - Environment variables:
     * `ENVIRONMENT=staging`
     * `DEBUG=true`
     * `LOG_LEVEL=debug`

2. **Production Environment**
   - Name: `production`
   - Protection rules:
     * Required reviewers (add team leads)
     * Wait timer: 10 minutes
     * Branch restrictions: only `main`
   - Environment variables:
     * `ENVIRONMENT=production`
     * `DEBUG=false`
     * `LOG_LEVEL=info`

## Branch Protection Rules

Configure in repository settings (Settings > Branches):

1. **Main Branch Protection**
   - Require a pull request before merging
   - Require approvals (minimum 1)
   - Require status checks to pass:
     * CI workflow
     * All tests passing
     * Code coverage threshold met
   - Require conversation resolution
   - Include administrators
   - Allow force pushes: disabled
   - Allow deletions: disabled

2. **Release Branch Pattern (`release/*`)**
   - Require a pull request before merging
   - Require approvals (minimum 2)
   - Require status checks to pass
   - Restrict who can push: devops team only

## Container Registry Setup

1. Enable GitHub Container Registry for your organization/repository
2. Configure visibility settings
3. Set up authentication for CI/CD pipeline
4. Configure retention policies for old images

## Monitoring and Notifications

1. **Enable notifications for:**
   - Workflow failures
   - Deployment status
   - Security alerts
   - Pull request reviews

2. **Configure status checks:**
   - Required checks must pass
   - Branches must be up to date

## Troubleshooting

Common issues and solutions:

1. **Workflow Failures**
   - Check Actions tab for detailed logs
   - Verify secrets are properly configured
   - Ensure environment variables are set

2. **Deployment Issues**
   - Verify SSH keys and permissions
   - Check network access and firewall rules
   - Validate Docker registry access

3. **Code Quality Checks**
   - Run pre-commit hooks locally
   - Update dependencies if needed
   - Check formatting and linting rules

## Security Measures

1. **Automated Security Scanning**
  - Dependency scanning (safety):
    * Checks for known vulnerabilities
    * Runs on every commit and daily
    * Blocks PR if vulnerabilities found

  - Static code analysis (bandit):
    * Python-specific security checks
    * Configured in pyproject.toml
    * Pre-commit hook integration

  - Container scanning (Trivy):
    * Scans built images for vulnerabilities
    * Provides SARIF reports
    * Runs during CI pipeline

  - Advanced code analysis (CodeQL):
    * Deep semantic code analysis
    * Weekly scheduled scans
    * Security query suite enabled

2. **Security Best Practices**
  - Secrets management:
    * All sensitive data in GitHub Secrets
    * Environment-specific variables
    * No hardcoded credentials

  - Access control:
    * Branch protection rules
    * Required code reviews
    * Limited admin access

  - Container security:
    * Minimal base images
    * Regular base updates
    * Vulnerability monitoring

3. **Security Monitoring**
  - Daily automated scans
  - Vulnerability notifications
  - Dependency update alerts
  - Security patch automation
