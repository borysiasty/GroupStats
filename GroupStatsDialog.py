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

        self.ui.wyniki = OknoWyniki(self.ui.centralwidget)

        self.ui.horizontalLayout.addWidget(self.ui.wyniki)

        self.obliczenia = Obliczenia(self)

        self.ui.listaPol.setAcceptDrops(True)
        self.ui.listaPol.setModelColumn(2)

        self.ui.wiersze.setAcceptDrops(True)
        self.ui.kolumny.setAcceptDrops(True)
        self.ui.wartosci.setAcceptDrops(True)

        self.ui.oblicz.clicked.connect(self.pokazWynik)
        self.ui.wyczysc.clicked.connect(self.wyczyscWybor)
        self.ui.filtrButton.clicked.connect(self.ustawFiltr)
        self.ui.warstwa.currentIndexChanged.connect(self.wyborWarstwy)   # Sygnał wyboru warstwy

        slownikPol =  {'atrybutyTxt':[('Rejon',1), ('Posterunek',2)],
                    'atrybutyLicz':[('Moc stacji', 3)],
                    'geometria':[('Dlugosc', 1), ('Powierzchnia', 2)],
                    'obliczenia':[('Liczebnosc', 1), ('Suma', 2), ('Srednia', 3), ('Odchylenie statystyczne', 4)]}

        self.tm1 = ModelListaPol(self)
        self.ui.listaPol.setModel(self.tm1)

        self.tm2 = ModelWiK(self)
        #tm2.ustawInneModele(tm1)
        self.ui.wiersze.setModel(self.tm2)

        self.tm3 = ModelWiK(self)
        #tm3.ustawInneModele(tm1)
        self.ui.kolumny.setModel(self.tm3)

        self.tm4 = ModelWartosci(self)
        self.ui.wartosci.setModel(self.tm4)

        self.tm2.ustawInneModele(self.tm3, self.tm4)
        self.tm3.ustawInneModele(self.tm2, self.tm4)
        self.tm4.ustawInneModele(self.tm2, self.tm3)

        self.tm2.rowsInserted.connect(self.blokujObliczenia)   # Sygnał wyboru warstwy
        self.tm3.rowsInserted.connect(self.blokujObliczenia)   # Sygnał wyboru warstwy
        self.tm4.rowsInserted.connect(self.blokujObliczenia)   # Sygnał wyboru warstwy
        self.tm2.rowsRemoved.connect(self.blokujObliczenia)   # Sygnał wyboru warstwy
        self.tm3.rowsRemoved.connect(self.blokujObliczenia)   # Sygnał wyboru warstwy
        self.tm4.rowsRemoved.connect(self.blokujObliczenia)   # Sygnał wyboru warstwy

        self.ui.actionKopiuj.triggered.connect(self.kopiowanie)   # Sygnał wyboru warstwy
        self.ui.actionKopiujZaznaczone.triggered.connect(self.kopiowanieZaznaczonych)   # Sygnał wyboru warstwy
        self.ui.actionZapiszCSV.triggered.connect(self.eksportCSV)   # Sygnał wyboru warstwy
        self.ui.actionZapiszCSVZaznaczone.triggered.connect(self.eksportCSVZaznaczonych)   # Sygnał wyboru warstwy
        self.ui.actionPokazPanel.triggered.connect(self.pokazPanelSterowania)   # Sygnał wyboru warstwy
        self.ui.actionPokazNaMapie.triggered.connect(self.pokazNaMapie)   # Sygnał wyboru warstwy
        self.ui.actionTutorial.triggered.connect(self.pokazTutorial)   # Sygnał wyboru warstwy

        self.ui.wyniki.verticalHeader().sortIndicatorChanged.connect(self.sortRows)   # Sygnał wyboru warstwy


    def sortRows(self,wiersz,tryb):
            self.ui.wyniki.model().sortRows(wiersz,tryb)


    def blokujObliczenia(self, x, y, z): #gotowe
        wartosci = self.tm4.dane
        kolumny = self.tm3.dane
        wiersze = self.tm2.dane
        # Jeżeli w polu wartości są liczby (atrybuty lub geometria) i wybrano jakąś funcję obliczającą
        if  ('geometria' in [a[0] for a in wartosci] or 'atrybutyLicz' in [a[0] for a in wartosci]) and\
            'obliczenia' in [a[0] for a in wartosci+wiersze+kolumny]:
            self.ui.oblicz.setEnabled(True)
        # Jeżeli w polu wartości jest atrybut tekstowy i wybrano dokładnie jedną funkcję - licznik
        elif 'atrybutyTxt' in [a[0] for a in wartosci] and len([a for a in wartosci+wiersze+kolumny if a[0]=='obliczenia'])>0:
            if set([a[2] for a in wartosci+wiersze+kolumny if a[0]=='obliczenia']).issubset(set(self.obliczenia.listaText)): #[a for a in wartosci+wiersze+kolumny if a[0]=='obliczenia'][0][2]==0:
                self.ui.oblicz.setEnabled(True)
        else:
            self.ui.oblicz.setEnabled(False)


    def pokazWynik(self):               #gotowe
        "Wykonuje obliczenia i wysyła je do wyswietlenia"

        wybraneWiersze = tuple(self.tm2.dane)                                               # Sczytanie z okna wybranych wierszy
        wybraneKolumny = tuple(self.tm3.dane)                                               # Sczytanie z okna wybranych kolumn
        wybraneWartosciiObl = tuple(self.tm4.dane)                                          # Sczytanie z okna wybranej wartosci i obliczenia

        wartosc = [x for x in wybraneWartosciiObl if x[0]!='obliczenia'][0]                 # Sczytanie pola, które zostało wybrane do obliczeń (moe być tylko jedno)
        if wartosc[0]=='geometria':                                                         # Ustawienie funkcji obliczającej w zależności od typu wybranej wartości
            if wartosc[2]==1:
                wartoscFunkcja = lambda obiekt: obiekt.geometry().length()                  # długość
            elif wartosc[2]==2:
                wartoscFunkcja = lambda obiekt: obiekt.geometry().area()                    # powierzchnia
        elif wartosc[0]=='atrybutyTxt':
            wartoscFunkcja = lambda obiekt: None if obiekt.attribute(wartosc[1])==None else obiekt.attribute(wartosc[1])#.toString()    # atrybut tekstowy
        elif wartosc[0]=='atrybutyLicz':
            wartoscFunkcja = lambda obiekt: None if obiekt.attribute(wartosc[1])==None else float(obiekt.attribute(wartosc[1]))         #.toReal()[0]   # atrybut liczbowy (toReal daje wynik (real, True/False))

        indeks = self.ui.warstwa.currentIndex()                                             # Pobranie wybranej warstwy
        idWarstwy = self.ui.warstwa.itemData(indeks)
        warstwa = QgsProject.instance().mapLayer(idWarstwy)#.toString())

        warstwaTemp = QgsVectorLayer(warstwa.source(), warstwa.name(), warstwa.providerType())
        warstwaTemp.setCrs(warstwa.crs())
        filtr = self.ui.filtr.toPlainText()
        filtrWarstwy = warstwa.subsetString()
        if filtrWarstwy == '' and filtr != '':
            warstwaTemp.setSubsetString (filtr)
        elif filtrWarstwy != '' and filtr != '':
            warstwaTemp.setSubsetString ('(%s) and (%s)' % (filtr, filtrWarstwy))

        provider = warstwaTemp.dataProvider()
        iterator = provider.getFeatures()

        if self.ui.tylkoZaznaczone.isChecked():                                         # Pobranie ID zaznaczonych obiektów
            zaznaczoneObiekty = warstwa.selectedFeatureIds()
            tylkoZaznaczone = True
        else:
            zaznaczoneObiekty = []
            tylkoZaznaczone = False

        wyniki = {}                                                                         # Słownik na wyniki {((wiersz)(kolumna)):[[wartosci],[indeksy]}
        f=QgsFeature()                                                                      # Wyszukiwanie danych do obliczeń
        liczbaObiektow = provider.featureCount()
        if liczbaObiektow != 0:
            procent = 100.00 / liczbaObiektow                                                   # Liczba obiektów
        else:
            procent = 100
        licznik = 0.0
        licznikNULL = 0
        while iterator.nextFeature(f):                                                      # dla każdego obiektu...
            if tylkoZaznaczone==False or (tylkoZaznaczone and (f.id() in zaznaczoneObiekty)):

                klucz_kol = []                                                                  # klucz kolumny (kolumna1, kolumna2...)
                klucz_wie = []                                                                  # klucz wierszy (wiersz1, wiersze2...)
                klucz = ()
                for k in wybraneKolumny:                                                        # dla każdej wybranej kolumny sprawdzamy typ kolumny
                    if k[0]=='geometria':                                                       # i tworzymy klucz kolumny
                        if k[2]==1:
                            klucz_kol.append(f.geometry().length())
                        elif k[2]==2:
                            klucz_kol.append(f.geometry().area())
                    elif k[0]=='atrybutyTxt' or k[0]=='atrybutyLicz':
                        if f.attribute(k[1]) == None:
                            nowyKluczKolumny = ''
                        else:
                            nowyKluczKolumny = f.attribute(k[1])

                        klucz_kol.append(nowyKluczKolumny)#.toString())
                for k in wybraneWiersze:                                                        # dla każdego wybranego wiersza sprawdzmy typ wiersza
                    if k[0]=='geometria':                                                       # i tworzymy klucz wiersza
                        if k[2]==1:
                            klucz_wie.append(f.geometry().length())
                        elif k[2]==2:
                            klucz_wie.append(f.geometry().area())
                    elif k[0]=='atrybutyTxt' or k[0]=='atrybutyLicz':
                        if f.attribute(k[1]) == None:
                            nowyKluczWiersza = ''
                        else:
                            nowyKluczWiersza = f.attribute(k[1])

                        klucz_wie.append(nowyKluczWiersza)

                klucz = ( tuple(klucz_wie) , tuple(klucz_kol) )                                 # klucz do identyfikacji grup obiektów

                wartoscDoObliczen = wartoscFunkcja(f)
                if wartoscDoObliczen!=None or self.ui.useNULL.isChecked():
                    if  wartoscDoObliczen==None:
                        licznikNULL += 1
                        if wartosc[0]=='atrybutyLicz':
                            wartoscDoObliczen=0

                    if klucz in wyniki:
                        wyniki[klucz][0].append(wartoscDoObliczen)                                     # jeśli klucz istnieje to dadawana jest nowa wartosc do listy
                    else:
                        wyniki[klucz] = [[wartoscDoObliczen],[]]                                         # jeśli klucz nie istnieje to jest tworona nowa lista

                    wyniki[klucz][1].append(f.id())
                else:
                    licznikNULL += 1

                licznik = licznik + procent
                self.statusBar().showMessage(QCoreApplication.translate('GroupStats','Calculate... ') + '%.0f%%' % (licznik))         # Wyświetlenie postępu

        self.statusBar().showMessage(self.statusBar().currentMessage() + ' |  ' + QCoreApplication.translate('GroupStats','generate view...'))

        klucze = wyniki.keys()                                                              # Znalezienie unikalnych kluczy wierszy i kolumn (osobno)
        wier = set([])
        kolu = set([])
        for z in klucze:                                                                    # dodanie kluczy do zbiorów, aby odrzucić powtórzenia
            wier.add(z[0])
            kolu.add(z[1])
        wiersze = list(wier)                                                                # lista unikalnych kluczy wierszy
        kolumny = list(kolu)                                                                # lista unikalnych kluczy kolumn

        wierSlownik={}                                                                      # Stworzenie słowników dla wierszy i kolumn (szybsze wyszukiwanie)
        for nr, wie in enumerate(wiersze):
            wierSlownik[wie]=nr
        kolSlownik={}
        for nr, kol in enumerate(kolumny):
            kolSlownik[kol]=nr

        obliczenia = [[x[2] for x in wybraneWartosciiObl if x[0]=='obliczenia'],            # lista wybranych obliczeń w wartościach, wierszach i kolumnach
                      [x[2] for x in wybraneWiersze      if x[0]=='obliczenia'],
                      [x[2] for x in wybraneKolumny      if x[0]=='obliczenia']]

        if len(obliczenia[0])!=0:                                                           # Wzięcie do obliczeń tylko niepustej części listy powyżej
            obliczenie = obliczenia[0]
        elif len(obliczenia[1])!=0:
            obliczenie = obliczenia[1]
        else:
            obliczenie = obliczenia[2]

        dane = []                                                                           # Stworzenie pustej tablicy na dane (l.wierszy x l.kolumn)
        for x in range( max( len(wiersze) , len(wiersze)*len(obliczenia[1]))):
            dane.append(max(len(kolumny),len(kolumny)*len(obliczenia[2]))*[('',())])

        for x in klucze:                                                                    # Obliczenie wartości dla wszystkich kluczy
            nrw = wierSlownik[x[0]]                                                         # nr wiersza w tabeli danych dla wybranego klucza
            nrk = kolSlownik[x[1]]                                                          # nr kolumny w tabeli danych dla wybranego klucza
            for n,y in enumerate(obliczenie):                                                       # wykonanie wszystkich obliczeń dla wszystkich kluczy
                if len(obliczenia[1])>0:
                    dane[nrw*len(obliczenia[1])+n][nrk] = [self.obliczenia.lista[y][1](wyniki[x][0]),wyniki[x][1]]    # wstawienie wyniku jeśli obliczenia z wierszy
                elif len(obliczenia[2])>0:
                    dane[nrw][nrk*len(obliczenia[2])+n] = [self.obliczenia.lista[y][1](wyniki[x][0]),wyniki[x][1]]    # wstawienie wyniku jeśli obliczenia z kolumn
                else:
                    dane[nrw][nrk] = [self.obliczenia.lista[y][1](wyniki[x][0]),wyniki[x][1]]                         # wstawienie wyniku jeśli obliczenia z wartosci

        atr = {}                                                                            # Attributes as dict.
        for i in range(provider.fields().count()):
            atr[i] = provider.fields().at(i)

        nazwyWierszy=[]                                                                     # Lista z nazwami wierszy
        for x in wybraneWiersze:
            if x[0]=='geometria':
                nazwyWierszy.append(x[1])
            elif x[0]!='obliczenia':
                nazwyWierszy.append(atr[x[2]].name())
        nazwyKolumn=[]                                                                      # Lista z nazwami kolumn
        for x in wybraneKolumny:
            if x[0]=='geometria':
                nazwyKolumn.append(x[1])
            elif x[0]!='obliczenia':
                nazwyKolumn.append(atr[x[2]].name())

        nazwaKolumnyObiczen=()                                                              # Wstawienie nazw wierszy i kolumn z obliczeniami
        nazwaWierszaObliczen=()
        if len(obliczenia[1])>0:
            obl = [self.obliczenia.lista[x][0] for x in obliczenia[1]]
            wiersze1 = [w+(o,) for w in wiersze for o in obl]
            kolumny1 = kolumny
            nazwaWierszaObliczen=(QCoreApplication.translate('GroupStats','Function'),)
        elif len(obliczenia[2])>0:
            obl = [self.obliczenia.lista[x][0] for x in obliczenia[2]]
            kolumny1 = [w+(o,) for w in kolumny for o in obl]
            wiersze1 = wiersze
            nazwaKolumnyObiczen=(QCoreApplication.translate('GroupStats','Function'),)
        else:
            kolumny1 = kolumny
            wiersze1 = wiersze
        if len(wiersze1)>0 and len(wiersze1[0])>0:
            wiersze1.insert(0,tuple(nazwyWierszy)+nazwaWierszaObliczen)
        if len(kolumny1)>0 and len(kolumny1[0])>0:
            kolumny1.insert(0,tuple(nazwyKolumn)+nazwaKolumnyObiczen)


        if len(wiersze1)>0 and len(kolumny1)>0:
            self.ui.wyniki.setUpdatesEnabled(False)
            self.tm5 = ModelWyniki(dane, wiersze1, kolumny1, warstwa)
            self.ui.wyniki.setModel(self.tm5)
            for i in range(len(kolumny1[0]),0,-1):
                self.ui.wyniki.verticalHeader().setSortIndicator( i-1, Qt.AscendingOrder )
            for i in range(len(wiersze1[0]),0,-1):
                self.ui.wyniki.horizontalHeader().setSortIndicator( i-1, Qt.AscendingOrder )
            komunikat = self.statusBar().currentMessage()
            procent = 100.00 / self.tm5.columnCount()
            licznik = 0
            for i in range(self.tm5.columnCount()):
                self.ui.wyniki.resizeColumnToContents(i)
                licznik = licznik + procent
                self.statusBar().showMessage(komunikat + '%.0f%%' % (licznik))

            self.ui.wyniki.setUpdatesEnabled(True)

            if licznikNULL==1:
                rekordy='record'
            else:
                rekordy='records'

            if self.ui.useNULL.isChecked() and licznikNULL>0:
                tekstNULL = QCoreApplication.translate('GroupStats','  (used %s %s with null value in "%s" field)' % (licznikNULL, rekordy, wartosc[1]))
            elif self.ui.useNULL.isChecked()==False and licznikNULL>0:
                tekstNULL = QCoreApplication.translate('GroupStats','  (not used %s %s with null value in "%s" field)' % (licznikNULL, rekordy, wartosc[1]))
            else:
                tekstNULL = ''

            self.statusBar().showMessage(self.statusBar().currentMessage() + ' |  ' + QCoreApplication.translate('GroupStats','done.')+tekstNULL, 20000)

        else:
            try:
                del(self.tm5)
            except AttributeError:
                pass

            self.statusBar().showMessage(QCoreApplication.translate('GroupStats','No data found.'), 10000)


    def ustawWarstwy (self, warstwy):   #gotowe
        "Dodaje dostępne wartwy do listy wyboru w oknie"

        indeks = self.ui.warstwa.currentIndex()
        if indeks !=-1:
            idWarstwy = self.ui.warstwa.itemData(indeks)                        # id wcześniej wybranej warstwy

        self.ui.warstwa.blockSignals(True)
        self.ui.warstwa.clear()                                                 # wypełnienie comboBoxa nową listą warstw
        warstwy.sort(key=lambda x: x[0].lower())
        for i in warstwy:
            self.ui.warstwa.addItem(i[0], i[1])

        if indeks !=-1:
            indeks2 = self.ui.warstwa.findData(idWarstwy)                       # jeżeli wcześniej wybrana warstwa jest to liście to wybranie jej
            if indeks2 !=-1:
                self.ui.warstwa.setCurrentIndex(indeks2)
            else:
                self.wyborWarstwy(0)                                            # jeśli nie ma to wybranie pierwszej
        else:
            self.wyborWarstwy(0)
        self.ui.warstwa.blockSignals(False)


    def wyborWarstwy(self, indeks):     #gotowe
        "Uruchamiane po wybraniu warstwy z listy. Ustawia nową listę pól do wyboru i kasuje okna z już wybranymi polami"

        idW = self.ui.warstwa.itemData(indeks)                          # Pobranie ID wybranej warstwy
        warstwa = QgsProject.instance().mapLayer(idW)#.toString())
        provider = warstwa.dataProvider()
        fields = provider.fields()

        slownikPol = {}
        if warstwa.geometryType() in (QgsWkbTypes.PointGeometry, QgsWkbTypes.NullGeometry):
            slownikPol['geometria'] =  []
        elif warstwa.geometryType() == QgsWkbTypes.LineGeometry:                             # line
            slownikPol ['geometria'] = [(QCoreApplication.translate('GroupStats','Length'), 1)]
        elif warstwa.geometryType() == QgsWkbTypes.PolygonGeometry:                             # polygon
            slownikPol ['geometria'] = [(QCoreApplication.translate('GroupStats','Perimeter'), 1), (QCoreApplication.translate('GroupStats','Area'), 2)]

        slownikPol ['atrybutyLicz'] = []
        slownikPol ['atrybutyTxt'] = []
        for i in range(fields.count()):
            atrybut = fields.at(i)
            if atrybut.typeName().upper() in ('REAL', 'FLOAT4') or atrybut.typeName().upper().startswith('INT'):
                slownikPol['atrybutyLicz'].append((atrybut.name(), i))
            else:
                slownikPol['atrybutyTxt'].append((atrybut.name(), i))

        slownikPol['obliczenia']=[]
        obl = self.obliczenia.lista
        for c,b in obl.items():
            slownikPol['obliczenia'].append((b[0],c))

        del(self.tm1)
        self.tm1 = ModelListaPol()
        self.ui.listaPol.setModel(self.tm1)
        klucze = ['obliczenia', 'geometria']
        for i in klucze:
            j = slownikPol[i]
            j.sort(key=lambda x: x[0].lower())
            wiersze=[]
            for k, l in j:
                wiersze.append((i,k,l))
            self.tm1.insertRows( 0, len(wiersze), QModelIndex(), wiersze)

        klucze = ['atrybutyLicz', 'atrybutyTxt']
        wiersze=[]
        for i in klucze:
            j = slownikPol[i]
            for k, l in j:
                wiersze.append((i,k,l))

        wiersze.sort(key=lambda x: x[1].lower())
        self.tm1.insertRows( 0, len(wiersze), QModelIndex(), wiersze)

        self.wyczyscWybor()


    def wyczyscWybor(self):             # gotowe
        " Czyści okna z wybranymi wierszami, kolumnami i wartościami"
        self.tm2.removeRows(0, self.tm2.rowCount() ,QModelIndex())
        self.tm3.removeRows(0, self.tm3.rowCount() ,QModelIndex())
        self.tm4.removeRows(0, self.tm4.rowCount() ,QModelIndex())
        self.ui.filtr.setPlainText('')


    def pokazPanelSterowania(self):     # gotowe
        ""

        self.ui.panelSterowania.setVisible(True)

    def pokazTutorial(self):
        url = "http://underdark.wordpress.com/2013/02/02/group-stats-tutorial/"
        webbrowser.open (url, 2)

    def ustawFiltr(self):               # gotowe 2
        indeks = self.ui.warstwa.currentIndex()                                             # Pobranie wybranej warstwy
        idWarstwy = self.ui.warstwa.itemData(indeks)
        warstwa = QgsProject.instance().mapLayer(str(idWarstwy))

        tekst = self.ui.filtr.toPlainText()                                                 # Pobranie tekstu z okna i wyświetlenie okna zapytań
        q = QgsSearchQueryBuilder(warstwa)
        q.setSearchString(tekst)
        q.exec_()

        self.ui.filtr.setPlainText(q.searchString ())                                       # Wstawienie zapytania do okna

    # ------------------------ KOPIOWANIE DANYCH DO SCHOWKA I ZAPIS CSV ----------------------------START

    def kopiowanie (self):
        "Kopiowanie wszystkich danych do schowka"
        tekst, test = self.pobierzDaneZTabeli(True, True)
        if test==True:
            schowek = QApplication.clipboard()
            schowek.setText(tekst)

    def kopiowanieZaznaczonych (self):
        "Kopiowanie zaznaczonych danych do schowka"
        tekst, test = self.pobierzDaneZTabeli(False, True)
        if test==True:
            schowek = QApplication.clipboard()
            schowek.setText(tekst)

    def eksportCSV (self):
        "Zapisuje wszystkie dane do pliku CSV"
        dane, test = self.pobierzDaneZTabeli(True, False)
        if test==True:
            self.zapiszDaneWPliku(dane)

    def eksportCSVZaznaczonych (self):
        "Zapisuje zaznaczone dane do pliku CSV"
        dane, test = self.pobierzDaneZTabeli(False, False)
        if test==True:
            self.zapiszDaneWPliku(dane)

    def zapiszDaneWPliku (self, dane):
        "Obsługa zapisu danych do pliku"
        oknoPlikow = QFileDialog()                                              # Wybór pliku do zapisu
        oknoPlikow.setAcceptMode(1)
        oknoPlikow.setDefaultSuffix("csv")
        oknoPlikow.setNameFilters(["CSV files (*.csv)", "All files (*)"])
        if oknoPlikow.exec_() == 0:                                             # Nie wybrano żadnego pliku - wyjście
            return
        nazwaPliku = oknoPlikow.selectedFiles()[0]
        plik = open(nazwaPliku, 'w')                                           # Otwarcie pliku do zapisu
        plikCSV = csv.writer( plik, delimiter=';' )
        for i in dane:                                                          # Kopiowanie danych z tabeli
            #plikCSV.writerow([bytes(x, 'utf-8') for x in i])
            plikCSV.writerow(i)
        plik.close()

    def pobierzDaneZTabeli(self, wszystkieDane=True, znakiSterujace=False):
        if self.ui.wyniki.model()==None:
            QMessageBox.information(None,QCoreApplication.translate('GroupStats','Information'), \
                QCoreApplication.translate('GroupStats','No data to save/copy'))
            return None, False

        tekst=''
        dane = []
        liczbaKolumn = self.tm5.columnCount()
        liczbaWierszy = self.tm5.rowCount()
        wiersze = []
        kolumny = []

        if wszystkieDane == False:                                                               # Jeśli opcja 'tylko zaznaczone' pobranie indeksów zaznaczonych pól
            listaIndeksow = self.ui.wyniki.selectedIndexes()
            if len(listaIndeksow)==0:
                QMessageBox.information(None,QCoreApplication.translate('GroupStats','Information'), \
                    QCoreApplication.translate('GroupStatsD','No data selected'))
                return None, False
            for i in listaIndeksow:
                wiersze.append(i.row())
                kolumny.append(i.column())

        for i in range(liczbaWierszy):                                                          # Kopiowanie danych z tabeli
            if wszystkieDane or (i in wiersze) or (i < self.tm5.offsetY):
                wiersz = []
                for j in range(liczbaKolumn):
                    if wszystkieDane or (j in kolumny) or (j < self.tm5.offsetX):
                        wiersz.append(unicode(self.tm5.createIndex(i,j).data()))
                dane.append(wiersz)

        if znakiSterujace == True:
            for m, i in enumerate(dane):                                                          # Kopiowanie danych z tabeli
                if m>0:
                    tekst = tekst + chr(13)
                for n, j in enumerate(i):
                    if n>0:
                        tekst = tekst + chr(9)
                    tekst = tekst + j
            return tekst, True
        else:
            return dane, True

    # ------------------------ KOPIOWANIE DANYCH DO SCHOWKA I ZAPIS CSV ----------------------------END



    def pokazNaMapie(self):             # zmienic zeby nie dublowac indeksow z komorek
        listaIndeksow = self.ui.wyniki.selectedIndexes()                                    # Pobranie indeksów zaznaczonych pól
        listaId = []
        for i in listaIndeksow:                                                             # Pobranie indeksów obiektów do pokazania
            lista = i.data(Qt.UserRole)#.toList()
            if lista == None:                                                               # Odrzucenie wierszy z nagłówkami
                lista = ()
            for j in lista:
                listaId.append(j)    #w 1 było listaId.append(j.toInt()[0])

        self.tm5.warstwa.selectByIds(listaId)                                           #   zaznaczenie ich na mapie
        self.iface.mapCanvas().zoomToSelected(self.tm5.warstwa)                         #   zoom do wybranych obiektów
        if len(listaId)==1 and self.tm5.warstwa.geometryType()==0:                      #      jeżeli warstwa jest punktowa i w grupie jest tylko jeden obiekt..
            self.iface.mapCanvas().zoomScale(1000)                                      #      to ustaw skalę na 1:1000



