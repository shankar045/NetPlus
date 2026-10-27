import unittest

from app import app, valid_host, tcp_check


class NetPulseTests(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_valid_hostnames_and_ips(self):
        self.assertTrue(valid_host("example.com"))
        self.assertTrue(valid_host("127.0.0.1"))
        self.assertTrue(valid_host("::1"))
        self.assertFalse(valid_host(""))
        self.assertFalse(valid_host("not a host"))

    def test_rejects_invalid_port(self):
        response = self.client.post("/api/monitor", json={
            "name": "bad port", "host": "localhost", "port": 70000
        })
        self.assertEqual(response.status_code, 400)

    def test_rejects_invalid_hostname(self):
        response = self.client.post("/api/monitor", json={
            "name": "bad host", "host": "not a valid host", "port": 443
        })
        self.assertEqual(response.status_code, 400)

    def test_local_tcp_connection_when_server_is_running(self):
        # This is a basic unit check of the return structure; a remote host is not required.
        result = tcp_check("127.0.0.1", 1, timeout=0.2)
        self.assertIn(result["status"], ("UP", "DOWN"))
        self.assertIn("message", result)


if __name__ == "__main__":
    unittest.main()
