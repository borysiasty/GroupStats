# -*- coding: utf-8 -*-
"""
/***************************************************************************
 GroupStats
                                 A QGIS plugin
 Oblicza statystyki danych
                              -------------------
        begin                : 2012-12-21
        copyright            : (C) 2012 by Rayo
        email                : rayo001@interia.pl
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os.path

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import QAction, QMessageBox


from qgis.core import *

from . import resources_rc

from .GroupStatsDialog import GroupStatsDialog


class GroupStats:
    def __init__(self, iface):
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize locale
        pluginPath = QFileInfo(os.path.realpath(__file__)).path()  # patch by Régis Haubourg
        if QFileInfo(pluginPath).exists():
            localeName = QgsSettings().value("locale/userLocale")
            if localeName:
                localePath = pluginPath + "/i18n/groupstats_" + localeName + ".qm"
                if not QFileInfo(localePath).exists():
                    localePath = pluginPath + "/i18n/groupstats_" + localeName[:2] + ".qm"
                if QFileInfo(localePath).exists():
                    self.translator = QTranslator()
                    self.translator.load(localePath)
                    QCoreApplication.installTranslator(self.translator)
        # Create the dialog and keep reference
        self.dlg = GroupStatsDialog()


    def initGui(self):    
        # Create action that will start plugin configuration
        self.action = QAction(QIcon(":/plugins/groupstats/icon.png"), "GroupStats", self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        # Add toolbar button and menu item
        self.iface.addVectorToolBarIcon(self.action)
        self.iface.addPluginToVectorMenu( "&Group Stats", self.action )


    def unload(self):
        # Remove the plugin menu item and icon
        self.iface.removePluginVectorMenu( "&Group Stats", self.action )
        self.iface.removeVectorToolBarIcon(self.action)


    # run method that performs all the real work
    def run(self):
        warstwy = QgsProject.instance().mapLayers()        # Wczytanie słownika warstw z projektu
        listaWarstw = []
        for id in warstwy.keys():                                   # Wczytanie nazw warstw do okna
            if warstwy[id].type() == QgsMapLayer.VectorLayer:
                listaWarstw.append((warstwy[id].name(), id))

        if len(listaWarstw) == 0:
            QMessageBox.information(None,
                                    QCoreApplication.translate('GroupStats', 'Information'),
                                    QCoreApplication.translate('GroupStats', 'Vector layers not found'))
            return
        self.dlg.iface = self.iface
        self.dlg.ustawWarstwy(listaWarstw)
        
        # show the dialog
        self.dlg.show()
