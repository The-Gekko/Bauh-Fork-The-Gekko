import unittest
from unittest.mock import MagicMock

from bauh.view.qt.view_model import PackageView, PackageViewStatus
from bauh.api.abstract.model import SoftwarePackage, PackageStatus

class TestPackageView(unittest.TestCase):

    def test_package_view_initial_status(self):
        # Mapeo básico de un modelo a la vista
        mock_model = MagicMock(spec=SoftwarePackage)
        mock_model.name = "TestApp"
        mock_model.installed = True
        mock_model.update = False
        mock_model.status = PackageStatus.READY

        mock_i18n = MagicMock()
        view = PackageView(mock_model, i18n=mock_i18n)
        
        self.assertEqual(view.model.name, "TestApp")
        self.assertEqual(view.status, PackageViewStatus.READY)
        self.assertFalse(view.update_checked)

if __name__ == '__main__':
    unittest.main()
