# coding=utf-8
"""
InaSAFE Disaster risk assessment tool developed by Eka - **DaLA Configuration Dialog.**

Contact : eka.a.kurniawan@gmail.com

.. note:: This program is free software; you can redistribute it and/or modify
     it under the terms of the GNU General Public License as published by
     the Free Software Foundation; either version 2 of the License, or
     (at your option) any later version.

"""
__author__ = 'eka.a.kurniawan@gmail.com'
__revision__ = '$Format:%H$'
__date__ = '14/07/2015'
__copyright__ = 'Copyright 2015, Eka A. Kurniawan'

from PyQt4 import QtGui

from safe.utilities.resources import get_ui_class

FORM_CLASS = get_ui_class('dala_configuration_dialog_base.ui')


class DalaConfigurationDialog(QtGui.QDialog, FORM_CLASS):
    """DaLA Configuration"""

    def __init__(self, parent=None):
        """Constructor for the dialog.

        :param parent: Parent widget of this dialog
        :type parent: QWidget
        """

        QtGui.QDialog.__init__(self, parent)
        self.setupUi(self)
        self.parent = parent
