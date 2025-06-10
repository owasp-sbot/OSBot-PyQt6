import osbot_pyqt6
from unittest                      import TestCase
from osbot_utils.utils.Files       import parent_folder, file_name
from osbot_pyqt6.utils.Version     import Version, version__osbot_pyqt6


class test_Version(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.version = Version()

    def test_path_code_root(self):
        assert self.version.path_code_root() == osbot_pyqt6.path

    def test_path_version_file(self):
        with self.version as _:
            assert parent_folder(_.path_version_file()) == osbot_pyqt6.path
            assert file_name    (_.path_version_file()) == 'version'

    def test_value(self):
        assert self.version.value() == version__osbot_pyqt6