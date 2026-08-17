"""Isolated live verification for the vision document parser adapter."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, "src")

from interviewer_domain.adapters.integrations import SyncOpenRouterHTTPTransport
from interviewer_domain.capabilities.contracts import ProviderError
from interviewer_domain.documents import VisionDocumentParser
from interviewer_domain.models import DocumentSource
from interviewer_domain.phase16_rehearsal import load_dotenv


class LiveVisionDocumentParserTests(unittest.TestCase):
    """Verify one real PDF parse without running the full interview rehearsal."""

    def test_demo_resume_is_parsed_by_selected_vision_model(self) -> None:
        """Send the demo resume to the configured vision model and validate chunks."""
        environ = load_dotenv(Path(".env"), os.environ)
        api_key = environ.get("LLM_API_KEY", "")
        model = environ.get("DOCUMENT_LLM_MODEL", "").strip()
        fixture = Path(environ.get("PHASE16_RESUME_FIXTURE", "tests/demo_resume.pdf"))
        if not api_key or not model:
            self.skipTest("LLM_API_KEY and DOCUMENT_LLM_MODEL are required")
        self.assertTrue(fixture.is_file(), f"missing resume fixture: {fixture}")

        parser = VisionDocumentParser(
            SyncOpenRouterHTTPTransport(timeout=60.0),
            api_key,
            model,
        )
        try:
            chunks = parser.parse(fixture.read_bytes(), "application/pdf", "resume")
        except ProviderError as error:
            self.fail(
                "vision adapter failed with "
                f"code={error.code.value}, retryable={error.retryable}: {error}"
            )

        self.assertTrue(chunks, "vision parser returned no document chunks")
        self.assertTrue(all(chunk.source is DocumentSource.RESUME for chunk in chunks))
        self.assertTrue(parser.last_fields, "vision parser returned no structured fields")
        print(
            "[DOC17-LIVE] vision-document-live-ok "
            f"model={model} chunks={len(chunks)} fields={len(parser.last_fields)}"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
