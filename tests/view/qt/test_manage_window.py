import unittest
from unittest.mock import MagicMock
import logging

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon

from bauh.view.qt.window.manage_window import ManageWindow
from bauh.api.abstract.controller import SoftwareManager
from bauh.api.abstract.context import ApplicationContext
from bauh.api.http import HttpClient
from bauh.view.util.translation import I18n
from bauh.api.abstract.cache import MemoryCache

class TestManageWindow(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Necesario para inicializar componentes Qt
        cls.app = QApplication.instance() or QApplication([])

    def test_instantiation_with_mixins(self):
        # Mocks para todas las dependencias
        mock_i18n = MagicMock(spec=I18n)
        mock_i18n.get.return_value = "Mock"
        mock_i18n.__getitem__.return_value = "Mock"
        
        mock_icon_cache = MagicMock(spec=MemoryCache)
        mock_manager = MagicMock(spec=SoftwareManager)
        mock_config = {
            'ui': {
                'table': {
                    'max_displayed': 50
                }
            },
            'download': {
                'icons': True
            },
            'memory_cache': {
                'data_expiration': 60
            },
            'disk': {
                'store_history': False
            },
            'suggestions': {
                'enabled': False
            }
        }
        mock_context = MagicMock(spec=ApplicationContext)
        mock_context.internet_checker = MagicMock()
        mock_http_client = MagicMock(spec=HttpClient)
        mock_logger = logging.getLogger("test")
        mock_icon = QIcon()

        try:
            window = ManageWindow(
                i18n=mock_i18n,
                icon_cache=mock_icon_cache,
                manager=mock_manager,
                config=mock_config,
                context=mock_context,
                http_client=mock_http_client,
                logger=mock_logger,
                icon=mock_icon
            )
            # Si instanció sin fallar el MRO, el test es exitoso
            self.assertIsNotNone(window)
            self.assertEqual(window.display_limit, 50)
            
            # Verificamos que los Mixins inyectaron sus métodos
            self.assertTrue(hasattr(window, '_handle_updates_filter')) # De WindowFiltersMixin
            self.assertTrue(hasattr(window, 'begin_uninstall'))        # De WindowActionsMixin
            self.assertTrue(hasattr(window, '_register_groups'))       # De WindowUIMixin

        except Exception as e:
            self.fail(f"ManageWindow falló al instanciar: {e}")

if __name__ == '__main__':
    unittest.main()
