import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSIONS = ROOT / "backend" / "alembic" / "versions"


class DatabaseMigrationContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        migrations = sorted(VERSIONS.glob("*.py"))
        cls.assertTrue = unittest.TestCase().assertTrue
        cls.assertTrue(migrations, "At least one Alembic migration is required")
        cls.migration_text = "\n".join(path.read_text(encoding="utf-8") for path in migrations)

    def test_required_tables_are_created(self):
        for table in [
            "search_requests",
            "products",
            "supplier_contacts",
            "contact_attempts",
            "conversation_messages",
            "agent_tasks",
        ]:
            with self.subTest(table=table):
                self.assertRegex(self.migration_text, rf"create_table\(\s*[\"']{table}[\"']")

    def test_required_check_constraints_are_created(self):
        for constraint in [
            "supplier_contacts_type_check",
            "contact_attempts_channel_check",
            "conversation_messages_direction_check",
            "conversation_messages_status_check",
            "conversation_messages_channel_check",
            "agent_tasks_type_check",
        ]:
            with self.subTest(constraint=constraint):
                self.assertIn(constraint, self.migration_text)

    def test_required_indexes_are_created(self):
        for index in [
            "idx_products_search_request_id",
            "idx_supplier_contacts_product_id",
            "idx_contact_attempts_product_id",
            "idx_conversation_messages_product_id",
            "idx_conversation_messages_contact_attempt_id",
            "idx_agent_tasks_status",
            "idx_search_requests_status",
        ]:
            with self.subTest(index=index):
                self.assertIn(index, self.migration_text)

    def test_products_price_and_currency_are_nullable(self):
        price_match = re.search(r"sa\.Column\([\"']price[\"'].*?nullable=True", self.migration_text, re.S)
        currency_match = re.search(r"sa\.Column\([\"']currency[\"'].*?nullable=True", self.migration_text, re.S)
        self.assertIsNotNone(price_match, "products.price must be nullable")
        self.assertIsNotNone(currency_match, "products.currency must be nullable")

    def test_products_title_and_url_are_required(self):
        title_match = re.search(r"sa\.Column\([\"']title[\"'].*?nullable=False", self.migration_text, re.S)
        url_match = re.search(r"sa\.Column\([\"']product_url[\"'].*?nullable=False", self.migration_text, re.S)
        self.assertIsNotNone(title_match, "products.title must be required")
        self.assertIsNotNone(url_match, "products.product_url must be required")

    def test_search_requests_max_results_is_persisted(self):
        self.assertIn("max_results", self.migration_text)
        max_results_match = re.search(r"sa\.Column\([\"']max_results[\"'].*?nullable=False", self.migration_text, re.S)
        self.assertIsNotNone(max_results_match, "search_requests.max_results must be required")


if __name__ == "__main__":
    unittest.main()
