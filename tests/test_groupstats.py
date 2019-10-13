from qgis.core import QgsProject, QgsVectorLayer, QgsField, QgsFeature, QgsFields
from PyQt5.QtCore import QVariant, QModelIndex
import mock
from mock import call
from io import TextIOBase
from groupstats import GroupStats

class TestGroupStats(object):

    def setUp(self):
        pass

    def create_vectorlayer(self, _fields, data):
        self.vlayer = QgsVectorLayer("Point?crs=epsg:4326", "test", "memory")
        provider = self.vlayer.dataProvider()

        fields = QgsFields()
        for _field in _fields:
            fields.append(_field)

        provider.addAttributes(_fields)
        self.vlayer.updateFields()
        feats = []
        for features_attributes in data:
            feature = QgsFeature(fields)
            for idx, attr in enumerate(features_attributes):
                feature[_fields[idx].name()] = attr
            feature.setGeometry(None)
            #print("Feature valid: " + str(feature.isValid()))
            feats.append(feature)
        provider.addFeatures(feats)
        self.vlayer.updateExtents()

        features = [f for f in self.vlayer.getFeatures('True') if f.id() in self.vlayer.allFeatureIds()]
        feature_ids = [feature.id() for feature in features]

        QgsProject.instance().addMapLayer(self.vlayer)
        hide_print = True
        if not hide_print:
            print("1. Valid vlayer '{}'".format(self.vlayer.isValid()))
            print("2. feature_ids: " + str(feature_ids))
            print("5. QgsVectorLayer.getFeature(): " + str([self.vlayer.getFeature(x).id() for x in feature_ids]))
            print("6. QgsVectorLayer.getFeature() type: " + str([str(type(self.vlayer.getFeature(x))) for x in feature_ids]))
            print("7. QgsVectorLayer.getFeatures(): " + str([x.id() for x in self.vlayer.getFeatures(feature_ids)]))
            print("8. QgsVectorLayer.featureCount(): " + str(self.vlayer.featureCount()))

        root = QgsProject.instance().layerTreeRoot()
        root.addLayer(self.vlayer)

    def init_gs(self):
        mock_iface = mock.Mock
        self.gs = GroupStats(mock_iface)
        self.gs.run()

        self.all = self.gs.dlg.tm1
        self.rows_model = self.gs.dlg.tm2
        self.columns_model = self.gs.dlg.tm3
        self.values_model = self.gs.dlg.tm4
        self.showScore = 'showScore'
        self.actionSaveCSV = 'actionSaveCSV'
        self.data_var = 'data'

    def test_all_unique(self):
        _fields = [QgsField('id', QVariant.Int, QVariant.typeToName(QVariant.Int)),
                   QgsField('rows', QVariant.String, QVariant.typeToName(QVariant.Int)),
                   QgsField('cols', QVariant.String, QVariant.typeToName(QVariant.Int)),
                   QgsField('values', QVariant.Double, QVariant.typeToName(QVariant.Int))]
        data = [[1, 'row1', 'col1', 1.0], [2, 'row2', 'col1', 2.0], [3, 'row3', 'col1', 3.0], [4, 'row4', 'col1', 4.0]]
        self.create_vectorlayer(_fields, data)
        self.init_gs()

        for idx, value in enumerate(getattr(self.gs.dlg.tm1, self.data_var)):
            print("{} {}".format(str(idx), str(value)))

        cols_index = self.all.createIndex(0, 0)
        rows_index = self.all.createIndex(2, 0)
        values_index = self.all.createIndex(3, 0)
        sum_index = self.all.createIndex(10, 0)

        cols_data = self.all.mimeData([cols_index])
        rows_data = self.all.mimeData([rows_index])
        values_data = self.all.mimeData([values_index])
        sum_data = self.all.mimeData([sum_index])

        self.columns_model.dropMimeData(cols_data, None, 0, 0, QModelIndex())
        self.rows_model.dropMimeData(rows_data, None, 0, 0, QModelIndex())
        self.values_model.dropMimeData(sum_data, None, 0, 0, self.values_model.index(0))
        self.values_model.dropMimeData(values_data, None, 0, 0, self.values_model.index(0))

        @mock.patch("PyQt5.QtWidgets.QFileDialog.selectedFiles")
        @mock.patch('PyQt5.QtWidgets.QMainWindow.statusBar')
        @mock.patch("PyQt5.QtWidgets.QMessageBox.information")
        @mock.patch("PyQt5.QtWidgets.QFileDialog.exec_")
        @mock.patch("builtins.open")
        def savefile(dlg, mock_open, mock_exec, mock_messagebox, mock_statusbar, mock_selectedfile):
            mock_selectedfile.return_value = ['noname']
            mock_exec.return_value = 1
            getattr(self.gs.dlg, self.showScore)()
            mock_file = mock.MagicMock(spec=TextIOBase)
            mock_open.return_value = mock_file
            getattr(dlg.ui, self.actionSaveCSV).trigger()
            return mock_file

        mock_file = savefile(self.gs.dlg)
        print(str(mock_file.mock_calls))

        assert [call.write('cols;col1\r\n'),
                 call.write('rows;\r\n'),
                 call.write('row1;1.0\r\n'),
                 call.write('row2;2.0\r\n'),
                 call.write('row3;3.0\r\n'),
                 call.write('row4;4.0\r\n'),
                 call.close()] in mock_file.mock_calls

    def test_sum(self):
        _fields = [QgsField('id', QVariant.Int, QVariant.typeToName(QVariant.Int)),
                   QgsField('rows', QVariant.String, QVariant.typeToName(QVariant.Int)),
                   QgsField('cols', QVariant.String, QVariant.typeToName(QVariant.Int)),
                   QgsField('values', QVariant.Double, QVariant.typeToName(QVariant.Int))]
        data = [[1, 'row1', 'col1', 1.0], [2, 'row1', 'col1', 2.0], [3, 'row2', 'col1', 3.0], [4, 'row2', 'col1', 4.0]]
        self.create_vectorlayer(_fields, data)
        self.init_gs()

        for idx, value in enumerate(getattr(self.gs.dlg.tm1, self.data_var)):
            print("{} {}".format(str(idx), str(value)))

        cols_index = self.all.createIndex(0, 0)
        rows_index = self.all.createIndex(2, 0)
        values_index = self.all.createIndex(3, 0)
        sum_index = self.all.createIndex(10, 0)

        cols_data = self.all.mimeData([cols_index])
        rows_data = self.all.mimeData([rows_index])
        values_data = self.all.mimeData([values_index])
        sum_data = self.all.mimeData([sum_index])

        self.columns_model.dropMimeData(cols_data, None, 0, 0, QModelIndex())
        self.rows_model.dropMimeData(rows_data, None, 0, 0, QModelIndex())
        self.values_model.dropMimeData(sum_data, None, 0, 0, self.values_model.index(0))
        self.values_model.dropMimeData(values_data, None, 0, 0, self.values_model.index(0))

        @mock.patch("PyQt5.QtWidgets.QFileDialog.selectedFiles")
        @mock.patch('PyQt5.QtWidgets.QMainWindow.statusBar')
        @mock.patch("PyQt5.QtWidgets.QMessageBox.information")
        @mock.patch("PyQt5.QtWidgets.QFileDialog.exec_")
        @mock.patch("builtins.open")
        def savefile(dlg, mock_open, mock_exec, mock_messagebox, mock_statusbar, mock_selectedfile):
            mock_selectedfile.return_value = ['noname']
            mock_exec.return_value = 1
            getattr(self.gs.dlg, self.showScore)()
            mock_file = mock.MagicMock(spec=TextIOBase)
            mock_open.return_value = mock_file
            getattr(dlg.ui, self.actionSaveCSV).trigger()
            return mock_file

        mock_file = savefile(self.gs.dlg)
        print(str(mock_file.mock_calls))

        assert [call.write('cols;col1\r\n'),
                 call.write('rows;\r\n'),
                 call.write('row1;3.0\r\n'),
                 call.write('row2;7.0\r\n'),
                 call.close()] in mock_file.mock_calls

    def tearDown(self):
        QgsProject.instance().clear()