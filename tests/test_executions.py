import unittest
from unittest.mock import MagicMock, patch

from rundeck_mcp.models import (
    Execution,
    ExecutionOutput,
    ExecutionQuery,
    ListResponseModel,
    LogEntry,
)
from rundeck_mcp.tools.executions import get_execution, get_execution_output, list_executions


class TestExecutionModels(unittest.TestCase):
    """Tests for execution-related Pydantic models."""

    def test_execution_query_to_params_minimal(self):
        """Test ExecutionQuery with minimal fields."""
        query = ExecutionQuery(project="myproject")
        params = query.to_params()
        self.assertEqual(params["max"], 20)
        self.assertEqual(params["offset"], 0)

    def test_execution_query_to_params_full(self):
        """Test ExecutionQuery with all fields populated."""
        query = ExecutionQuery(
            project="myproject",
            status="failed",
            user="admin",
            recent_filter="1h",
            limit=50,
            offset=10,
        )
        params = query.to_params()
        self.assertEqual(params["statusFilter"], "failed")
        self.assertEqual(params["userFilter"], "admin")
        self.assertEqual(params["recentFilter"], "1h")
        self.assertEqual(params["max"], 50)
        self.assertEqual(params["offset"], 10)

    def test_execution_date_parsing_dict(self):
        """Test Execution parses date from dict format."""
        data = {
            "id": 123,
            "status": "succeeded",
            "project": "myproject",
            "user": "admin",
            "date-started": {"unixtime": 1700000000000, "date": "2023-11-14T00:00:00Z"},
            "date-ended": {"unixtime": 1700000045000, "date": "2023-11-14T00:00:45Z"},
        }
        execution = Execution.model_validate(data)
        self.assertIsNotNone(execution.date_started)
        self.assertIsNotNone(execution.date_ended)

    def test_execution_duration_seconds(self):
        """Test Execution.duration_seconds computed field."""
        execution = Execution(
            id=123,
            status="succeeded",
            project="myproject",
            user="admin",
        )
        # With alias fields, we need to set them via model_validate
        execution_data = {
            "id": 123,
            "status": "succeeded",
            "project": "myproject",
            "user": "admin",
            "date-started": {"unixtime": 1700000000000},
            "date-ended": {"unixtime": 1700000045000},
        }
        execution = Execution.model_validate(execution_data)
        self.assertIsNotNone(execution.duration_seconds)
        self.assertAlmostEqual(execution.duration_seconds, 45.0, places=0)

    def test_execution_summary(self):
        """Test Execution.execution_summary computed field."""
        execution = Execution(
            id=123,
            status="succeeded",
            project="myproject",
            user="admin",
            argstring="-version 1.0",
        )
        summary = execution.execution_summary
        self.assertIn("#123", summary)
        self.assertIn("SUCCEEDED", summary)
        self.assertIn("admin", summary)

    def test_log_entry_model(self):
        """Test LogEntry model parses correctly."""
        entry = LogEntry(
            time="12:00:00",
            level="ERROR",
            log="Something went wrong",
            node="server1",
            step="1",
        )
        self.assertEqual(entry.level, "ERROR")
        self.assertEqual(entry.log, "Something went wrong")

    def test_execution_output_summary(self):
        """Test ExecutionOutput.output_summary computed field."""
        output = ExecutionOutput(
            id=123,
            completed=True,
            entries=[
                LogEntry(log="Line 1", level="NORMAL"),
                LogEntry(log="Line 2", level="NORMAL"),
            ],
        )
        summary = output.output_summary
        self.assertIn("COMPLETE", summary)
        self.assertIn("2", summary)


