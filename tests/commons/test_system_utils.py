import unittest
import os
from bauh.commons import system

class TestSystemUtils(unittest.TestCase):

    def test_run_cmd(self):
        # Un test muy básico para verificar que run_cmd ejecuta y retorna salida
        res = system.run_cmd('echo test')
        self.assertEqual(res.strip(), 'test')

    def test_run_cmd_ignore_code(self):
        # Probamos el flag ignore_return_code
        res = system.run_cmd('echo test2', ignore_return_code=True)
        self.assertEqual(res.strip(), 'test2')

if __name__ == '__main__':
    unittest.main()