class ModelList(QAbstractListModel):
    """
    Model dla okien z listami atrybutów.
    Dane przechowywane na liście: [ (typ atrybutu, nazwa, id), ... ]
    """

    def __init__(self, oknoGlowne, parent=None):

        super(ModelList, self).__init__(parent)
        self.dane = []
        self.oknoGlowne = oknoGlowne
        self.obliczenia = Obliczenia(self)


    def rowCount(self, parent=QModelIndex):
        return len(self.dane)


    def data(self, indeks, rola=Qt.DisplayRole):
        if not indeks.isValid() or not 0 <= indeks.row() < self.rowCount():
            return None#QVariant()

        wiersz = indeks.row()

        if rola == Qt.DisplayRole:
            return self.dane[wiersz][1]

        #elif rola == Qt.ForegroundRole:
        #    if self.dane[wiersz][0] == 'geometria':
        #        kolor = QColor(0,255,0)
        #    elif self.dane[wiersz][0] == 'obliczenia':
        #        kolor = QColor(255,0,0)
        #    elif self.dane[wiersz][0] == 'atrybutyTxt':
        #        kolor = QColor(150,150,150)
        #    else:
        #        kolor = QColor(0,0,0)   # 'atrybutyLicz'
        #
        #    pedzel = QBrush(kolor)
        #    return pedzel

        elif rola == Qt.DecorationRole:
            if self.dane[wiersz][0] == 'geometria':
                ikona = QIcon(":/plugins/groupstats/icons/geom.png")
            elif self.dane[wiersz][0] == 'obliczenia':
                ikona = QIcon(":/plugins/groupstats/icons/calc.png")
            elif self.dane[wiersz][0] == 'atrybutyTxt':
                ikona = QIcon(":/plugins/groupstats/icons/alpha.png")
            else:
                ikona = QIcon(":/plugins/groupstats/icons/digits.png")

            return ikona

        return None#QVariant()


    def mimeTypes(self):
        return ['application/x-groupstats-polaL', 'application/x-groupstats-polaWK', 'application/x-groupstats-polaW']


    def supportedDragActions(self):
        return Qt.MoveAction


    def supportedDropActions(self):
        return Qt.MoveAction


    def insertRows(self, wiersz, liczba, indeks, dane):
        self.beginInsertRows(indeks, wiersz, wiersz+liczba-1)
        for n in range(liczba):
            self.dane.insert(wiersz+n, dane[n])
        self.endInsertRows()
        return True


    def removeRows(self, wiersz, liczba, indeks):
        self.beginRemoveRows(indeks, wiersz, wiersz+liczba-1)
        del self.dane[wiersz:wiersz+liczba]
        self.endRemoveRows()
        return True


    def mimeData(self, indeksy, typMime='application/x-groupstats-polaL'):
        daneMime = QMimeData()
        dane = QByteArray()
        strumien = QDataStream(dane, QIODevice.WriteOnly)

        for indeks in indeksy:
            wiersz = indeks.row()
            stringg = pickle.dumps(self.dane[wiersz][2])
            #strumien << self.dane[wiersz][0][0] << self.dane[wiersz][1][0]    #----------------------------- ???????[0]poprawic
            # Datatypes below happen to be strings or already bytes! (b'geometria', b'obliczenia' or b'atrybutyTxt' - maybe reused?)

            strumien.writeBytes(bytes(self.dane[wiersz][0], 'utf-8') if isinstance(self.dane[wiersz][0], str) else bytes(self.dane[wiersz][0]))
            strumien.writeBytes(bytes(self.dane[wiersz][1], 'utf-8') if isinstance(self.dane[wiersz][1], str) else bytes(self.dane[wiersz][1]))
            strumien.writeInt16(self.dane[wiersz][2])

        daneMime.setData(typMime, dane)

        return daneMime


    def flags(self, indeks):
        flagi = super(ModelList, self).flags(indeks)

        if indeks.isValid():
            return flagi | Qt.ItemIsDragEnabled | Qt.ItemIsEnabled | Qt.ItemIsSelectable
        else:
            return Qt.ItemIsDropEnabled



