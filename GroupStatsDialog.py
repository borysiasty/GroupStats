# -*- coding: utf-8 -*-

import csv
import os
import pickle
import sys
import webbrowser
from math import *

from PyQt5 import uic
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import QApplication, QFileDialog, QMainWindow, QMessageBox, QTableView, QWidget

from qgis.core import *
from qgis.gui import *


FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'ui_groupstats.ui'))

class GroupStatsDialog(QMainWindow):
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        self.ui = FORM_CLASS()
        self.ui.setupUi(self)

        self.ui.results = WindowResults(self.ui.centralwidget)

        self.ui.horizontalLayout.addWidget(self.ui.results)

        self.calculations = Calculations(self)

        self.ui.listHalf.setAcceptDrops(True)
        self.ui.listHalf.setModelColumn(2)

        self.ui.rows.setAcceptDrops(True)
        self.ui.column.setAcceptDrops(True)
        self.ui.values.setAcceptDrops(True)

        self.ui.calculate.clicked.connect(self.showScore)
        self.ui.clear.clicked.connect(self.clearChoice)
        self.ui.filterButton.clicked.connect(self.setFilter)
        self.ui.layer.currentIndexChanged.connect(self.layerSelection)   # Layer selection signal

        dictionary =  {'attributeTxt':[('Rejon',1), ('Posterunek',2)],
                    'countAttributes':[('Moc stacji', 3)],
                    'geometry':[('Length', 1), ('Area', 2)],
                    'calculations':[('Count', 1), ('Sum', 2), ('Average', 3), ('Standard deviation', 4)]}

        self.tm1 = ModelListaPol(self)
        self.ui.listHalf.setModel(self.tm1)

        self.tm2 = ModelWiK(self)
        #tm2.ustawInneModele(tm1)
        self.ui.rows.setModel(self.tm2)

        self.tm3 = ModelWiK(self)
        #tm3.ustawInneModele(tm1)
        self.ui.column.setModel(self.tm3)

        self.tm4 = ValueModel(self)
        self.ui.values.setModel(self.tm4)

        self.tm2.setOtherModels(self.tm3, self.tm4)
        self.tm3.setOtherModels(self.tm2, self.tm4)
        self.tm4.setOtherModels(self.tm2, self.tm3)

        self.tm2.rowsInserted.connect(self.blockCalculations)   # Layer selection signal
        self.tm3.rowsInserted.connect(self.blockCalculations)   # Layer selection signal
        self.tm4.rowsInserted.connect(self.blockCalculations)   # Layer selection signal
        self.tm2.rowsRemoved.connect(self.blockCalculations)   # Layer selection signal
        self.tm3.rowsRemoved.connect(self.blockCalculations)   # Layer selection signal
        self.tm4.rowsRemoved.connect(self.blockCalculations)   # Layer selection signal

        self.ui.actionCopy.triggered.connect(self.duplication)   # Layer selection signal
        self.ui.actionCopySelected.triggered.connect(self.copyMarked)   # Layer selection signal
        self.ui.actionSaveCSV.triggered.connect(self.exportToCSV)   # Layer selection signal
        self.ui.actionSaveCSVSelected.triggered.connect(self.exportMarkedToCSV)   # Layer selection signal
        self.ui.actionShowPanel.triggered.connect(self.showControlPanel)   # Layer selection signal
        self.ui.actionShowOnMap.triggered.connect(self.showOnMap)   # Layer selection signal
        self.ui.actionTutorial.triggered.connect(self.showTutorial)   # Layer selection signal

        self.ui.results.verticalHeader().sortIndicatorChanged.connect(self.sortRows)   # Layer selection signal


    def sortRows(self,rows,mode):
            self.ui.result.model().sortRows(rows,mode)


    def blockCalculations(self, x, y, z): #finished
        values = self.tm4.data
        column = self.tm3.data
        rows = self.tm2.data
        # If the value field has numbers (attributes or geometry) and some calculate function has been selected
        if  ('geometry' in [a[0] for a in values] or 'countAttributes' in [a[0] for a in values]) and\
            'calculations' in [a[0] for a in values+rows+column]:
            self.ui.calculate.setEnabled(True)
        # If the value field has a text attribute and you have selected exactly one function - the counter
        elif 'attributeTxt' in [a[0] for a in values] and len([a for a in values+rows+column if a[0]=='calculations'])>0:
            if set([a[2] for a in values+rows+column if a[0]=='calculations']).issubset(set(self.calculations.textList)): #[a for a in values+rows+column if a[0]=='calculations'][0][2]==0:
                self.ui.calculate.setEnabled(True)
        else:
            self.ui.calculate.setEnabled(False)


    def showScore(self):               #finished
        "Performs calculations and sends them for display"

        chosenRows = tuple(self.tm2.data)                                               # Reading selected rows from the window
        chosenColumns = tuple(self.tm3.data)                                               # Reading selected columns from the window
        chosenValues = tuple(self.tm4.data)                                          # Reading from the window chosenj values ​​and calculations

        value = [x for x in chosenValues if x[0]!='calculations'][0]                 # reading the field that has been chosen for calculation (can only be one)
        if value[0]=='geometry':                                                         # Setting the calculate function depending on the chosen value type
            if value[2]==1:
                valueFunction = lambda _object: _object.geometry().length()                  # length
            elif value[2]==2:
                valueFunction = lambda _object: _object.geometry().area()                    # area
        elif value[0]=='attributeTxt':
            valueFunction = lambda _object: None if _object.attribute(value[1])==None else _object.attribute(value[1])#.toString()    # amodeut tekstowy
        elif value[0]=='countAttributes':
            valueFunction = lambda _object: None if _object.attribute(value[1])==None else float(_object.attribute(value[1]))         #.toReal()[0]   # amodeut liczbowy (toReal daje wynik (real, True/False))

        index = self.ui.layer.currentIndex()                                             # Download chosen layer
        layerId = self.ui.layer.itemData(index)
        layer = QgsProject.instance().mapLayer(layerId)#.toString())

        provider = layer.dataProvider()
        request = QgsFeatureRequest()
        _filter = self.ui._filter.toPlainText()
        if _filter:
            request.setFilterExpression(_filter)
        iterator = provider.getFeatures(request)

        if self.ui.onlySelected.isChecked():                                         # Retrieve the IDs of the selected _objects
            selectedObjects = layer.selectedFeatureIds()
            onlySelected = True
        else:
            selectedObjects = []
            onlySelected = False

        result = {}                                                                         # Dictionary for result {((rows) (column)): [[values], [indexes]}
        f=QgsFeature()                                                                      # Data search for calculations
        numberOfObjects = provider.featureCount()
        if numberOfObjects != 0:
            percent = 100.00 / numberOfObjects                                                   # Number of _objects
        else:
            percent = 100
        counter = 0.0
        NULLcounter = 0
        while iterator.nextFeature(f):                                                      # for each object ...
            if onlySelected==False or (onlySelected and (f.id() in selectedObjects)):

                key_column = []                                                                  # key column (column1, column2...)
                key_row = []                                                                  # key row (rows1, rows2...)
                key = ()
                for k in chosenColumns:                                                        # for each chosen column we check the column type
                    if k[0]=='geometry':                                                       # and create the key column
                        if k[2]==1:
                            key_column.append(f.geometry().length())
                        elif k[2]==2:
                            key_column.append(f.geometry().area())
                    elif k[0]=='attributeTxt' or k[0]=='countAttributes':
                        if f.attribute(k[1]) == None:
                            newKeyColumns = ''
                        else:
                            newKeyColumns = f.attribute(k[1])

                        key_column.append(newKeyColumns)#.toString())
                for k in chosenRows:                                                        # for each chosen rows we check the rows type
                    if k[0]=='geometry':                                                       # and create key rows
                        if k[2]==1:
                            key_row.append(f.geometry().length())
                        elif k[2]==2:
                            key_row.append(f.geometry().area())
                    elif k[0]=='attributeTxt' or k[0]=='countAttributes':
                        if f.attribute(k[1]) == None:
                            newRowKey = ''
                        else:
                            newRowKey = f.attribute(k[1])

                        key_row.append(newRowKey)

                key = ( tuple(key_row) , tuple(key_column) )                                 # key to identify object groups

                valueToCalculate = valueFunction(f)
                if valueToCalculate!=None or self.ui.useNULL.isChecked():
                    if  valueToCalculate==None:
                        NULLcounter += 1
                        if value[0]=='countAttributes':
                            valueToCalculate=0

                    if key in result:
                        result[key][0].append(valueToCalculate)                                     # if key exists, a new value is added to the list
                    else:
                        result[key] = [[valueToCalculate],[]]                                         # if key does not exist then a new list is created

                    result[key][1].append(f.id())
                else:
                    NULLcounter += 1

                counter = counter + percent
                self.statusBar().showMessage(QCoreApplication.translate('GroupStats','Calculate... ') + '%.0f%%' % (counter))         # Displaying progress

        self.statusBar().showMessage(self.statusBar().currentMessage() + ' |  ' + QCoreApplication.translate('GroupStats','generate view...'))

        keys = result.keys()                                                              # Finding unique row and column keys (separately)
        topmost = set([])
        kolu = set([])
        for z in keys:                                                                    # adding keys to collections to reject repetition
            topmost.add(z[0])
            kolu.add(z[1])
        rows = list(topmost)                                                                # list of unique row keys
        column = list(kolu)                                                                # list of unique column keys

        rowDictionary={}                                                                      # Creating dictionaries for rows and columns (faster search)
        for nr, row in enumerate(rows):
            rowDictionary[row]=nr
        columnDictionary={}
        for nr, column in enumerate(column):
            columnDictionary[column]=nr

        calculations = [[x[2] for x in chosenValues if x[0]=='calculations'],         # list of selected calculations in values, rows and columns
                      [x[2] for x in chosenRows      if x[0]=='calculations'],
                      [x[2] for x in chosenColumns      if x[0]=='calculations']]

        if len(calculations[0])!=0:                                                           # Take to calculations only the non-empty part of the list above
            calculation = calculations[0]
        elif len(calculations[1])!=0:
            calculation = calculations[1]
        else:
            calculation = calculations[2]

        data = []                                                                           # Creating an empty array for the date (l.row x l.column)
        for x in range( max( len(rows) , len(rows)*len(calculations[1]))):
            data.append(max(len(column),len(column)*len(calculations[2]))*[('',())])

        print("result: {} rowDictionary {} calculation {} ".format(str(result), str(rowDictionary), str(calculation)))
        print("self.calculations.list: " + str(self.calculations.list))
        for x in keys:                                                                    # Calculation of values ​​for all keys
            nrw = rowDictionary[x[0]]                                                         # rows no in the data table for the chosen key
            nrk = columnDictionary[x[1]]                                                          # column number in the data table for the chosen key
            for n,y in enumerate(calculation):                                                       # making all calculates for all keys
                if len(calculations[1])>0:
                    data[nrw*len(calculations[1])+n][nrk] = [self.calculations.list[y][1](result[x][0]), result[x][1]]    # insert result if calculations with row
                elif len(calculations[2])>0:
                    data[nrw][nrk*len(calculations[2])+n] = [self.calculations.list[y][1](result[x][0]), result[x][1]]    # insert result if calculations from columns
                else:
                    data[nrw][nrk] = [self.calculations.list[y][1](result[x][0]), result[x][1]]                         # insert result if calculations with values

        atr = {}                                                                            # Attributes as dict.
        for i in range(provider.fields().count()):
            atr[i] = provider.fields().at(i)

        rowNames=[]                                                                     # List with names of rows
        for x in chosenRows:
            if x[0]=='geometry':
                rowNames.append(x[1])
            elif x[0]!='calculations':
                rowNames.append(atr[x[2]].name())
        colNames=[]                                                                      # List with column names
        for x in chosenColumns:
            if x[0]=='geometry':
                colNames.append(x[1])
            elif x[0]!='calculations':
                colNames.append(atr[x[2]].name())

        nameColumnsCalculations=()                                                              # Insert row and column names with calculations
        nameRowsCalculation=()
        if len(calculations[1])>0:
            obl = [self.calculations.list[x][0] for x in calculations[1]]
            rows1 = [w+(o,) for w in rows for o in obl]
            column1 = column
            nameRowsCalculation=(QCoreApplication.translate('GroupStats','Function'),)
        elif len(calculations[2])>0:
            obl = [self.calculations.list[x][0] for x in calculations[2]]
            column1 = [w+(o,) for w in column for o in obl]
            rows1 = rows
            nameColumnsCalculations=(QCoreApplication.translate('GroupStats','Function'),)
        else:
            column1 = column
            rows1 = rows
        if len(rows1)>0 and len(rows1[0])>0:
            rows1.insert(0,tuple(rowNames)+nameRowsCalculation)
        if len(column1)>0 and len(column1[0])>0:
            column1.insert(0,tuple(colNames)+nameColumnsCalculations)


        if len(rows1)>0 and len(column1)>0:
            self.ui.result.setUpdatesEnabled(False)
            self.tm5 = ResultModel(data, rows1, column1, layer)
            self.ui.result.setModel(self.tm5)
            for i in range(len(column1[0]),0,-1):
                self.ui.result.verticalHeader().setSortIndicator( i-1, Qt.AscendingOrder )
            for i in range(len(rows1[0]),0,-1):
                self.ui.result.horizontalHeader().setSortIndicator( i-1, Qt.AscendingOrder )
            statement = self.statusBar().currentMessage()
            percent = 100.00 / self.tm5.columnCount()
            counter = 0
            for i in range(self.tm5.columnCount()):
                self.ui.result.resizeColumnToContents(i)
                counter = counter + percent
                self.statusBar().showMessage(statement + '%.0f%%' % (counter))

            self.ui.result.setUpdatesEnabled(True)

            if NULLcounter==1:
                rekordy='record'
            else:
                rekordy='records'

            if self.ui.useNULL.isChecked() and NULLcounter>0:
                textNULL = QCoreApplication.translate('GroupStats','  (used %s %s with null value in "%s" field)' % (NULLcounter, rekordy, value[1]))
            elif self.ui.useNULL.isChecked()==False and NULLcounter>0:
                textNULL = QCoreApplication.translate('GroupStats','  (not used %s %s with null value in "%s" field)' % (NULLcounter, rekordy, value[1]))
            else:
                textNULL = ''

            self.statusBar().showMessage(self.statusBar().currentMessage() + ' |  ' + QCoreApplication.translate('GroupStats','done.')+textNULL, 20000)

        else:
            try:
                del(self.tm5)
            except AttributeError:
                pass

            self.ui.result.setModel(None)
            self.statusBar().showMessage(QCoreApplication.translate('GroupStats','No data found.'), 10000)


    def setLayers (self, layer):   #finished
        "Adds available layers to the selection list in the window"

        index = self.ui.layer.currentIndex()
        if index !=-1:
            layerId = self.ui.layer.itemData(index)                        # id wcześniej chosenj layer

        self.ui.layer.blockSignals(True)
        self.ui.layer.clear()                                                 # wypełnienie comboBoxa nową listą warstw
        layer.sort(key=lambda x: x[0].lower())
        for i in layer:
            self.ui.layer.addItem(i[0], i[1])

        if index !=-1:
            index2 = self.ui.layer.findData(layerId)                       # jeżeli wcześniej wybrana layer jest to liście to wybranie jej
            if index2 !=-1:
                self.ui.layer.setCurrentIndex(index2)
            else:
                self.layerSelection(0)                                            # jeśli nie ma to wybranie pierwszej
        else:
            self.layerSelection(0)
        self.ui.layer.blockSignals(False)


    def layerSelection(self, index):     #finished
        "Runs after selecting layer from the list. Sets a new list of fields to choose from and deletes windows with already selected fields"

        idW = self.ui.layer.itemData(index)                          # Get the ID of the selected layer
        layer = QgsProject.instance().mapLayer(idW)#.toString())
        provider = layer.dataProvider()
        fields = provider.fields()

        dictionary = {}
        if layer.geometryType() in (QgsWkbTypes.PointGeometry, QgsWkbTypes.NullGeometry):
            dictionary['geometry'] =  []
        elif layer.geometryType() == QgsWkbTypes.LineGeometry:                             # line
            dictionary['geometry'] = [(QCoreApplication.translate('GroupStats','Length'), 1)]
        elif layer.geometryType() == QgsWkbTypes.PolygonGeometry:                             # polygon
            dictionary['geometry'] = [(QCoreApplication.translate('GroupStats','Perimeter'), 1), (QCoreApplication.translate('GroupStats','Area'), 2)]

        dictionary['countAttributes'] = []
        dictionary['attributeTxt'] = []

        for i in range(fields.count()):
            field = fields.at(i)
            if field.typeName().upper() in ('REAL', 'FLOAT4', 'DOUBLE') or field.typeName().upper().startswith('INT'):
                dictionary['countAttributes'].append((field.name(), i))
            else:
                dictionary['attributeTxt'].append((field.name(), i))

        dictionary['calculations']=[]
        obl = self.calculations.list
        for c,b in obl.items():
            dictionary['calculations'].append((b[0],c))

        del(self.tm1)
        self.tm1 = ModelListaPol()
        self.ui.listHalf.setModel(self.tm1)
        keys = ['calculations', 'geometry']
        for i in keys:
            j = dictionary[i]
            j.sort(key=lambda x: x[0].lower())
            rows=[]
            for k, l in j:
                rows.append((i,k,l))
            self.tm1.insertRows( 0, len(rows), QModelIndex(), rows)

        keys = ['countAttributes', 'attributeTxt']
        rows=[]
        for i in keys:
            j = dictionary[i]
            for k, l in j:
                rows.append((i,k,l))

        rows.sort(key=lambda x: x[1].lower())
        self.tm1.insertRows( 0, len(rows), QModelIndex(), rows)

        self.clearChoice()


    def clearChoice(self):             # finished
        " Czyści okna z wybranymi rowsami, columnmi i wartościami"
        self.tm2.removeRows(0, self.tm2.rowCount() ,QModelIndex())
        self.tm3.removeRows(0, self.tm3.rowCount() ,QModelIndex())
        self.tm4.removeRows(0, self.tm4.rowCount() ,QModelIndex())
        self.ui._filter.setPlainText('')


    def showControlPanel(self):     # finished
        ""

        self.ui.panelSterowania.setVisible(True)

    def showTutorial(self):
        url = "http://underdark.wordpress.com/2013/02/02/group-stats-tutorial/"
        webbrowser.open (url, 2)

    def setFilter(self):               # finished 2
        index = self.ui.layer.currentIndex()                                             # Pobranie chosenj layer
        layerId = self.ui.layer.itemData(index)
        layer = QgsProject.instance().mapLayer(str(layerId))

        text = self.ui._filter.toPlainText()                                                 # Pobranie tekstu z okna i wyświetlenie okna zapytań
        q = QgsSearchQueryBuilder(layer)
        q.setSearchString(text)
        q.exec_()

        self.ui._filter.setPlainText(q.searchString ())                                       # Wstawienie zapytania do okna

    # ------------------------ KOPIOWANIE DANYCH DO SCHOWKA I ZAPIS CSV ----------------------------START

    def duplication (self):
        "Kopiowanie wszystkich danych do schowka"
        text, test = self.downloadDataFromTheTable(True, True)
        if test==True:
            schowek = QApplication.clipboard()
            schowek.setText(text)

    def copyMarked (self):
        "Kopiowanie zaznaczonych danych do schowka"
        text, test = self.downloadDataFromTheTable(False, True)
        if test==True:
            schowek = QApplication.clipboard()
            schowek.setText(text)

    def exportToCSV (self):
        "Zapisuje wszystkie data do pliku CSV"
        data, test = self.downloadDataFromTheTable(True, False)
        if test==True:
            self.saveFileData(data)

    def exportMarkedToCSV (self):
        "Zapisuje zaznaczone data do pliku CSV"
        data, test = self.downloadDataFromTheTable(False, False)
        if test==True:
            self.saveFileData(data)

    def saveFileData (self, data):
        "Obsługa zapisu danych do pliku"
        fileWindow = QFileDialog()                                              # Wybór pliku do zapisu
        fileWindow.setAcceptMode(1)
        fileWindow.setDefaultSuffix("csv")
        fileWindow.setNameFilters(["CSV files (*.csv)", "All files (*)"])
        if fileWindow.exec_() == 0:                                             # Nie wybrano żadnego pliku - wyjście
            return
        fileName = fileWindow.selectedFiles()[0]
        _file = open(fileName, 'w')                                           # Otwarcie pliku do zapisu
        csvfile = csv.writer( _file, delimiter=';' )
        for i in data:                                                          # Kopiowanie danych z tabeli
            #csvfile.writerow([bytes(x, 'utf-8') for x in i])
            csvfile.writerow(i)
        _file.close()

    def downloadDataFromTheTable(self, allData=True, controlCharacters=False):
        if self.ui.result.model()==None:
            QMessageBox.information(None,QCoreApplication.translate('GroupStats','Information'), \
                QCoreApplication.translate('GroupStats','No data to save/copy'))
            return None, False

        text=''
        data = []
        numberOfColumns = self.tm5.columnCount()
        numberOfRows = self.tm5.rowCount()
        rows = []
        column = []

        if allData == False:                                                               # Jeśli opcja 'only zaznaczone' pobranie indexów zaznaczonych pól
            indexList = self.ui.result.selectedIndexes()
            if len(indexList)==0:
                QMessageBox.information(None,QCoreApplication.translate('GroupStats','Information'), \
                    QCoreApplication.translate('GroupStatsD','No data selected'))
                return None, False
            for i in indexList:
                rows.append(i.row())
                column.append(i.column())

        for i in range(numberOfRows):                                                          # Copying data from the table
            if allData or (i in rows) or (i < self.tm5.offsetY):
                rows = []
                for j in range(numberOfColumns):
                    if allData or (j in column) or (j < self.tm5.offsetX):
                        rows.append(str(self.tm5.createIndex(i,j).data()))
                data.append(rows)

        if controlCharacters == True:
            for m, i in enumerate(data):                                                # Copying data from the table
                if m>0:
                    text = text + chr(13)
                for n, j in enumerate(i):
                    if n>0:
                        text = text + chr(9)
                    text = text + j
            return text, True
        else:
            return data, True

    # ------------------------ COPYING DATA TO THE CLIPBOARD AND SAVING CSV ------------------ ---------- END



    def showOnMap(self):             # zmienic zeby nie dublowac indexow z komorek
        indexList = self.ui.result.selectedIndexes()                                    # Pobranie indexów zaznaczonych pól
        idList = []
        for i in indexList:                                                             # Pobranie indexów _objectów do pokazania
            lista = i.data(Qt.UserRole)#.toList()
            if lista == None:                                                               # Odrzucenie row z nagłówkami
                lista = ()
            for j in lista:
                idList.append(j)    #w 1 było idList.append(j.toInt()[0])

        self.tm5.layer.selectByIds(idList)                                           #   zaznaczenie ich na mapie
        self.iface.mapCanvas().zoomToSelected(self.tm5.layer)                         #   zoom do wybranych _objectów
        if len(idList)==1 and self.tm5.layer.geometryType()==0:                      #      jeżeli layer jest punktowa i w grupie jest only jeden _object..
            self.iface.mapCanvas().zoomScale(1000)                                      #      to ustaw skalę na 1:1000


