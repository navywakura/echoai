"""Plan C1 sealed campaign: ordering, binding and tamper detection."""
import tempfile
import unittest
from pathlib import Path

from echoai.nexus0.sim3.canon import Sim3Error, canonical_bytes
from echoai.nexus0.sim3.seal import REHEARSAL_SECRET, open_once, read_seal
from echoai.nexus0.transfer3 import campaign_c1, custodian_c1
from echoai.nexus0.transfer3.custody import validate_notice, verify_reveal

SALTS = {'B': bytes([2])*32, 'C': bytes([3])*32}
OTHER = bytes([7])*32


def protocol_bytes(kind='rehearsal', excluded=()):
    return canonical_bytes(dict(version='c1-campaign-test', kind=kind, counts={'B': 2, 'C': 2},
                                excluded_shapes=sorted(excluded),
                                examiner_manifest=campaign_c1.manifest()))


def notice_for(protocol, kind='rehearsal', secret=REHEARSAL_SECRET):
    return custodian_c1.commit(secret, SALTS, protocol, kind=kind,
                               custodian='test fixture', publication_reference='test fixture')


class Custodian(unittest.TestCase):
    def test_rooms_are_a_deterministic_function_of_the_secret(self):
        a = custodian_c1.generate_split(REHEARSAL_SECRET, 'B', 3, [])
        self.assertEqual(a, custodian_c1.generate_split(REHEARSAL_SECRET, 'B', 3, []))
        self.assertNotEqual(a, custodian_c1.generate_split(OTHER, 'B', 3, []))

    def test_splits_differ_and_respect_exclusion(self):
        b = custodian_c1.generate_split(REHEARSAL_SECRET, 'B', 3, [])
        c = custodian_c1.generate_split(REHEARSAL_SECRET, 'C', 3, [r['shape'] for r in b])
        self.assertTrue({r['shape'] for r in b}.isdisjoint({r['shape'] for r in c}))

    def test_the_public_notice_carries_no_seed_and_no_secret(self):
        notice, rooms = notice_for(protocol_bytes())
        validate_notice(notice)
        text = canonical_bytes(notice).decode()
        self.assertNotIn(REHEARSAL_SECRET.hex(), text)
        for split in custodian_c1.SPLITS:
            for room in rooms[split]:
                self.assertNotIn(str(room['seed']), text)

    def test_a_short_secret_is_refused(self):
        with self.assertRaises(ValueError):
            custodian_c1.generate_split(b'short', 'B', 1, [])


class Reveal(unittest.TestCase):
    def setUp(self):
        self.protocol = protocol_bytes()
        self.notice, self.rooms = notice_for(self.protocol)
        self.reveal = custodian_c1.reveal(self.rooms, SALTS, 'B')

    def test_an_honest_reveal_binds_to_the_published_commitment(self):
        verify_reveal(self.notice, 'B', self.reveal['entries'], bytes.fromhex(self.reveal['salt']))
        campaign_c1.bind_rooms(self.reveal, 'B', 2, [])

    def test_a_wrong_salt_is_refused(self):
        with self.assertRaises(ValueError):
            verify_reveal(self.notice, 'B', self.reveal['entries'], OTHER)

    def test_a_substituted_room_is_refused(self):
        forged = dict(self.reveal, rooms=[dict(self.reveal['rooms'][0], seed=12345)]+self.reveal['rooms'][1:])
        with self.assertRaises(ValueError):
            campaign_c1.bind_rooms(forged, 'B', 2, [])

    def test_a_seed_that_does_not_produce_its_shape_is_refused(self):
        other = custodian_c1.generate_split(OTHER, 'B', 1, [])[0]
        room = dict(self.reveal['rooms'][0], shape=other['shape'])
        entries = [dict(self.reveal['entries'][0], package_sha256=custodian_c1.package_sha(room))]
        forged = dict(self.reveal, rooms=[room]+self.reveal['rooms'][1:],
                      entries=entries+self.reveal['entries'][1:])
        with self.assertRaises(ValueError):
            campaign_c1.bind_rooms(forged, 'B', 2, [])

    def test_a_room_that_is_not_fresh_is_refused(self):
        with self.assertRaises(ValueError):
            campaign_c1.bind_rooms(self.reveal, 'B', 2, [self.reveal['rooms'][0]['shape']])


class Ordering(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='campaign-c1-test-')
        cls.latches = Path(cls.tmp.name)
        cls.protocol = protocol_bytes()
        cls.notice, cls.rooms = notice_for(cls.protocol)
        cls.frozen = campaign_c1.freeze(cls.notice, cls.protocol, cls.latches)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_freeze_needs_the_notice_that_commits_to_this_protocol(self):
        with self.assertRaises(ValueError):
            campaign_c1.freeze(self.notice, protocol_bytes(excluded=['0'*64]), self.latches/'other')

    def test_freeze_binds_the_payloads_to_the_notice(self):
        self.assertEqual(self.frozen['kind'], 'rehearsal')
        self.assertEqual(set(self.frozen['payloads']), {f'{x},{y}' for x in (-1, 0, 1) for y in (-1, 0, 1)})

    def test_c_is_refused_without_a_passing_b_and_the_latch_stays_sealed(self):
        reveal_c = custodian_c1.reveal(self.rooms, SALTS, 'C')
        failing_b = dict(split='B', verdict=dict(passes=False), freeze_sha256='x', rooms=[])
        with self.assertRaises(ValueError):
            campaign_c1.exam('C', self.notice, self.protocol, self.frozen, reveal_c, self.latches,
                             prior=failing_b)
        self.assertEqual(read_seal(self.latches/'C.json').state, 'sealed')

    def test_a_split_can_be_opened_only_once(self):
        latch = self.latches/'second-open.json'
        from echoai.nexus0.sim3.seal import seal
        seal(latch, split='B', commitment='0'*64, inventory_sha256='pending-reveal',
             custodian='test', n_packages=1)
        with open_once(latch):
            pass
        with self.assertRaises(Sim3Error):
            with open_once(latch):
                pass