class TestExecutionTools(unittest.TestCase):
    """Tests for execution tool functions."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.sample_execution_data = {
            "id": 12345,
            "href": "/api/44/execution/12345",
            "permalink": "/project/myproject/execution/show/12345",
            "status": "succeeded",
            "project": "myproject",
            "user": "admin",
            "date-started": {"unixtime": 1700000000000},
            "date-ended": {"unixtime": 1700000045000},
            "argstring": "-version 1.0 -env prod",
            "job": {
                "id": "abc-123",
                "name": "Deploy",
                "group": "deploy",
                "project": "myproject",
            },
            "successfulNodes": ["server1", "server2"],
        }

        cls.sample_executions_response = {
            "executions": [
                {
                    "id": 12345,
                    "status": "succeeded",
                    "project": "myproject",
                    "user": "admin",
                },
                {
                    "id": 12344,
                    "status": "failed",
                    "project": "myproject",
                    "user": "admin",
                },
            ]
        }

        cls.sample_output_response = {
            "id": 12345,
            "offset": 1024,
            "completed": True,
            "execCompleted": True,
            "hasMoreOutput": False,
            "execState": "succeeded",
            "execDuration": 45000,
            "percentLoaded": 100.0,
            "totalSize": 2048,
            "entries": [
                {"time": "12:00:00", "level": "NORMAL", "log": "Starting deployment..."},
                {"time": "12:00:30", "level": "NORMAL", "log": "Deployment complete."},
            ],
        }

    @patch("rundeck_mcp.tools.executions.get_client")
    def test_list_executions_by_project(self, mock_get_client):
        """Test list_executions filters by project."""
        mock_client = MagicMock()
        mock_client.get.return_value = self.sample_executions_response
        mock_get_client.return_value = mock_client

        query = ExecutionQuery(project="myproject")
        result = list_executions(query)

        self.assertIsInstance(result, ListResponseModel)
        self.assertEqual(len(result.response), 2)
        mock_client.get.assert_called_with(
            "/project/myproject/executions",
            params={"max": 20, "offset": 0},
        )

    @patch("rundeck_mcp.tools.executions.get_client")
    def test_list_executions_by_job(self, mock_get_client):
        """Test list_executions filters by job_id."""
        mock_client = MagicMock()
        mock_client.get.return_value = self.sample_executions_response
        mock_get_client.return_value = mock_client

        query = ExecutionQuery(job_id="abc-123")
        list_executions(query)

        mock_client.get.assert_called_with(
            "/job/abc-123/executions",
            params={"max": 20, "offset": 0},
        )

    @patch("rundeck_mcp.tools.executions.get_client")
    def test_list_executions_requires_filter(self, mock_get_client):
        """Test list_executions requires project or job_id."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        query = ExecutionQuery()
        with self.assertRaises(ValueError) as context:
            list_executions(query)
        self.assertIn("Either project or job_id must be provided", str(context.exception))

    @patch("rundeck_mcp.tools.executions.get_client")
    def test_get_execution(self, mock_get_client):
        """Test get_execution returns full execution details."""
        mock_client = MagicMock()
        mock_client.get.return_value = self.sample_execution_data
        mock_get_client.return_value = mock_client

        result = get_execution(12345)

        self.assertIsInstance(result, Execution)
        self.assertEqual(result.id, 12345)
        self.assertEqual(result.status, "succeeded")
        self.assertIsNotNone(result.job)
        self.assertEqual(result.job.name, "Deploy")

    @patch("rundeck_mcp.tools.executions.get_client")
    def test_get_execution_output(self, mock_get_client):
        """Test get_execution_output returns logs."""
        mock_client = MagicMock()
        mock_client.get.return_value = self.sample_output_response
        mock_get_client.return_value = mock_client

        result = get_execution_output(12345)

        self.assertIsInstance(result, ExecutionOutput)
        self.assertEqual(result.id, 12345)
        self.assertTrue(result.completed)
        self.assertEqual(len(result.entries), 2)
        self.assertEqual(result.entries[0].log, "Starting deployment...")

    @patch("rundeck_mcp.tools.executions.get_client")
    def test_get_execution_output_with_params(self, mock_get_client):
        """Test get_execution_output with optional parameters."""
        mock_client = MagicMock()
        mock_client.get.return_value = self.sample_output_response
        mock_get_client.return_value = mock_client

        get_execution_output(12345, last_lines=50, node="server1")

        mock_client.get.assert_called_with(
            "/execution/12345/output/node/server1",
            params={"lastlines": 50},
        )


if __name__ == "__main__":
    unittest.main()
