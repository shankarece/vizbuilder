"""
Tests for visual_types.py: alias resolution and cross-consistency of the
supported types / roles / role-aliases / default-sizes tables.

Run from the repo root (standard library only):
    python -m unittest discover tests
"""

import os
import sys
import unittest

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_DIR)

from visual_types import (  # noqa: E402
    DEFAULT_SIZES,
    MEASURE_ROLES,
    ROLE_ALIASES,
    SUPPORTED_VISUAL_TYPES,
    VISUAL_DATA_ROLES,
    VISUAL_TYPE_ALIASES,
    resolve_visual_type,
)


class ResolveVisualTypeTest(unittest.TestCase):

    def test_canonical_name_passes_through(self):
        for vtype in SUPPORTED_VISUAL_TYPES:
            with self.subTest(vtype=vtype):
                self.assertEqual(resolve_visual_type(vtype), vtype)

    def test_alias_resolves_to_canonical(self):
        self.assertEqual(resolve_visual_type("bar"), "barChart")
        self.assertEqual(resolve_visual_type("pie"), "donutChart")
        self.assertEqual(resolve_visual_type("combo"), "lineStackedColumnComboChart")
        self.assertEqual(resolve_visual_type("matrix"), "pivotTable")

    def test_every_alias_resolves(self):
        for alias, canonical in VISUAL_TYPE_ALIASES.items():
            with self.subTest(alias=alias):
                self.assertEqual(resolve_visual_type(alias), canonical)

    def test_case_sensitive(self):
        # Neither the canonical name nor the alias table matches on case.
        with self.assertRaises(ValueError):
            resolve_visual_type("Bar")
        with self.assertRaises(ValueError):
            resolve_visual_type("BARCHART")

    def test_unknown_type_raises_with_helpful_message(self):
        with self.assertRaises(ValueError) as ctx:
            resolve_visual_type("not_a_real_visual")
        message = str(ctx.exception)
        self.assertIn("not_a_real_visual", message)
        self.assertIn("bar", message)  # suggests an example alias


class MetadataConsistencyTest(unittest.TestCase):
    """Every table in visual_types.py must agree with the others."""

    def test_every_alias_targets_a_supported_type(self):
        for alias, canonical in VISUAL_TYPE_ALIASES.items():
            with self.subTest(alias=alias):
                self.assertIn(canonical, SUPPORTED_VISUAL_TYPES)

    def test_every_supported_type_has_data_roles_entry(self):
        for vtype in SUPPORTED_VISUAL_TYPES:
            with self.subTest(vtype=vtype):
                self.assertIn(vtype, VISUAL_DATA_ROLES)

    def test_every_supported_type_has_default_size(self):
        for vtype in SUPPORTED_VISUAL_TYPES:
            with self.subTest(vtype=vtype):
                self.assertIn(vtype, DEFAULT_SIZES)
                w, h = DEFAULT_SIZES[vtype]
                self.assertGreater(w, 0)
                self.assertGreater(h, 0)

    def test_every_supported_type_has_role_aliases_entry(self):
        for vtype in SUPPORTED_VISUAL_TYPES:
            with self.subTest(vtype=vtype):
                self.assertIn(vtype, ROLE_ALIASES)

    def test_every_role_alias_targets_a_declared_role(self):
        for vtype, aliases in ROLE_ALIASES.items():
            declared = set(VISUAL_DATA_ROLES.get(vtype, []))
            for user_role, pbir_role in aliases.items():
                with self.subTest(vtype=vtype, user_role=user_role):
                    self.assertIn(pbir_role, declared,
                                  f"{vtype}.{user_role} -> {pbir_role} not in {declared}")

    def test_measure_roles_are_a_subset_of_declared_roles(self):
        all_declared_roles = {role for roles in VISUAL_DATA_ROLES.values() for role in roles}
        self.assertTrue(MEASURE_ROLES <= all_declared_roles)


if __name__ == "__main__":
    unittest.main()