class ModelWiK(ModelList):
    """
    Model dla okien z listami pól dla wierszy i kolumn
    """

    def __init__(self, parent):

        super(ModelWiK, self).__init__(parent)
        self.dane = []


    def setData(self, indeks, wartosc):
        self.dane.insert(indeks,wartosc)
        return True


    def ustawInneModele(self, modelWiK, modelWartosci):
        self.modelWiK = modelWiK.dane
        self.modelWartosci = modelWartosci.dane


    def mimeData(self, indeksy):
        return super(ModelWiK, self).mimeData(indeksy, 'application/x-groupstats-polaWK')

    def dropMimeData(self, daneMime, akcja, wiersz, kolumna, indeks):
        if daneMime.hasFormat('application/x-groupstats-polaL'):
            typDanych = 'application/x-groupstats-polaL'
        elif daneMime.hasFormat('application/x-groupstats-polaWK'):
            typDanych = 'application/x-groupstats-polaWK'
        elif daneMime.hasFormat('application/x-groupstats-polaW'):
            typDanych = 'application/x-groupstats-polaW'
        else:
            return False

        dane = daneMime.data(typDanych)
        strumien = QDataStream(dane, QIODevice.ReadOnly)
        daneWy = []
        while not strumien.atEnd():
            #typ = ''#QString() --------------------------------???????????????????????????????????????
            #nazwa = ''#QString()   -------------------------------------??????????????????????????????????????????????
            #strumien >> typ >> nazwa
            typ = strumien.readBytes().decode('utf-8')
            nazwa = strumien.readBytes().decode('utf-8')
            id = strumien.readInt16()
            pole = (typ, nazwa, id)
            daneWKiW = self.modelWiK+self.modelWartosci
            if typ=='obliczenia' and typ in [x[0] for x in daneWKiW] and typDanych == 'application/x-groupstats-polaL':
                self.oknoGlowne.statusBar().showMessage(QCoreApplication.translate('GroupStats','Function can be droped in only one area'),15000)
                return False
            elif (pole in self.modelWiK or pole in self.dane) and typDanych in ['application/x-groupstats-polaL', 'application/x-groupstats-polaW']:
                self.oknoGlowne.statusBar().showMessage(QCoreApplication.translate('GroupStats','This field has already been droped'),15000)
                return False
            #elif (typ != 'obliczenia' and 'obliczenia' in [x[0] for x in self.dane]) or (typ=='obliczenia' and len([x for x in self.dane if (x[0] != 'obliczenia')])>0):
            #    print 'pola obliczeniowe nie moga byc razem z innymi polami'
            #    return False
            elif typ=='obliczenia' and id not in self.obliczenia.listaText and 'atrybutyTxt' in [x[0] for x in self.modelWartosci]:  #nazwa != self.obliczenia.lista[0][0]
                self.oknoGlowne.statusBar().showMessage(QCoreApplication.translate('GroupStats','For the text value function can only be one of (%s)' % self.obliczenia.nazwyText),15000)
                return False

            daneWy.append(pole)

        self.insertRows(wiersz, len(daneWy), indeks, daneWy)

        return True


