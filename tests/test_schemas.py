import unittest
from schemas.context import CONTEXT_SCHEMA
from schemas.strategy import STRATEGY_SCHEMA
from schemas.battle import BATTLE_SCHEMA
from schemas.red_team import RED_TEAM_SCHEMA
from schemas.scenario import SCENARIO_RESULT_SCHEMA, SCENARIO_SETUP_SCHEMA


class SchemaContractTests(unittest.TestCase):
    def test_all_top_level_schemas_are_closed(self):
        for schema in [CONTEXT_SCHEMA, STRATEGY_SCHEMA, BATTLE_SCHEMA, RED_TEAM_SCHEMA, SCENARIO_RESULT_SCHEMA, SCENARIO_SETUP_SCHEMA]:
            self.assertFalse(schema.get("additionalProperties", True))
            self.assertEqual(set(schema["required"]), set(schema["properties"].keys()))


if __name__ == "__main__":
    unittest.main()