class ModelList(QAbstractListModel):
    """
    Model for windows with amodeut lists.
    Data stored on the list: [(amodeutu type, name, id), ...]
    """

    def __init__(self, mainWindow, parent=None):

        super(ModelList, self).__init__(parent)
        self.data = []
        self.mainWindow = mainWindow
        self.calculations = Calculations(self)


    def rowCount(self, parent=QModelIndex):
        return len(self.data)


    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < self.rowCount():
            return None#QVariant()

        rows = index.row()

        if role == Qt.DisplayRole:
            return self.data[rows][1]

        #elif rola == Qt.ForegroundRole:
        #    if self.data[rows][0] == 'geometry':
        #        kolor = QColor(0,255,0)
        #    elif self.data[rows][0] == 'calculations':
        #        kolor = QColor(255,0,0)
        #    elif self.data[rows][0] == 'attributeTxt':
        #        kolor = QColor(150,150,150)
        #    else:
        #        kolor = QColor(0,0,0)   # 'countAttributes'
        #
        #    pedzel = QBrush(kolor)
        #    return pedzel

        elif role == Qt.DecorationRole:
            if self.data[rows][0] == 'geometry':
                icon = QIcon(":/plugins/groupstats/icons/geom.png")
            elif self.data[rows][0] == 'calculations':
                icon = QIcon(":/plugins/groupstats/icons/calc.png")
            elif self.data[rows][0] == 'attributeTxt':
                icon = QIcon(":/plugins/groupstats/icons/alpha.png")
            else:
                icon = QIcon(":/plugins/groupstats/icons/digits.png")

            return icon

        return None#QVariant()


    def mimeTypes(self):
        return ['application/x-groupstats-polaL', 'application/x-groupstats-polaWK', 'application/x-groupstats-polaW']


    def supportedDragActions(self):
        return Qt.MoveAction


    def supportedDropActions(self):
        return Qt.MoveAction


    def insertRows(self, rows, number, index, data):
        self.beginInsertRows(index, rows, rows + number - 1)
        for n in range(number):
            self.data.insert(rows+n, data[n])
        self.endInsertRows()
        return True


    def removeRows(self, rows, number, index):
        self.beginRemoveRows(index, rows, rows+number-1)
        del self.data[rows:rows+number]
        self.endRemoveRows()
        return True


    def mimeData(self, indexy, typMime='application/x-groupstats-polaL'):
        print("Indexy:" + str(type(indexy)) + " value: " + str(indexy))
        dataMime = QMimeData()
        data = QByteArray()
        stream = QDataStream(data, QIODevice.WriteOnly)
        for index in indexy:
            row = index.row()
            stringg = pickle.dumps(self.data[row][2])
            #stream << self.data[rows][0][0] << self.data[rows][1][0]    #----------------------------- ???????[0]poprawic
            # Datatypes below happen to be strings or already bytes! (b'geometry', b'calculations' or b'attributeTxt' - maybe reused?)

            stream.writeBytes(bytes(self.data[row][0], 'utf-8') if isinstance(self.data[row][0], str) else bytes(self.data[row][0]))
            stream.writeBytes(bytes(self.data[row][1], 'utf-8') if isinstance(self.data[row][1], str) else bytes(self.data[row][1]))
            stream.writeInt16(self.data[row][2])

        dataMime.setData(typMime, data)

        return dataMime


    def flags(self, index):
        flag = super(ModelList, self).flags(index)

        if index.isValid():
            return flag | Qt.ItemIsDragEnabled | Qt.ItemIsEnabled | Qt.ItemIsSelectable
        else:
            return Qt.ItemIsDropEnabled