class ModelWartosci(ModelList):
    """
    Model dla okna z wartosciami do obliczenia
    """

    def __init__(self, parent=None):

        super(ModelWartosci, self).__init__(parent)
        self.dane = []

    def mimeData(self, indeksy):
        return super(ModelWartosci, self).mimeData(indeksy, 'application/x-groupstats-polaW')

    def dropMimeData(self, daneMime, akcja, wiersz, kolumna, indeks):

        if daneMime.hasFormat('application/x-groupstats-polaL'):
            typDanych = 'application/x-groupstats-polaL'
        elif daneMime.hasFormat('application/x-groupstats-polaWK'):
            typDanych = 'application/x-groupstats-polaWK'
        elif daneMime.hasFormat('application/x-groupstats-polaW'):
            typDanych = 'application/x-groupstats-polaW'
        else:
            return False

        dane = daneMime.data(typDanych)
        strumien = QDataStream(dane, QIODevice.ReadOnly)
        daneWy = []
        while not strumien.atEnd():

            #typ = '2'#QString()-------------------------------------????????????????????????????
            #nazwa = '2'#QString()-------------------------------------?????????????????????
            #strumien >> typ >> nazwa
            typ = strumien.readBytes().decode('utf-8')
            nazwa = strumien.readBytes().decode('utf-8')
            id = strumien.readInt16()
            pole = (typ, nazwa, id)

            daneWszystkie = self.modelWiersze+self.modelKolumny+self.dane
            daneWiK = self.modelWiersze+self.modelKolumny
            if len(self.dane)>=2:
                self.oknoGlowne.statusBar().showMessage(QCoreApplication.translate('GroupStats',"Area 'Value' may contain a maximum of two entries"),15000)
                return False
            elif typ=='obliczenia' and typ in [x[0] for x in daneWszystkie] and typDanych == 'application/x-groupstats-polaL':
                self.oknoGlowne.statusBar().showMessage(QCoreApplication.translate('GroupStats','Function can be droped in only one area'),15000)
                return False
            elif len(self.dane)==1 and typ != 'obliczenia' and self.dane[0][0] != 'obliczenia':
                self.oknoGlowne.statusBar().showMessage(QCoreApplication.translate('GroupStats',"In the area 'Value' one of the items must be a function"),15000)
                return False
            elif len(self.dane)==1 and ((typ=='atrybutyTxt' and self.dane[0][2] not in self.obliczenia.listaText) or (id not in self.obliczenia.listaText and self.dane[0][0]=='atrybutyTxt')):
                self.oknoGlowne.statusBar().showMessage(QCoreApplication.translate('GroupStats','For the text value function can only be one of (%s)' % self.obliczenia.nazwyText),15000)
                return False
            elif typ=='atrybutyTxt' and len([x for x in daneWiK if (x[0]=='obliczenia' and x[2] not in self.obliczenia.listaText)])>0:
                self.oknoGlowne.statusBar().showMessage(QCoreApplication.translate('GroupStats','For the text value function can only be one of (%s)' % self.obliczenia.nazwyText),15000)
                return False

            daneWy.append(pole)

        self.insertRows(wiersz, len(daneWy), indeks, daneWy)


        # sprawdzic: co jeśli przy usuwaniu zostanie tylko pole obliczeniowe albo pole wartosci


        return True

    def ustawInneModele(self, modelWiersze, modelKolumny):
        self.modelWiersze = modelWiersze.dane
        self.modelKolumny = modelKolumny.dane


