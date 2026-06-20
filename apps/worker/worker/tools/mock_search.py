"""Mock search tool — deterministic fake results (no network)."""

from typing import Any

from worker.tools.base import Tool


class MockSearchTool(Tool):
    name = "mock_search"
    description = "Return deterministic fake search results for a query."
    input_schema = {"query": "string"}
    output_schema = {"query": "string", "results": "list"}

    def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        query = str(input_data.get("query") or "").strip() or "stagehand"
        results = [
            {
                "title": f"Result {i + 1} for {query}",
                "snippet": f"Deterministic snippet {i + 1} about {query}.",
                "url": f"https://example.com/{query.replace(' ', '-')}/{i + 1}",
            }
            for i in range(3)
        ]
        return {"query": query, "results": results}
