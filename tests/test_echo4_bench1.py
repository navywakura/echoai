"""E4-BENCH-1 A · grader, ECHO verifier, structural property and a mock end-to-end run."""
import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from echoai.echo4 import bench1 as B


class Grader(unittest.TestCase):
    def test_short_answers(self):
        g = B.grade_short
        self.assertEqual(g("Michio Sugeno", "Michio Sugeno"), "correct")
        self.assertEqual(g("It was Michio Sugeno.", "Michio Sugeno"), "correct")
        self.assertEqual(g("Yoshua Bengio", "Michio Sugeno"), "incorrect")
        self.assertEqual(g("I don't know", "Michio Sugeno"), "not_attempted")
        self.assertEqual(g("1912", "1912"), "correct")
        self.assertEqual(g("In 1913", "1912"), "incorrect")
        self.assertEqual(g("15 June 1981", "June 15, 1981"), "correct")

    def test_letters_and_numbers(self):
        self.assertEqual(B.grade_letter("C", "C")[0], "correct")
        self.assertEqual(B.grade_letter("I don't know", "C")[0], "not_attempted")
        self.assertEqual(B.grade_number("so...\nFinal answer: 72", "72"), "correct")
        self.assertEqual(B.grade_number("Final answer: 70", "72"), "incorrect")


class Verifier(unittest.TestCase):
    def test_needs_an_extract(self):
        v = B.EchoVerifier()
        ex = [{"text": "The 2010 Frank Rosenblatt Award was given to Michio Sugeno."}]
        self.assertEqual(v.verify("Michio Sugeno", ex)["status"], "supported")
        self.assertEqual(v.verify("Yoshua Bengio", ex)["status"], "unknown")
        self.assertEqual(v.verify("Michio Sugeno", [])["status"], "unknown")
        self.assertEqual(v.verify("I don't know", ex)["status"], "unknown")

    def test_answer_is_a_hypothesis_not_a_fact(self):
        v = B.EchoVerifier()
        v.verify("Michio Sugeno", [{"text": "Michio Sugeno won."}])
        hyp = [s for s in v.cam.slot if s.occupied and s.source == B.HYPOTHESIS_SOURCE]
        self.assertTrue(hyp and all(not s.has_fact and not s.extract for s in hyp))


class Mock(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        user = body["messages"][1]["content"]
        if "Context passages" in user:                  # answer with the first words of the context
            first = user.split("\n")[1].split("] ", 1)[-1]
            content = " ".join(first.split()[:3])
        elif "Final answer" in body["messages"][0]["content"]:
            content = "Final answer: 1"
        else:
            content = "I don't know"
        raw = json.dumps({"choices": [{"message": {"content": content}}],
                          "usage": {"prompt_tokens": 10, "completion_tokens": 3}}).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *a):
        pass


class EndToEnd(unittest.TestCase):
    def test_mock_run_scores_and_audit_rebuilds(self):
        server = HTTPServer(("127.0.0.1", 0), Mock)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        old = B.OPENROUTER
        B.OPENROUTER = "http://127.0.0.1:%d/v1/chat/completions" % server.server_address[1]
        try:
            items = {"simpleqa": [{"id": "sq-x", "question": "Who won?", "gold": "Michio Sugeno"}],
                     "mmlupro": [{"id": "mm-x", "question": "Pick", "options": ["a", "b"], "gold": "A"}],
                     "gsm8k": [{"id": "gs-x", "question": "1+0?", "gold": "1"}]}
            retrieval = {"sq-x": {"extracts": [{"title": "t", "text": "Michio Sugeno won the award in 2010."}]},
                         "mm-x": {"extracts": [{"title": "t", "text": "Nothing relevant here at all."}]}}
            out = Path(tempfile.mkdtemp())
            receipts = {"mock/model": B.run_model("mock/model", items, retrieval, out, "test-key", workers=2)}
            self.assertNotIn("test-key", json.dumps(receipts))           # the key never enters receipts
            per_item, table = B.score(items, retrieval, receipts)
            sq = table["mock/model"]["simpleqa"]["counts"]
            self.assertEqual(sq["M"]["not_attempted"], 1)
            self.assertEqual(sq["TRIVIAL"]["not_attempted"], 1)
            gs = table["mock/model"]["gsm8k"]["counts"]
            self.assertEqual((gs["M"]["correct"], gs["M+ECHO"]["not_attempted"]), (1, 1))
            for row in per_item:                                           # ECHO never creates a correct answer
                if row["dataset"] != "gsm8k" and row["M+R+ECHO"] == "correct":
                    self.assertEqual(row["M+R"], "correct")
            r1, _, _ = B.report_for("dev", items, retrieval, receipts)
            r2, _, _ = B.report_for("dev", items, retrieval, receipts)
            self.assertEqual(r1["reproduction_sha256"], r2["reproduction_sha256"])
        finally:
            B.OPENROUTER = old
            server.shutdown()


if __name__ == "__main__":
    unittest.main()
