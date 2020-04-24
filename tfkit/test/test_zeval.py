import unittest

import os


class TestEval(unittest.TestCase):

    def testHelp(self):
        result = os.system('tfkit-eval -h')
        self.assertTrue(result == 0)

    def testEvalOnGen(self):
        result = os.system(
            'tfkit-eval --model ./cache/10.pt --valid ../demo_data/generate.csv --metric classification --print')
        self.assertTrue(result == 0)
        result = os.system(
            'tfkit-eval --model ./cache/10.pt --valid ../demo_data/generate.csv --metric emf1 --print --beamsearch --outfile')
        self.assertTrue(result == 0)

    def testEvalClassify(self):
        result = os.system(
            'tfkit-eval --model ./cache/10.pt --valid ../demo_data/classification.csv --metric classification --print  --outfile')
        self.assertTrue(result == 0)

    def testEvalQA(self):
        result = os.system(
            'tfkit-eval --model ./cache/model/albert_small_zh_mrc.pt --valid ./cache/test_qa/drcd-dev --metric emf1 --outfile')
        self.assertTrue(result == 0)

    def testEvalTAG(self):
        result = os.system(
            'tfkit-eval --model ./cache/model/albert_small_zh_ner.pt --valid ../demo_data/tag_row.csv --metric classification --outfile')
        self.assertTrue(result == 0)