class ModelListaPol(ModelList):
    """
    Model dla okna z listą dostępnych pól
    """

    def __init__(self, parent=None):

        super(ModelListaPol, self).__init__(parent)
        #self.ustawDane(slownikPol)
        self.dane = []



    def dropMimeData(self, daneMime, akcja, wiersz, kolumna, indeks):
        return True


    def removeRows(self, wiersz, liczba, indeks):

        return True


class ModelWyniki(QAbstractTableModel):     # gotowe
    """
    Model dla okna z wynikami obliczeń
    """

    def __init__(self, dane, wiersze, kolumny, warstwa, parent=None):
        super(ModelWyniki, self).__init__(parent)
        self.dane = dane
        self.wiersze = wiersze
        self.kolumny = kolumny
        self.warstwa = warstwa

        self.offsetX = max(1,len(wiersze[0]))                                           # Przesunięcie współrzednych tak, aby dane zaczynały się od 0,0
        self.offsetY = max(1,len(kolumny[0]))

        if len(wiersze[0]) != 0 and len(kolumny[0]) != 0:                               # Przesunięcie o jeden wiersz (pusty) aby zrobić miejsce na nazwy wierszy
                self.offsetY += 1

    def columnCount(self,parent=QModelIndex()):
        if len(self.wiersze[0])>0 and len(self.kolumny[0])>0:
            l = len(self.kolumny)+len(self.wiersze[0])-1
        elif len(self.wiersze[0])>0 and len(self.kolumny[0])==0:
            l = len(self.wiersze[0])+1
        elif len(self.wiersze[0])==0 and len(self.kolumny[0])>0:
            l = len(self.kolumny)
        else:
            l = 2

        return l #max(len(self.wiersze[0])+1,len(self.kolumny)+len(self.wiersze[0]))

    def rowCount(self, parent=QModelIndex()):
        return max(2,len(self.wiersze)+len(self.kolumny[0]))

    def data(self, indeks, rola=Qt.DisplayRole):
        if not indeks.isValid() or not 0 <= indeks.row() < self.rowCount():
            return None

        wiersz = indeks.row() - self.offsetY
        kolumna = indeks.column() - self.offsetX

        if rola == Qt.DisplayRole:
            if wiersz >=0 and kolumna >=0:                                      # Dane
                return self.dane[wiersz][kolumna][0]
            elif kolumna < 0 and wiersz >= 0 and len(self.wiersze[0])>0:        # opisy wierszy
                return self.wiersze[wiersz+1][kolumna]
            elif wiersz == -1 and kolumna <0 and len(self.wiersze[0])>0:        # nazwy wierszy
                return self.wiersze[0][kolumna]
            elif kolumna >= -1 and wiersz < 0 and len(self.kolumny[0])>0:       # opisy i nazwy kolumn
                if len(self.wiersze[0])>0:
                    if wiersz == -1:                                            # linia przerwy
                        return ''
                    else:
                        return self.kolumny[kolumna+1][wiersz+1]                # opisy i nazwy kolumn jesli jest linia przerwy
                else:
                    return self.kolumny[kolumna+1][wiersz]                      # opisy i nazwy kolumn jesli nie ma linii przerwy

        elif rola == Qt.UserRole:
            if wiersz >=0 and kolumna >=0:                                      # Dane
                return self.dane[wiersz][kolumna][1]

        elif rola == Qt.UserRole+1:
            #print "user role+1"
            if wiersz <0 and kolumna >=0:                                      # kolumna, wiersz, czy dane
                return "kolumna"
            elif wiersz >=0 and kolumna <0:
                return "wiersz"
            elif wiersz >=0 and kolumna >=0:
                return "dane"

        elif rola == Qt.BackgroundRole:                                         # Wypełnienie komórek
            if wiersz<0 or kolumna<0:                                           # szare dla komórek z opisami i nazwami
                kolor = QColor(245,235,235)
                pedzel = QBrush(kolor)
                return pedzel

        elif rola == Qt.TextAlignmentRole:
            if kolumna < 0 and wiersz < -1 and len(self.wiersze[0]) != 0:
                return Qt.AlignRight | Qt.AlignVCenter
            elif kolumna >= 0 and wiersz < 0:
                return Qt.AlignHCenter | Qt.AlignVCenter
            elif kolumna >= 0 and wiersz >= 0:
                return Qt.AlignRight | Qt.AlignVCenter

        elif rola == Qt.FontRole:
            if wiersz<0 and kolumna<0:
                czcionka = QFont()
                czcionka.setBold(True)
                #czcionka.setItalic(True)
                return czcionka

        return None#QVariant()

    def sort(self, kolumna, tryb):
        """
        Sortuje tabelę wyników według wybranej kolumny
        kolumna - numer kolumny
        tryb - 1-malejąco, inne-rosnąco
        """

        if len(self.wiersze) == 1:                                              # Jeżeli jest tylko jeden wiersz, to nie ma co sortować
            return

        tmp = []                                                                # Tymczasowa lista na posortowaną kolumnę

        if kolumna >= self.offsetX:                                             # Wybranie danych do sortowania
            for n, d in enumerate(self.dane):                                   # n-numer wiersza przed stortowniem, d-dane w wierszu
                tmp.append((n,d[kolumna-self.offsetX][0]))
        else:                                                                   # lub nazw wierszy
            for n, d in enumerate(self.wiersze[1:]):                            # n-numer wiersza przed stortowniem, d-opis wiersza
                if str(type(d[kolumna])) != "<type 'float'>":                   # Zamiana tekstu na liczby, jeżeli jest liczbą (aby poprawnie sortowało liczby)
                    try:
                        liczba = float(d[kolumna])
                    except:
                        test = False
                    else:
                        test = True
                else:
                    test = False

                if test:
                    tmp.append((n,liczba))
                else:
                    tmp.append((n,d[kolumna]))

        tmp.sort(key=lambda x: x[1])                                            # sortowanie rosnąco
        if tryb==1:                                                             # sortowanie malejąco
            tmp.reverse()

        dane2 = tuple(self.dane)                                                # Tymczasowa krotka ze wszystkomi danymi
        self.dane=[]
        wiersze2=tuple(self.wiersze)                                            # Tymczasowa krotka z opisami wierszy
        self.wiersze=[]
        self.wiersze.append(wiersze2[0])                                        # Dodanie nazw wierszy (tylko nazwy, bez opisów wierszy)

        for i in tmp:                                                           # Ułożenie wszystkich danych i opisów wierszy wg tymczasowej listy sortowania
            self.dane.append(dane2[i[0]])
            self.wiersze.append(wiersze2[i[0]+1])

        topLeft = self.createIndex(0,0)                                         # Sygnał zmiany danych
        bottomRight = self.createIndex(self.rowCount(), self.columnCount())
        self.dataChanged.emit(topLeft, bottomRight)


    def sortRows(self, wiersz, tryb):
        """
        Sortuje tabelę wyników według wybranego wiersza
        wiersz - numer wiersza
        tryb - 1-malejąco, inne-rosnąco
        """

        if len(self.kolumny) == 1:                                              # Jeżeli jest tylko jedna kolumna, to nie ma co sortować
            return                                                              # (self.kolumny są wtedy następującą listą [(),])

        tmp = []                                                                # Tymczasowa lista na posortowany wiersz

        if wiersz >= self.offsetY:                                              # Wybranie danych do sortowania
            for n, d in enumerate(self.dane[wiersz-self.offsetY]):              # n-numer kolumny przed stortowniem, d-dane w kolumnie
                tmp.append((n,d[0]))
        else:                                                                   # lub nazw kolumn
            for n, d in enumerate(self.kolumny[1:]):                            # n-numer kolumny przed stortowniem, d-opis kolumny
                if str(type(d[wiersz])) != "<type 'float'>":                    # Zamiana tekstu na liczby, jeżeli jest liczbą (aby poprawnie sortowało liczby)
                    try:
                        liczba = float(d[wiersz])
                    except:
                        test = False
                    else:
                        test = True
                else:
                    test = False

                if test:
                    tmp.append((n,liczba))
                else:
                    tmp.append((n,d[wiersz]))

        tmp.sort(key=lambda x: x[1])                                    # sortowanie rosnąco
        if tryb==1:                                                             # sortowanie malejąco
            tmp.reverse()

        dane2 = tuple(self.dane)                                                # Tymczasowa krotka ze wszystkomi danymi
        self.dane=[]
        kolumny2=tuple(self.kolumny)                                            # Tymczasowa krotka z opisami kolumn
        self.kolumny=[]
        self.kolumny.append(kolumny2[0])                                        # Dodanie nazw kolumn (tylko nazwy, bez opisów kolumn)

        for j in dane2:                                                         # Ułożenie wszystkich danych wg tymczasowej listy sortowania
            wiersz = []
            for i in tmp:
                wiersz.append(j[i[0]])
            self.dane.append(tuple(wiersz))

        for i in tmp:                                                           # Ułożenie opisów kolumn wg tymczasowej listy sortowania
            self.kolumny.append(kolumny2[i[0]+1])

        topLeft = self.createIndex(0,0)                                         # Sygnał zmiany danych
        bottomRight = self.createIndex(self.rowCount(), self.columnCount())
        self.dataChanged.emit(topLeft, bottomRight)


