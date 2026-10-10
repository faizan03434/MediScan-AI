import unittest

from training.clean_medical_intake import select_clean


class MedicalCleaningTests(unittest.TestCase):
    def test_conflicting_folder_labels_are_never_resolved_by_sort_order(self):
        rows = [{'path': 'a', 'pixel_sha256': 'same', 'label': 'Acne'},
                {'path': 'b', 'pixel_sha256': 'same', 'label': 'Eczema'}]
        accepted, quarantine, redundant = select_clean(rows, {}, [])
        self.assertEqual(accepted, [])
        self.assertEqual(len(quarantine), 2)
        self.assertEqual(redundant, [])

    def test_conflicting_record_excludes_whole_pixel_group(self):
        rows = [{'path': 'a', 'pixel_sha256': 'same'}, {'path': 'b', 'pixel_sha256': 'same'},
                {'path': 'c', 'pixel_sha256': 'clean'}]
        accepted, quarantine, redundant = select_clean(rows, {'b': {'conflicting_hb'}}, [])
        self.assertEqual([row['path'] for row in accepted], ['c'])
        self.assertEqual({row['path'] for row in quarantine}, {'a', 'b'})
        self.assertEqual(redundant, [])
        self.assertEqual(rows[0], {'path': 'a', 'pixel_sha256': 'same'})

    def test_near_candidates_quarantine_all_copies_without_guessing_labels(self):
        rows = [{'path': 'a', 'pixel_sha256': 'one'}, {'path': 'b', 'pixel_sha256': 'one'},
                {'path': 'c', 'pixel_sha256': 'two'}]
        accepted, quarantine, _ = select_clean(rows, {}, [{'left': 'a', 'right': 'c'}])
        self.assertEqual(accepted, [])
        self.assertEqual(len(quarantine), 3)

    def test_duplicate_choice_is_deterministic_and_missing_review_path_fails(self):
        rows = [{'path': 'b', 'pixel_sha256': 'one'}, {'path': 'a', 'pixel_sha256': 'one'}]
        accepted, quarantine, redundant = select_clean(rows, {}, [])
        self.assertEqual(accepted[0]['path'], 'a')
        self.assertEqual(redundant, [{'path': 'b', 'representative': 'a'}])
        self.assertEqual(quarantine, [])
        with self.assertRaises(KeyError):
            select_clean(rows, {}, [{'left': 'a', 'right': 'missing'}])
