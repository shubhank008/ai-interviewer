"""Focused Phase 16 offline contracts for safe beta composition and lifecycle seams."""

import unittest
from interviewer_domain.configuration import ConfigurationError, RuntimeSettings, validate_beta_composition
from interviewer_domain.models import InterviewMode
from interviewer_domain.adapters.persistence import FirestoreDataStore, InterviewRecord


class Beta16Tests(unittest.TestCase):
    """Exercise production guards without credentials, network, or personal data."""

    def test_beta_composition_rejects_in_memory_and_missing_live_assets(self) -> None:
        """Production must fail closed instead of silently selecting local providers."""
        settings = RuntimeSettings.from_env({"APP_PROFILE": "production", "FIREBASE_PROJECT_ID": "project", "FIRESTORE_DATABASE": "(default)", "STT_PROVIDER": "faster-whisper", "TTS_PROVIDER": "kokoro", "LLM_PROVIDER": "openrouter", "LLM_API_KEY": "fixture-key"})
        with self.assertRaisesRegex(ConfigurationError, "Phase 16 beta composition is incomplete"):
            validate_beta_composition(settings)
        self.assertNotIn("fixture-key", str(settings.diagnostics()))
        print("[BETA16] composition-production-skipped")

    def test_firestore_delete_uses_exact_document_identity(self) -> None:
        """Deleting one interview must not issue a broad owner collection delete."""
        class Backend:
            def __init__(self) -> None:
                self.documents = {}
                self.deleted = []
            def set(self, collection, document_id, value):
                self.documents[(collection, document_id)] = value
            def get(self, collection, document_id):
                return self.documents.get((collection, document_id))
            def list(self, collection, field, value):
                return [v for (name, _), v in self.documents.items() if name == collection and v.get(field) == value]
            def delete_collection_value(self, collection, field, value):
                self.deleted.append(("query", collection, field, value))
            def delete_collection(self, collection):
                self.deleted.append(("collection", collection))
            def delete_document(self, collection, document_id):
                self.deleted.append(("document", collection, document_id))
        backend = Backend()
        store = FirestoreDataStore(backend)
        record = InterviewRecord("owner", InterviewMode.RECRUITER).with_retention()
        store.save_interview(record)
        store.delete_interview("owner", record.id)
        self.assertIn(("document", "interviews", str(record.id)), backend.deleted)
        self.assertNotIn(("query", "interviews", "id", str(record.id)), backend.deleted)
        print("[BETA16] retention-deletion-ok")


if __name__ == "__main__":
    unittest.main()