class ModelWiK(ModelList):
    """
    Model dla okien z listami pól dla row i kolumn
    """

    def __init__(self, parent):

        super(ModelWiK, self).__init__(parent)
        self.data = []


    def setData(self, index, value):
        self.data.insert(index,value)
        return True


    def setOtherModels(self, modelWiK, valueModel):
        self.modelWiK = modelWiK.data
        self.valueModel = valueModel.data


    def mimeData(self, indexy):
        return super(ModelWiK, self).mimeData(indexy, 'application/x-groupstats-polaWK')

    def dropMimeData(self, dataMime, share, rows, column, index):
        if dataMime.hasFormat('application/x-groupstats-polaL'):
            dataType = 'application/x-groupstats-polaL'
        elif dataMime.hasFormat('application/x-groupstats-polaWK'):
            dataType = 'application/x-groupstats-polaWK'
        elif dataMime.hasFormat('application/x-groupstats-polaW'):
            dataType = 'application/x-groupstats-polaW'
        else:
            return False

        data = dataMime.data(dataType)

        stream = QDataStream(data, QIODevice.ReadOnly)
        outData = []
        while not stream.atEnd():
            #typ = ''#QString() --------------------------------???????????????????????????????????????
            #name = ''#QString()   -------------------------------------??????????????????????????????????????????????
            #stream >> typ >> name
            typ = stream.readBytes().decode('utf-8')
            name = stream.readBytes().decode('utf-8')
            id = stream.readInt16()
            field = (typ, name, id)
            dataWKiW = self.modelWiK+self.valueModel
            print("typ: " + str(typ))
            print("Field: " + str(field))
            print("self.calculations.textList: " + str(self.calculations.textList))
            if typ=='calculations' and typ in [x[0] for x in dataWKiW] and dataType == 'application/x-groupstats-polaL':
                self.mainWindow.statusBar().showMessage(QCoreApplication.translate('GroupStats','Function can be droped in only one area'),15000)
                return False
            elif (field in self.modelWiK or field in self.data) and dataType in ['application/x-groupstats-polaL', 'application/x-groupstats-polaW']:
                self.mainWindow.statusBar().showMessage(QCoreApplication.translate('GroupStats','This field has already been droped'),15000)
                return False
            #elif (typ != 'calculations' and 'calculations' in [x[0] for x in self.data]) or (typ=='calculations' and len([x for x in self.data if (x[0] != 'calculations')])>0):
            #    print 'pola calculateeniowe nie moga byc razem z innymi polami'
            #    return False
            elif typ=='calculations' and id not in self.calculations.textList and 'attributeTxt' in [x[0] for x in self.valueModel]:  #name != self.calculations.lista[0][0]
                self.mainWindow.statusBar().showMessage(QCoreApplication.translate('GroupStats','For the text value function can only be one of (%s)' % self.calculations.textNames), 15000)
                return False

            outData.append(field)

        self.insertRows(rows, len(outData), index, outData)

        return True


