from qgis.core import QgsProject, QgsVectorLayer, QgsField, QgsFeature, QgsFields
from PyQt5.QtCore import QVariant, QModelIndex
import mock
import io
#from GroupStatsDialog import GroupStatsDialog
from groupstats import GroupStats


class TestGroupStats(object):

    def setUp(self):
        self.create_vectorlayer()
        mock_iface = mock.Mock
        self.gs = GroupStats(mock_iface)
        self.gs.run()

        self.all = self.gs.dlg.tm1
        self.rows_model = self.gs.dlg.tm2
        self.columns_model = self.gs.dlg.tm3
        self.values_model = self.gs.dlg.tm4
        self.showScore = 'showScore'
        self.actionSaveCSV = 'actionSaveCSV'

    def create_vectorlayer(self):
        #self.vlayer = QgsVectorLayer(providerLib="memory")
        self.vlayer = QgsVectorLayer("Point?crs=epsg:4326", "result", "memory")
        provider = self.vlayer.dataProvider()

        _fields = [QgsField('id', QVariant.Int),
                   QgsField('rows', QVariant.String),
                   QgsField('cols', QVariant.String),
                   QgsField('values', QVariant.Double)]
        fields = QgsFields()
        for _field in _fields:
            fields.append(_field)

        provider.addAttributes(_fields)
        self.vlayer.updateFields()
        feats = []
        for id, rows, cols, values in [[1, 'row1', 'col1', 1.0],
                                       [2, 'row2', 'col1', 2.0],
                                       [3, 'row3', 'col1', 3.0],
                                       [4, 'row4', 'col1', 4.0]]:

            feature = QgsFeature(fields)
            feature['id'] = id
            feature['rows'] = rows
            feature['cols'] = cols
            feature['values'] = values
            feature.setGeometry(None)
            #print("Feature valid: " + str(feature.isValid()))
            feats.append(feature)
            #self.vlayer.addFeature(feature)
        provider.addFeatures(feats)
        self.vlayer.updateExtents()

        #print("feats: " + str(feats))
        #print("add feats: " + str(self.vlayer.addFeatures(feats)))
        #provider.addFeatures(feats)

        features = [f for f in self.vlayer.getFeatures('True') if f.id() in self.vlayer.allFeatureIds()]

        #features = self.vlayer.getFeatures()
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


    def test_1(self):
        #gsd = GroupStatsDialog()
        #print(str(self.gs.ui.listHalf))
        for idx, value in enumerate(self.gs.dlg.tm1.data):
            print("{} {}".format(str(idx), str(value)))
        #print(self.gs.dlg.tm1.data)
        cols_index = self.all.createIndex(0, 0)
        rows_index = self.all.createIndex(2, 0)
        values_index = self.all.createIndex(3, 0)
        sum_index = self.all.createIndex(10, 0)

        cols_data = self.all.mimeData([cols_index])
        rows_data = self.all.mimeData([rows_index])
        values_data = self.all.mimeData([values_index])
        sum_data = self.all.mimeData([sum_index])
        self.columns_model.dropMimeData(dataMime=cols_data, share=None, rows=0, column=0, index=QModelIndex())
        self.rows_model.dropMimeData(dataMime=rows_data, share=None, rows=0, column=0, index=QModelIndex())
        self.values_model.dropMimeData(dataMime=sum_data, share=None, rows=0, column=0, index=QModelIndex())
        self.values_model.dropMimeData(dataMime=values_data, share=None, rows=0, column=0, index=QModelIndex())

        getattr(self.gs.dlg, self.showScore)()

        @mock.patch("PyQt5.QtWidgets.QMessageBox.information")
        @mock.patch("PyQt5.QtWidgets.QFileDialog")
        @mock.patch("builtins.open")
        def savefile(dlg, mock_open, mock_qfiledialog, mock_messagebox):
            mock_qfiledialog.return_value.exec_.return_value = 1
            mock_qfiledialog.return_value.selectedFiles = ['filename']
            f = io.StringIO()
            mock_open.return_value = f
            getattr(dlg.ui, self.actionSaveCSV).trigger()
            f.close()
            print(str(mock_messagebox.mock_calls))
        savefile(self.gs.dlg)
        #print("text: " + str(gsd.ui.layer.currentText()))
        assert False

    def tearDown(self):
        QgsProject.instance().clear()