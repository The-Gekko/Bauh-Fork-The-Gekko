from unittest import TestCase
from unittest.mock import patch

from bauh.commons.config import YAMLConfigManager
from bauh.view.core.config import CoreConfigManager


class CoreConfigManagerTest(TestCase):

    def test_get_default_config__must_store_custom_theme_at_the_root_level(self):
        config = CoreConfigManager().get_default_config()

        self.assertIn('custom_theme', config)
        self.assertNotIn('custom_theme', config['ui'])

    @patch.object(YAMLConfigManager, 'read_config', return_value={
        'ui': {'custom_theme': {'opacity': 75, 'enabled': True}}
    })
    def test_read_config__must_migrate_legacy_custom_theme(self, read_config):
        config = CoreConfigManager().read_config()

        self.assertNotIn('custom_theme', config['ui'])
        self.assertEqual({'opacity': 75, 'enabled': True}, config['custom_theme'])
        read_config.assert_called_once()

    @patch.object(YAMLConfigManager, 'read_config', return_value={
        'ui': {'custom_theme': {'opacity': 75}},
        'custom_theme': {'opacity': 90}
    })
    def test_read_config__must_preserve_a_root_custom_theme(self, read_config):
        config = CoreConfigManager().read_config()

        self.assertNotIn('custom_theme', config['ui'])
        self.assertEqual({'opacity': 90}, config['custom_theme'])
        read_config.assert_called_once()