class ValueModel(ModelList):
    """
    Model for a window with values ​​for calculations
    """

    def __init__(self, parent=None):

        super(ValueModel, self).__init__(parent)
        self.data = []

    def mimeData(self, indexy):
        return super(ValueModel, self).mimeData(indexy, 'application/x-groupstats-polaW')

    def dropMimeData(self, dataMime, share, rows, column, index):

        if dataMime.hasFormat('application/x-groupstats-polaL'):
            dataType = 'application/x-groupstats-polaL'
        elif dataMime.hasFormat('application/x-groupstats-polaWK'):
            dataType = 'application/x-groupstats-polaWK'
        elif dataMime.hasFormat('application/x-groupstats-polaW'):
            dataType = 'application/x-groupstats-polaW'
        else:
            return False

        data = dataMime.data(dataType)
        stream = QDataStream(data, QIODevice.ReadOnly)
        outData = []
        while not stream.atEnd():

            #typ = '2'#QString()-------------------------------------????????????????????????????
            #name = '2'#QString()-------------------------------------?????????????????????
            #stream >> typ >> name
            typ = stream.readBytes().decode('utf-8')
            name = stream.readBytes().decode('utf-8')
            id = stream.readInt16()
            field = (typ, name, id)

            allData = self.modelRows+self.modelColumns+self.data
            dataWiK = self.modelRows+self.modelColumns
            if len(self.data)>=2:
                self.mainWindow.statusBar().showMessage(QCoreApplication.translate('GroupStats',"Area 'Value' may contain a maximum of two entries"),15000)
                return False
            elif typ=='calculations' and typ in [x[0] for x in allData] and dataType == 'application/x-groupstats-polaL':
                self.mainWindow.statusBar().showMessage(QCoreApplication.translate('GroupStats','Function can be droped in only one area'),15000)
                return False
            elif len(self.data)==1 and typ != 'calculations' and self.data[0][0] != 'calculations':
                self.mainWindow.statusBar().showMessage(QCoreApplication.translate('GroupStats',"In the area 'Value' one of the items must be a function"),15000)
                return False
            elif len(self.data)==1 and ((typ=='attributeTxt' and self.data[0][2] not in self.calculations.textList) or (id not in self.calculations.textList and self.data[0][0] == 'attributeTxt')):
                self.mainWindow.statusBar().showMessage(QCoreApplication.translate('GroupStats','For the text value function can only be one of (%s)' % self.calculations.textNames), 15000)
                return False
            elif typ=='attributeTxt' and len([x for x in dataWiK if (x[0]=='calculations' and x[2] not in self.calculations.textList)])>0:
                self.mainWindow.statusBar().showMessage(QCoreApplication.translate('GroupStats','For the text value function can only be one of (%s)' % self.calculations.textNames), 15000)
                return False

            outData.append(field)

        self.insertRows(rows, len(outData), index, outData)


        # sprawdzic: co jeśli przy usuwaniu zostanie only pole calculateeniowe albo pole values


        return True

    def setOtherModels(self, modelRows, modelColumns):
        self.modelRows = modelRows.data
        self.modelColumns = modelColumns.data