class Regression(unittest.TestCase):
    """Nav's amendment: block on losses the oracle-calibrated agent avoids."""
    def row(self, seed, reached, **bad):
        return dict(dict(seed=seed, reached=bool(reached), energy=10, collisions=0,
                         reserve_violations=0, unsafe_admissions=0, false_facts=0,
                         imagined_writes=0, calibration_unchanged=True), **bad)

    def conditions(self, oracle_reaches_room_zero, **oracle_bad):
        rooms = range(20)
        learned = [self.row(i, i != 0) for i in rooms]
        nominal = [self.row(i, i == 0) for i in rooms]
        oracle = [self.row(i, i != 0 or oracle_reaches_room_zero, **(oracle_bad if i == 5 else {}))
                  for i in rooms]
        return {'c': dict(nominal=nominal, learned=learned, oracle=oracle,
                          prior_x=list(nominal), prior_d=list(nominal))}

    def test_a_loss_the_perfect_calibration_also_suffers_does_not_block(self):
        verdict = campaign_c1.verdict_for(self.conditions(False), {'s': dict(energy=0)})
        self.assertEqual(verdict['strict_losses'], 1)
        self.assertEqual(verdict['attributable_losses'], 0)
        self.assertFalse(verdict['checks']['no_new_failures'])
        self.assertTrue(verdict['passes'])
        self.assertFalse(verdict['passes_including_strict'])

    def test_a_loss_the_perfect_calibration_avoids_blocks(self):
        verdict = campaign_c1.verdict_for(self.conditions(True), {'s': dict(energy=0)})
        self.assertEqual(verdict['attributable_losses'], 1)
        self.assertFalse(verdict['passes'])

    def test_the_oracle_arm_is_held_to_the_hard_constraints(self):
        verdict = campaign_c1.verdict_for(self.conditions(False, unsafe_admissions=1),
                                          {'s': dict(energy=0)})
        self.assertFalse(verdict['checks']['hard_constraints'])
        self.assertFalse(verdict['passes'])

    def test_the_strict_count_is_reported_never_blocking(self):
        self.assertIn('no_new_failures', campaign_c1.REPORTED)
        self.assertNotIn('no_new_failures', campaign_c1.BLOCKING)
        self.assertIn('no_attributable_failures', campaign_c1.BLOCKING)
        self.assertIn('significant', campaign_c1.BLOCKING)


class Certificate(unittest.TestCase):
    def passing_exam(self, split, rooms, frozen_sha):
        return dict(split=split, freeze_sha256=frozen_sha, verdict=dict(passes=True), rooms=rooms)

    def setUp(self):
        self.protocol = protocol_bytes()
        self.frozen = dict(notice_sha256='n', protocol_sha256='p', payloads={})

    def chain(self, kind, secret=REHEARSAL_SECRET):
        protocol = protocol_bytes(kind)
        notice, rooms = notice_for(protocol, kind=kind, secret=secret)
        frozen_sha = campaign_c1.sha256_bytes(canonical_bytes(self.frozen))
        return notice, protocol, self.passing_exam('B', rooms['B'], frozen_sha), \
            self.passing_exam('C', rooms['C'], frozen_sha)

    def test_a_rehearsal_can_never_certify_green(self):
        notice, protocol, b, c = self.chain('rehearsal')
        self.assertFalse(campaign_c1.certify(notice, protocol, self.frozen, b, c,
                                             REHEARSAL_SECRET)['transfer3_green'])

    def test_only_an_external_campaign_notice_can_certify_green(self):
        notice, protocol, b, c = self.chain('campaign', secret=OTHER)
        result = campaign_c1.certify(notice, protocol, self.frozen, b, c, OTHER)
        self.assertTrue(result['transfer3_green'])
        self.assertIn('custodian having generated and held the secret', result['validity'])

    def test_a_wrong_secret_is_refused(self):
        notice, protocol, b, c = self.chain('rehearsal')
        with self.assertRaises(ValueError):
            campaign_c1.certify(notice, protocol, self.frozen, b, c, OTHER)

    def test_rooms_not_produced_by_the_committed_secret_are_refused(self):
        notice, protocol, b, c = self.chain('rehearsal')
        swapped = dict(b, rooms=custodian_c1.generate_split(OTHER, 'B', 2, []))
        with self.assertRaises(ValueError):
            campaign_c1.certify(notice, protocol, self.frozen, swapped, c, REHEARSAL_SECRET)

    def test_a_failing_b_cannot_be_certified(self):
        notice, protocol, b, c = self.chain('rehearsal')
        with self.assertRaises(ValueError):
            campaign_c1.certify(notice, protocol, self.frozen, dict(b, verdict=dict(passes=False)),
                                c, REHEARSAL_SECRET)


if __name__ == '__main__':
    unittest.main()
