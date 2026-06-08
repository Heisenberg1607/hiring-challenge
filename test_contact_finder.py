import unittest

from contact_finder import SUPPRESSED, compute_confidence, process_company


class ComputeConfidenceTests(unittest.TestCase):
    def test_full_corroboration_scores_high(self):
        registry = {"name": "Jane Doe", "role": "Owner"}
        listing = {"name": "Jane Smith"}
        enrichment = {"email": "jane@example.com", "provider_confidence": 88}

        score = compute_confidence(
            registry=registry,
            listing=listing,
            enrichment=enrichment,
            contact_name="Jane Doe",
            contact_role="Owner",
        )

        self.assertGreaterEqual(score, 70)

    def test_single_source_is_capped_below_threshold(self):
        score = compute_confidence(
            registry=None,
            listing=None,
            enrichment={"email": "only@source.com", "provider_confidence": 95},
            contact_name="Only Source",
            contact_role="",
        )

        self.assertLessEqual(score, 58)

    def test_no_named_person_is_capped(self):
        score = compute_confidence(
            registry=None,
            listing=None,
            enrichment={"phone": "555-123-4567", "provider_confidence": 95},
            contact_name="",
            contact_role="",
        )

        self.assertLessEqual(score, 45)

    def test_provider_confidence_is_not_adopted_as_final_score(self):
        score = compute_confidence(
            registry=None,
            listing=None,
            enrichment={"email": "solo@example.com", "provider_confidence": 90},
            contact_name="Solo Contact",
            contact_role="",
        )

        self.assertLessEqual(score, 58)
        self.assertLess(score, 70)


class ProcessCompanyTests(unittest.TestCase):
    def test_cannot_verify_returns_empty_row_for_missing_company(self):
        result = process_company(
            {"company_name": "Missing Co", "mailing_address": "N/A"},
            mock_data={},
        )

        self.assertTrue(result["needs_human_review"])
        self.assertEqual(result["contact_email_or_phone"], "")
        self.assertEqual(result["confidence_score"], 0)

    def test_suppressed_company_returns_empty_review_row(self):
        company_name = "Suppressed Co"
        mock_data = {
            company_name: {
                "registry": {"name": "Pat Lee", "role": "Owner"},
                "enrichment": {"email": "pat@suppressed.co", "provider_confidence": 95},
            }
        }

        SUPPRESSED.add(company_name)
        try:
            result = process_company(
                {"company_name": company_name, "mailing_address": "N/A"},
                mock_data=mock_data,
            )
        finally:
            SUPPRESSED.discard(company_name)

        self.assertTrue(result["needs_human_review"])
        self.assertEqual(result["contact_name"], "")
        self.assertEqual(result["contact_email_or_phone"], "")
        self.assertEqual(result["confidence_score"], 0)

    def test_found_person_without_reachable_handle_needs_review(self):
        mock_data = {
            "No Handle LLC": {
                "registry": {
                    "name": "Alex Rivera",
                    "role": "Owner",
                    "source_url": "https://registry.example/no-handle",
                }
            }
        }

        result = process_company(
            {"company_name": "No Handle LLC", "mailing_address": "N/A"},
            mock_data=mock_data,
        )

        self.assertEqual(result["contact_name"], "Alex Rivera")
        self.assertEqual(result["contact_email_or_phone"], "")
        self.assertTrue(result["needs_human_review"])

    def test_clean_auto_accept_with_registry_and_enrichment_email(self):
        mock_data = {
            "Auto Accept Inc": {
                "registry": {
                    "name": "Jordan Kim",
                    "role": "Owner",
                    "source_url": "https://registry.example/auto",
                },
                "listing": {
                    "name": "Jordan Patel",
                    "source_url": "https://listing.example/auto",
                },
                "enrichment": {
                    "email": "jordan@auto-accept.example",
                    "provider_confidence": 82,
                    "source_url": "https://enrichment.example/auto",
                },
            }
        }

        result = process_company(
            {"company_name": "Auto Accept Inc", "mailing_address": "N/A"},
            mock_data=mock_data,
        )

        self.assertFalse(result["needs_human_review"])
        self.assertNotEqual(result["contact_email_or_phone"], "")


if __name__ == "__main__":
    unittest.main()
