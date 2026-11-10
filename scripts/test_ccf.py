import unittest
from ccf import classify
class CCFTests(unittest.TestCase):
    def test_official_security_venues(self):
        for venue,kind,tier in [('Proceedings of the 35th USENIX Security Symposium','conference','A'),('USENIX Security','conference','A'),('IEEE Transactions on Information Forensics and Security','journal','A'),('ACM Asia Conference on Computer and Communications Security','conference','C')]:
            self.assertEqual(classify(dict(venue=venue,kind=kind))['tier'],tier,venue)
    def test_unknown_and_companion_not_inherit(self):
        for venue in ['Unknown venue','USENIX Security Workshop','USENIX Security Companion','USENIX Security Findings']:
            self.assertEqual(classify(dict(venue=venue,kind='conference',tier='A'))['tier'],'Unrated')
    def test_supplied_grade_overwritten(self):
        self.assertEqual(classify(dict(venue='ACM Asia Conference on Computer and Communications Security',kind='conference',tier='A'))['tier'],'C')
