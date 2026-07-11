from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from bauh.view.core import gems


class GemsLoaderTest(TestCase):

    @patch.object(gems, 'read_forbidden_gems', return_value=iter(()))
    @patch.object(gems.os, 'scandir', return_value=(SimpleNamespace(is_dir=lambda: True, name='example', path='/tmp/example'),))
    @patch.object(gems.importlib.util, 'find_spec')
    @patch.object(gems.importlib.util, 'module_from_spec')
    @patch.object(gems, 'find_manager')
    def test_load_managers__must_execute_the_module_spec(self, find_manager, module_from_spec, find_spec, scandir,
                                                          read_forbidden_gems):
        loader = Mock()
        spec = SimpleNamespace(loader=loader)
        module = object()
        manager = Mock()
        manager.is_default_enabled.return_value = True
        manager_class = Mock(return_value=manager)
        context = SimpleNamespace(i18n=SimpleNamespace(current={}, default={}))

        find_spec.return_value = spec
        module_from_spec.return_value = module
        find_manager.return_value = manager_class

        managers = gems.load_managers(locale=None, context=context, config={'gems': None}, default_locale='en',
                                      logger=Mock())

        self.assertEqual([manager], managers)
        module_from_spec.assert_called_once_with(spec)
        loader.exec_module.assert_called_once_with(module)
        manager.set_enabled.assert_called_once_with(True)

    @patch.object(gems, 'read_forbidden_gems', return_value=iter(()))
    @patch.object(gems.os, 'scandir', return_value=(SimpleNamespace(is_dir=lambda: True, name='broken', path='/tmp/broken'),))
    @patch.object(gems.importlib.util, 'find_spec')
    @patch.object(gems.importlib.util, 'module_from_spec')
    def test_load_managers__must_skip_a_gem_that_fails_to_import(self, module_from_spec, find_spec, scandir,
                                                                  read_forbidden_gems):
        loader = Mock()
        loader.exec_module.side_effect = ImportError('missing optional dependency')
        logger = Mock()
        context = SimpleNamespace(i18n=SimpleNamespace(current={}, default={}))

        find_spec.return_value = SimpleNamespace(loader=loader)
        module_from_spec.return_value = object()

        managers = gems.load_managers(locale=None, context=context, config={'gems': None}, default_locale='en',
                                      logger=logger)

        self.assertEqual([], managers)
        logger.exception.assert_called_once()