class ModelListaPol(ModelList):
    """
    Model for the window with a list of available fields
    """

    def __init__(self, parent=None):

        super(ModelListaPol, self).__init__(parent)
        #self.ustawDane(slownikPol)
        self.data = []

    def dropMimeData(self, dataMime, share, rows, column, index):
        return True


    def removeRows(self, rows, number, index):

        return True


class ResultModel(QAbstractTableModel):     # finished
    """
    Model dla okna z wynikami calculations
    """

    def __init__(self, data, rows, column, layer, parent=None):
        super(ResultModel, self).__init__(parent)
        self.data = data
        self.rows = rows
        self.column = column
        self.layer = layer

        self.offsetX = max(1,len(rows[0]))                                           # Przesunięcie współrzednych tak, aby data zaczynały się od 0,0
        self.offsetY = max(1,len(column[0]))

        if len(rows[0]) != 0 and len(column[0]) != 0:                               # Przesunięcie o jeden rows (pusty) aby zrobić miejsce na nazwy row
                self.offsetY += 1

    def columnCount(self,parent=QModelIndex()):
        if len(self.rows[0])>0 and len(self.column[0])>0:
            l = len(self.column)+len(self.rows[0])-1
        elif len(self.rows[0])>0 and len(self.column[0])==0:
            l = len(self.rows[0])+1
        elif len(self.rows[0])==0 and len(self.column[0])>0:
            l = len(self.column)
        else:
            l = 2

        return l #max(len(self.rows[0])+1,len(self.column)+len(self.rows[0]))

    def rowCount(self, parent=QModelIndex()):
        return max(2,len(self.rows)+len(self.column[0]))

    def data(self, index, rola=Qt.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < self.rowCount():
            return None

        rows = index.row() - self.offsetY
        column = index.column() - self.offsetX

        if rola == Qt.DisplayRole:
            if rows >=0 and column >=0:                                      # Dane
                return self.data[rows][column][0]
            elif column < 0 and rows >= 0 and len(self.rows[0])>0:        # opisy row
                return self.rows[rows+1][column]
            elif rows == -1 and column <0 and len(self.rows[0])>0:        # nazwy row
                return self.rows[0][column]
            elif column >= -1 and rows < 0 and len(self.column[0])>0:       # opisy i nazwy kolumn
                if len(self.rows[0])>0:
                    if rows == -1:                                            # linia przerwy
                        return ''
                    else:
                        return self.column[column+1][rows+1]                # opisy i nazwy kolumn jesli jest linia przerwy
                else:
                    return self.column[column+1][rows]                      # opisy i nazwy kolumn jesli nie ma linii przerwy

        elif rola == Qt.UserRole:
            if rows >=0 and column >=0:                                      # Dane
                return self.data[rows][column][1]

        elif rola == Qt.UserRole+1:
            #print "user role+1"
            if rows <0 and column >=0:                                      # column, rows, czy data
                return "column"
            elif rows >=0 and column <0:
                return "rows"
            elif rows >=0 and column >=0:
                return "data"

        elif rola == Qt.BackgroundRole:                                         # Wypełnienie komórek
            if rows<0 or column<0:                                           # szare dla komórek z opisami i nazwami
                kolor = QColor(245,235,235)
                pedzel = QBrush(kolor)
                return pedzel

        elif rola == Qt.TextAlignmentRole:
            if column < 0 and rows < -1 and len(self.rows[0]) != 0:
                return Qt.AlignRight | Qt.AlignVCenter
            elif column >= 0 and rows < 0:
                return Qt.AlignHCenter | Qt.AlignVCenter
            elif column >= 0 and rows >= 0:
                return Qt.AlignRight | Qt.AlignVCenter

        elif rola == Qt.FontRole:
            if rows<0 and column<0:
                czcionka = QFont()
                czcionka.setBold(True)
                #czcionka.setItalic(True)
                return czcionka

        return None#QVariant()

    def sort(self, column, mode):
        """
        Sortuje tabelę wyników według chosenj column
        column - numer column
        mode - 1-malejąco, inne-rosnąco
        """

        if len(self.rows) == 1:                                              # Jeżeli jest only jeden rows, to nie ma co sortować
            return

        tmp = []                                                                # Tymczasowa lista na posortowaną kolumnę

        if column >= self.offsetX:                                             # Wybranie danych do sortowania
            for n, d in enumerate(self.data):                                   # n-numer rowsa przed stortowniem, d-data w rowsu
                tmp.append((n,d[column-self.offsetX][0]))
        else:                                                                   # lub nazw row
            for n, d in enumerate(self.rows[1:]):                            # n-numer rowsa przed stortowniem, d-opis rowsa
                if str(type(d[column])) != "<type 'float'>":                   # Zamiana tekstu na liczby, jeżeli jest liczbą (aby poprawnie sortowało liczby)
                    try:
                        number = float(d[column])
                    except:
                        test = False
                    else:
                        test = True
                else:
                    test = False

                if test:
                    tmp.append((n,number))
                else:
                    tmp.append((n,d[column]))

        tmp.sort(key=lambda x: x[1])                                            # sortowanie rosnąco
        if mode==1:                                                             # sortowanie malejąco
            tmp.reverse()

        data2 = tuple(self.data)                                                # Tymczasowa krotka ze wszystkomi danymi
        self.data=[]
        rows2=tuple(self.rows)                                            # Tymczasowa krotka z opisami row
        self.rows=[]
        self.rows.append(rows2[0])                                        # Dodanie nazw row (only nazwy, bez opisów row)

        for i in tmp:                                                           # Ułożenie wszystkich danych i opisów row wg tymczasowej listy sortowania
            self.data.append(data2[i[0]])
            self.rows.append(rows2[i[0]+1])

        topLeft = self.createIndex(0,0)                                         # Sygnał zmiany danych
        bottomRight = self.createIndex(self.rowCount(), self.columnCount())
        self.dataChanged.emit(topLeft, bottomRight)


    def sortRows(self, rows, mode):
        """
        Sortuje tabelę wyników według chosengo rowsa
        rows - numer rowsa
        mode - 1-malejąco, inne-rosnąco
        """

        if len(self.column) == 1:                                              # Jeżeli jest only jedna column, to nie ma co sortować
            return                                                              # (self.column są wtedy następującą listą [(),])

        tmp = []                                                                # Tymczasowa lista na posortowany rows

        if rows >= self.offsetY:                                              # Wybranie danych do sortowania
            for n, d in enumerate(self.data[rows-self.offsetY]):              # n-numer column przed stortowniem, d-data w kolumnie
                tmp.append((n,d[0]))
        else:                                                                   # lub nazw kolumn
            for n, d in enumerate(self.column[1:]):                            # n-numer column przed stortowniem, d-opis column
                if str(type(d[rows])) != "<type 'float'>":                    # Zamiana tekstu na liczby, jeżeli jest liczbą (aby poprawnie sortowało liczby)
                    try:
                        number = float(d[rows])
                    except:
                        test = False
                    else:
                        test = True
                else:
                    test = False

                if test:
                    tmp.append((n,number))
                else:
                    tmp.append((n,d[rows]))

        tmp.sort(key=lambda x: x[1])                                    # sortowanie rosnąco
        if mode==1:                                                             # sortowanie malejąco
            tmp.reverse()

        data2 = tuple(self.data)                                                # Tymczasowa krotka ze wszystkomi danymi
        self.data=[]
        column2=tuple(self.column)                                            # Tymczasowa krotka z opisami kolumn
        self.column=[]
        self.column.append(column2[0])                                        # Dodanie nazw kolumn (only nazwy, bez opisów kolumn)

        for j in data2:                                                         # Ułożenie wszystkich danych wg tymczasowej listy sortowania
            rows = []
            for i in tmp:
                rows.append(j[i[0]])
            self.data.append(tuple(rows))

        for i in tmp:                                                           # Ułożenie opisów kolumn wg tymczasowej listy sortowania
            self.column.append(column2[i[0]+1])

        topLeft = self.createIndex(0,0)                                         # Sygnał zmiany danych
        bottomRight = self.createIndex(self.rowCount(), self.columnCount())
        self.dataChanged.emit(topLeft, bottomRight)


class WindowResults(QTableView):
    """
    Okno z wynikami calculations
    """

    def __init__(self, parent=None):
        super(WindowResults, self).__init__(parent)

        self.setSortingEnabled(True)
        self.setObjectName("result")
        self.verticalHeader().setSortIndicatorShown(True)

        self.clicked.connect(self.selectAll)


    def selectionCommand (self, index, event=None ):
        """
        Implementacja oryginalnej metody - dodaje zaznaczanie całych row i kolumn gdy zaznaczono nagłówek tabeli
        """
        flag = super(WindowResults, self).selectionCommand (index, event)        # wywołanie oryginalnej metody
        test = self.model().data(index, Qt.UserRole+1)                         # sprawdzenie typu zaznaczonej komórki
        if test == "rows":
            return flag | QItemSelectionModel.Rows
        elif test == "column":
            return flag | QItemSelectionModel.Columns
        else:
            return flag


    def selectAll (self,index):
        """
        Zaznacznie lub odznaczanie wszystkich danych po kliknięciu w narożniku tabeli
        """
        test = self.model().data(index, Qt.UserRole+1)                         # sprawdzenie typu zaznaczonej komórki
        if test not in ("data", "rows", "column"):                           # sprawdzenie czy narożnik
            if self.selectionModel().isSelected(index):                        # jeżeli zaznaczono narożnik to zaznacza też wszystkie data
                self.selectAll()
            else:
                self.clearSelection ()                                          # odznacza wszystkie data


class Calculations(QObject):                   # finished
    """
    A class that suppresses functions that perform statistical calculations
    """

    def __init__(self, parent):                                                                            # Lista z ID, nazwą i funkcją calculateająca
        super(Calculations, self).__init__(parent)

                                                                                                    # Do not change the function ID! (used for conditions)
        self.list = {0:(QCoreApplication.translate('Calculations', 'count'), self.count),
                     1:(QCoreApplication.translate('Calculations','sum'), self.sum),
                     2:(QCoreApplication.translate('Calculations','average'), self.average),
                     3:(QCoreApplication.translate('Calculations','variance'), self.variance),
                     4:(QCoreApplication.translate('Calculations','stand.dev.'), self.stand_dev),
                     5:(QCoreApplication.translate('Calculations','median'), self.median),
                     6:(QCoreApplication.translate('Calculations','min'), self.minimum),
                     7:(QCoreApplication.translate('Calculations','max'), self.maximum),
                     8:(QCoreApplication.translate('Calculations','unique'), self.unique)}

        self.textList = (0, 8)                                                                        # Calculations also working on text

        self.textNames = ''
        for i in self.textList:
            self.textNames = self.textNames + self.list[i][0] + ', '

        self.textNames = self.textNames[:-2]

    def count(self, result):
        return len(result)

    def sum(self, result):
        return sum(result)

    def average(self, result):
        return self.sum(result)/self.count(result)

    def variance(self, result):
        _variance = 0
        for x in result:
            _variance = _variance + (x-self.average(result))**2
        return _variance/self.count(result)

    def stand_dev(self, result):
        return sqrt(self.variance(result))

    def median(self, result):
        result.sort()
        count = self.count(result)
        if count == 1:
            median = result[0]
        else:
            position = int(count / 2)
            if count%2 == 0:
                median = (result[position]+result[position-1])/2
            else:
                median = result[position]
        return median

    def minimum(self, result):
        return min(result)

    def maximum(self, result):
        return max(result)

    def unique(self, result):
        return len(set(result))

