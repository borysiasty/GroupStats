from qgis.core import QgsProject, QgsVectorLayer, QgsField, QgsFeature, QgsFields
from PyQt5.QtCore import QVariant
from GroupStatsDialog import GroupStatsDialog

class TestGroupStats(object):
    def setUp(self):

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


    def test_1(self):
        gsd = GroupStatsDialog()

        assert False

    def tearDown(self):
        QgsProject.instance().clear()