class OknoWyniki(QTableView):
    """
    Okno z wynikami obliczeń
    """

    def __init__(self, parent=None):
        super(OknoWyniki, self).__init__(parent)

        self.setSortingEnabled(True)
        self.setObjectName("wyniki")
        self.verticalHeader().setSortIndicatorShown(True)

        self.clicked.connect(self.zaznaczWszystko)


    def selectionCommand (self, indeks, event=None ):
        """
        Implementacja oryginalnej metody - dodaje zaznaczanie całych wierszy i kolumn gdy zaznaczono nagłówek tabeli
        """
        flagi = super(OknoWyniki, self).selectionCommand (indeks, event)        # wywołanie oryginalnej metody
        test = self.model().data(indeks, Qt.UserRole+1)                         # sprawdzenie typu zaznaczonej komórki
        if test == "wiersz":
            return flagi | QItemSelectionModel.Rows
        elif test == "kolumna":
            return flagi | QItemSelectionModel.Columns
        else:
            return flagi


    def zaznaczWszystko (self,indeks):
        """
        Zaznacznie lub odznaczanie wszystkich danych po kliknięciu w narożniku tabeli
        """
        test = self.model().data(indeks, Qt.UserRole+1)                         # sprawdzenie typu zaznaczonej komórki
        if test not in ("dane", "wiersz", "kolumna"):                           # sprawdzenie czy narożnik
            if self.selectionModel().isSelected(indeks):                        # jeżeli zaznaczono narożnik to zaznacza też wszystkie dane
                self.selectAll()
            else:
                self.clearSelection ()                                          # odznacza wszystkie dane



