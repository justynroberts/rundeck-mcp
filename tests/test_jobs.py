import unittest
from unittest.mock import MagicMock, patch

from rundeck_mcp.models import Job, JobOption, JobQuery, JobRunRequest
from rundeck_mcp.tools.jobs import get_job, list_jobs, run_job
from rundeck_mcp.utils import format_job_options_for_display, validate_job_options


class TestJobModels(unittest.TestCase):
    """Tests for job-related Pydantic models."""

    def test_job_query_to_params_minimal(self):
        """Test JobQuery with only required fields."""
        query = JobQuery(project="myproject")
        params = query.to_params()
        self.assertEqual(params, {"max": 1000})

    def test_job_query_to_params_full(self):
        """Test JobQuery with all fields populated."""
        query = JobQuery(
            project="myproject",
            group_path="deploy/prod",
            job_filter="backup",
            scheduled_filter=True,
            tags="critical,daily",
            limit=50,
        )
        params = query.to_params()
        self.assertEqual(params["groupPath"], "deploy/prod")
        self.assertEqual(params["jobFilter"], "backup")
        self.assertEqual(params["scheduledFilter"], True)
        self.assertEqual(params["tags"], "critical,daily")
        self.assertEqual(params["max"], 50)

    def test_job_option_summary_required(self):
        """Test JobOption summary for required option."""
        opt = JobOption(
            name="version",
            required=True,
            description="Version to deploy",
        )
        summary = opt.option_summary
        self.assertIn("'version'", summary)
        self.assertIn("[REQUIRED]", summary)
        self.assertIn("Version to deploy", summary)

    def test_job_option_summary_with_default(self):
        """Test JobOption summary with default value."""
        opt = JobOption(
            name="env",
            value="staging",
            description="Target environment",
        )
        summary = opt.option_summary
        self.assertIn("(default: 'staging')", summary)

    def test_job_option_summary_with_values(self):
        """Test JobOption summary with allowed values."""
        opt = JobOption(
            name="env",
            values=["dev", "staging", "prod"],
        )
        summary = opt.option_summary
        self.assertIn("[allowed:", summary)
        self.assertIn("dev", summary)

    def test_job_required_options(self):
        """Test Job.required_options computed field."""
        job = Job(
            id="abc-123",
            name="Deploy",
            project="myproject",
            options=[
                JobOption(name="version", required=True),
                JobOption(name="env", required=False),
                JobOption(name="replicas", required=True),
            ],
        )
        self.assertEqual(job.required_options, ["version", "replicas"])

    def test_job_run_request_to_body(self):
        """Test JobRunRequest conversion to request body."""
        request = JobRunRequest(
            options={"version": "1.2.3", "env": "prod"},
            log_level="DEBUG",
        )
        body = request.to_request_body()
        self.assertEqual(body["options"], {"version": "1.2.3", "env": "prod"})
        self.assertEqual(body["loglevel"], "DEBUG")


class TestValidateJobOptions(unittest.TestCase):
    """Tests for job option validation logic."""

    def test_validate_no_options_required(self):
        """Test validation when job has no options."""
        is_valid, errors = validate_job_options(None, None)
        self.assertTrue(is_valid)
        self.assertEqual(errors, [])

    def test_validate_provided_when_none_expected(self):
        """Test validation fails when options provided but none expected."""
        is_valid, errors = validate_job_options(None, {"foo": "bar"})
        self.assertFalse(is_valid)
        self.assertIn("Job has no options", errors[0])

    def test_validate_missing_required(self):
        """Test validation fails when required option is missing."""
        job_options = [
            {"name": "version", "required": True},
            {"name": "env", "required": False, "value": "staging"},
        ]
        is_valid, errors = validate_job_options(job_options, {})
        self.assertFalse(is_valid)
        self.assertIn("Required option 'version' is missing", errors[0])

    def test_validate_required_with_default(self):
        """Test required option with default passes without value."""
        job_options = [
            {"name": "version", "required": True, "value": "1.0.0"},
        ]
        is_valid, errors = validate_job_options(job_options, {})
        self.assertTrue(is_valid)

    def test_validate_enforced_values(self):
        """Test validation fails for invalid enforced values."""
        job_options = [
            {"name": "env", "enforced": True, "values": ["dev", "staging", "prod"]},
        ]
        is_valid, errors = validate_job_options(job_options, {"env": "invalid"})
        self.assertFalse(is_valid)
        self.assertIn("not in allowed values", errors[0])

    def test_validate_enforced_values_valid(self):
        """Test validation passes for valid enforced values."""
        job_options = [
            {"name": "env", "enforced": True, "values": ["dev", "staging", "prod"]},
        ]
        is_valid, errors = validate_job_options(job_options, {"env": "prod"})
        self.assertTrue(is_valid)

    def test_validate_unknown_options(self):
        """Test validation warns about unknown options."""
        job_options = [
            {"name": "version"},
        ]
        is_valid, errors = validate_job_options(job_options, {"version": "1.0", "unknown": "value"})
        self.assertFalse(is_valid)
        self.assertIn("Unknown options", errors[0])


