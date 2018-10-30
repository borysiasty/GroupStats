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
 This script initializes the plugin, making it known to QGIS.
"""


def classFactory(iface):
    from .groupstats import GroupStats
    return GroupStats(iface)