class Obliczenia(QObject):                   # gotowe
    """
    Klasa zawierająca funkcje dokonujące obliczeń statystycznych
    """

    def __init__(self, parent):                                                                            # Lista z ID, nazwą i funkcją obliczająca
        super(Obliczenia, self).__init__(parent)
                                                                                                            # Nie zmieniać ID funkcji! (są używane do warunków)
        self.lista = {  0:(QCoreApplication.translate('Obliczenia','count'), self.liczebnosc),
                        1:(QCoreApplication.translate('Obliczenia','sum'), self.suma),
                        2:(QCoreApplication.translate('Obliczenia','average'), self.srednia),
                        3:(QCoreApplication.translate('Obliczenia','variance'), self.wariancja),
                        4:(QCoreApplication.translate('Obliczenia','stand.dev.'), self.odchylenie),
                        5:(QCoreApplication.translate('Obliczenia','median'), self.mediana),
                        6:(QCoreApplication.translate('Obliczenia','min'), self.minimum),
                        7:(QCoreApplication.translate('Obliczenia','max'), self.maksimum),
                        8:(QCoreApplication.translate('Obliczenia','unique'), self.unikalne) }

        self.listaText = (0,8)                                                                        # Obliczenia działające również na tekście

        self.nazwyText = ''
        for i in self.listaText:
            self.nazwyText = self.nazwyText + self.lista[i][0] + ', '

        self.nazwyText = self.nazwyText[:-2]

    def liczebnosc(self, wyniki):
        return len(wyniki)

    def suma(self, wyniki):
        return sum(wyniki)

    def srednia(self, wyniki):
        return self.suma(wyniki)/self.liczebnosc(wyniki)

    def wariancja(self, wyniki):
        wariancja = 0
        for x in wyniki:
            wariancja = wariancja + (x-self.srednia(wyniki))**2
        return wariancja/self.liczebnosc(wyniki)

    def odchylenie(self, wyniki):
        return sqrt(self.wariancja(wyniki))

    def mediana(self, wyniki):
        wyniki.sort()
        liczebnosc = self.liczebnosc(wyniki)
        if liczebnosc == 1:
            mediana = wyniki[0]
        else:
            pozycja = int(liczebnosc / 2)
            if liczebnosc%2 == 0:
                mediana = (wyniki[pozycja]+wyniki[pozycja-1])/2
            else:
                mediana = wyniki[pozycja]
        return mediana

    def minimum(self, wyniki):
        return min(wyniki)

    def maksimum(self, wyniki):
        return max(wyniki)

    def unikalne(self, wyniki):
        return len(set(wyniki))