class TestFormatJobOptions(unittest.TestCase):
    """Tests for job options display formatting."""

    def test_format_no_options(self):
        """Test formatting when job has no options."""
        result = format_job_options_for_display(None)
        self.assertEqual(result, "This job has no options.")

    def test_format_required_option(self):
        """Test formatting shows required marker."""
        options = [{"name": "version", "required": True}]
        result = format_job_options_for_display(options)
        self.assertIn("[REQUIRED]", result)

    def test_format_default_value(self):
        """Test formatting shows default value."""
        options = [{"name": "env", "value": "staging"}]
        result = format_job_options_for_display(options)
        self.assertIn("(default: 'staging')", result)

    def test_format_allowed_values_enforced(self):
        """Test formatting shows enforced allowed values."""
        options = [{"name": "env", "enforced": True, "values": ["dev", "prod"]}]
        result = format_job_options_for_display(options)
        self.assertIn("must be", result)
        self.assertIn("'dev'", result)

    def test_format_allowed_values_suggested(self):
        """Test formatting shows suggested allowed values."""
        options = [{"name": "env", "enforced": False, "values": ["dev", "prod"]}]
        result = format_job_options_for_display(options)
        self.assertIn("suggested", result)


class TestJobTools(unittest.TestCase):
    """Tests for job tool functions."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.sample_job_data = {
            "id": "abc-123-def",
            "name": "Deploy Application",
            "group": "deploy/prod",
            "project": "myproject",
            "description": "Deploy the application to production",
            "href": "/api/44/job/abc-123-def",
            "permalink": "/project/myproject/job/show/abc-123-def",
            "scheduled": True,
            "scheduleEnabled": True,
            "enabled": True,
            "averageDuration": 45000,
            "options": [
                {
                    "name": "version",
                    "required": True,
                    "description": "Version to deploy",
                },
                {
                    "name": "env",
                    "value": "staging",
                    "values": ["dev", "staging", "prod"],
                    "enforced": True,
                },
            ],
        }

        cls.sample_jobs_list = [
            {
                "id": "abc-123",
                "name": "Job 1",
                "project": "myproject",
            },
            {
                "id": "def-456",
                "name": "Job 2",
                "project": "myproject",
            },
        ]

    @patch("rundeck_mcp.tools.jobs.get_client")
    def test_list_jobs(self, mock_get_client):
        """Test list_jobs returns markdown table."""
        mock_client = MagicMock()
        mock_client.get.return_value = self.sample_jobs_list
        mock_get_client.return_value = mock_client

        query = JobQuery(project="myproject")
        result = list_jobs(query)

        self.assertIsInstance(result, str)
        self.assertIn("| # | Name | Group | Job ID |", result)
        self.assertIn("| 1 | Job 1 |", result)
        self.assertIn("| 2 | Job 2 |", result)

    @patch("rundeck_mcp.tools.jobs.get_client")
    def test_get_job(self, mock_get_client):
        """Test get_job returns formatted job details with options table."""
        mock_client = MagicMock()
        mock_client.get.return_value = self.sample_job_data
        mock_get_client.return_value = mock_client

        result = get_job("abc-123-def")

        self.assertIsInstance(result, str)
        self.assertIn("## Deploy Application", result)
        self.assertIn("abc-123-def", result)
        self.assertIn("### Job Options", result)
        self.assertIn("| # | Option | Required | Default | Allowed Values |", result)
        self.assertIn("**version**", result)
        self.assertIn("🔴 Yes", result)  # Required marker

    @patch("rundeck_mcp.tools.jobs.get_client")
    def test_run_job_validates_options(self, mock_get_client):
        """Test run_job returns formatted error for missing required options."""
        mock_client = MagicMock()
        mock_client.get.return_value = self.sample_job_data
        mock_get_client.return_value = mock_client

        # Missing required 'version' option
        result = run_job("abc-123-def", JobRunRequest(options={"env": "prod"}))

        self.assertIsInstance(result, str)
        self.assertIn("❌ Cannot run", result)
        self.assertIn("Required option 'version' is missing", result)
        self.assertIn("| Option | Required | Default | Allowed Values | Your Value |", result)
        self.assertIn("**version**", result)

    @patch("rundeck_mcp.tools.jobs.get_client")
    def test_run_job_validates_enforced_values(self, mock_get_client):
        """Test run_job returns formatted error for invalid enforced values."""
        mock_client = MagicMock()
        mock_client.get.return_value = self.sample_job_data
        mock_get_client.return_value = mock_client

        # Invalid value for enforced 'env' option
        result = run_job("abc-123-def", JobRunRequest(options={"version": "1.0", "env": "invalid"}))

        self.assertIsInstance(result, str)
        self.assertIn("❌ Cannot run", result)
        self.assertIn("not in allowed values", result)

    @patch("rundeck_mcp.tools.jobs.get_client")
    def test_run_job_success(self, mock_get_client):
        """Test run_job executes successfully with valid options."""
        mock_client = MagicMock()
        mock_client.get.return_value = self.sample_job_data
        mock_client.post.return_value = {
            "id": 12345,
            "href": "/api/44/execution/12345",
            "permalink": "/project/myproject/execution/show/12345",
            "status": "running",
            "project": "myproject",
            "user": "admin",
            "job": {
                "id": "abc-123-def",
                "name": "Deploy Application",
                "project": "myproject",
            },
        }
        mock_get_client.return_value = mock_client

        result = run_job("abc-123-def", JobRunRequest(options={"version": "1.0", "env": "prod"}))

        self.assertIsInstance(result, str)
        self.assertIn("✅ Job Started", result)
        self.assertIn("Deploy Application", result)
        self.assertIn("12345", result)
        self.assertIn("running", result)
        mock_client.post.assert_called_once()


if __name__ == "__main__":
    unittest.main()
